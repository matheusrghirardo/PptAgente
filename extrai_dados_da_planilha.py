"""
extrai_dados_da_planilha.py — Extração inteligente de dados financeiros de planilhas Excel via LLM.

Lê arquivos Excel com pandas, converte para representação textual (Markdown)
e usa o LLM para identificar, normalizar e estruturar os dados financeiros
relevantes. Suporta planilhas sem layout padronizado — o LLM infere o contexto.
"""

import json
import logging
from io import BytesIO
from typing import Any

import pandas as pd

from cliente_modelos_de_linguagem import LLMClient
from configura_modelos_por_etapa import modelo as _modelo

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────
# Prompt do sistema para extração de dados
# ─────────────────────────────────────────────────
SYSTEM_PROMPT_EXCEL_READER = """Você é um especialista em controladoria e FP&A.
Receberá o conteúdo de uma ou mais abas de uma planilha Excel e deve:

1. Identificar TODOS os dados financeiros e volumétricos relevantes para um fechamento mensal.
2. Para planilhas com MÚLTIPLOS MESES em colunas (ex: "Fev/25 (R$ mil)" e "Mar/25 (R$ mil)"):
   → Crie UMA ENTRADA POR MÊS POR INDICADOR — nunca consolide em uma só entrada.
   → Use o período no nome da chave: ex receita_produto_a_fev25 e receita_produto_a_mar25.
   → O campo "periodo" deve conter EXATAMENTE o mês/ano daquele valor (ex: "Fev/25", "Mar/25").
3. Normalizar valores numéricos (float sem formatação de milhar).
4. Ignorar apenas linhas auxiliares e cabeçalhos decorativos — NUNCA ignore totais.

5. **EXTRAÇÃO COMPLETA DE COLUNAS — REGRA OBRIGATÓRIA:**
   Para tabelas com séries temporais, extraia TODAS as colunas presentes —
   não apenas os valores absolutos.
   Para cada indicador identifique e extraia:
   - Variações período a período (MoM, semana a semana, etc)
     tanto em valor absoluto quanto em percentual
   - Valores de períodos de comparação (mesmo mês do ano anterior,
     trimestre anterior, etc) se presentes na tabela
   - Variações de longo prazo (YoY, YTD, etc)

   Use sufixos descritivos nas chaves do JSON baseados no que estiver
   escrito nos cabeçalhos da própria planilha.
   Não assuma nomes de colunas — leia os cabeçalhos reais.

   Esses campos são obrigatórios quando presentes na planilha —
   sem eles o pipeline não consegue preencher todos os campos do PPTX.

RETORNE **apenas** um JSON válido (sem markdown, sem ```), com a estrutura:
{
  "dados": {
    "<chave_snake_case_com_periodo>": {
      "label": "<nome legível do indicador>",
      "valor": <número float>,
      "unidade": "<R$, %, unidades, etc.>",
      "periodo": "<mês/ano EXATO desse valor, ex: Fev/25 ou Mar/25>",
      "variacao_mes": "<+X,X% ou null — variação MoM percentual, vírgula decimal, sinal explícito>",
      "variacao_mes_abs": <número float ou null — variação MoM em valor absoluto>,
      "valor_referencia_yoy": <número float ou null — valor do mesmo mês do ano anterior>,
      "periodo_referencia_yoy": "<mês/ano da coluna YoY, ex: Mar/24 ou null>",
      "variacao_yoy": "<+X,X% ou null — variação YoY percentual, vírgula decimal, sinal explícito>",
      "contexto": "<breve descrição>"
    }
  },
  "resumo": "<frase curta descrevendo os dados encontrados>"
}

ATENÇÃO AOS CAMPOS ADICIONAIS:
- "variacao_mes_abs": valor ABSOLUTO (em R$, unidades, etc.) da variação MoM.
  Leia o cabeçalho da coluna para saber a unidade (ex: "Var. MoM (R$)").
  Positivo se cresceu, negativo se caiu.
- "valor_referencia_yoy": valor do mesmo mês no ano anterior.
  Leia o cabeçalho (ex: "Mar/24 (R$ mil)") para saber qual coluna pegar.
- "periodo_referencia_yoy": o período de referência YoY (ex: "Mar/24").
- "variacao_yoy": variação percentual YoY lida diretamente da planilha.

Se uma dessas colunas NÃO existir na planilha, use null para o campo.
Se existir, é OBRIGATÓRIO extrair — nunca omita colunas presentes.

REGRAS CRÍTICAS:
- Extraia TODOS os meses disponíveis na planilha — nunca apenas o mais recente.
  Para cada linha de dado, crie entradas SEPARADAS para cada coluna de mês.
- O campo "periodo" deve refletir o cabeçalho da coluna de onde o valor veio
  (ex: coluna "Mar/25 (R$ mil)" → periodo="Mar/25").
- Inclua TOTAIS e subtotais como entradas separadas por mês.
- Chaves: snake_case + sufixo do período (sem barras, lowercase), ex: _mar25, _fev25.
- Percentuais SEMPRE com vírgula decimal e sinal: "+3,2%" ou "-1,5%".
  NUNCA use ponto decimal em percentuais.
- As variações (MoM, YoY) e valor de referência YoY da planilha pertencem ao mês
  ATUAL (mais recente) — atribua-os às entradas do mês atual.
  Entradas de meses anteriores NÃO têm variações (use null).
- Se não encontrar dados financeiros: {"dados": {}, "resumo": "Nenhum dado financeiro identificado."}.
"""


def _df_para_texto(df: pd.DataFrame) -> str:
    """Converte DataFrame para texto.

    Tenta to_markdown (requer tabulate) e cai em to_csv caso o pacote
    não esteja instalado — garantindo que o LLM sempre receba conteúdo.
    """
    try:
        return df.to_markdown(index=False)
    except (ImportError, ModuleNotFoundError):
        logger.warning("tabulate não instalado — usando CSV como fallback para to_markdown()")
        return df.to_csv(index=False, sep="\t")
    except Exception as e:
        logger.warning("to_markdown falhou (%s) — usando to_string() como fallback", e)
        return df.to_string(index=False)


def _excel_para_markdown(file_bytes: bytes, filename: str) -> str:
    """Converte um arquivo Excel em representação Markdown (todas as abas).

    Usa ``header=0`` para preservar os nomes reais das colunas, que são
    essenciais para o LLM inferir o contexto semântico dos dados.
    Se a aba falhar com header=0, tenta novamente com header=None.
    """
    xls = pd.ExcelFile(BytesIO(file_bytes))
    partes: list[str] = [f"## Arquivo: {filename}\n"]

    for sheet_name in xls.sheet_names:
        # Tenta com header=0 (preserva nome das colunas)
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=0)
        except Exception:
            # Fallback: sem header (ex: planilhas com merges no topo)
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

        # Remove linhas inteiramente vazias (não remove colunas para não perder contexto)
        df = df.dropna(how="all")
        # Remove colunas cujos nomes são NaN (colunas sem cabeçalho)
        df = df.loc[:, df.columns.notna()]
        # Renomeia colunas numéricas para evitar nomes sem sentido para o LLM
        df.columns = [
            col if not isinstance(col, int) else f"Coluna_{col}"
            for col in df.columns
        ]

        if df.empty:
            logger.debug("Aba '%s' vazia após limpeza — ignorada.", sheet_name)
            continue

        partes.append(f"### Aba: {sheet_name}")
        # Limita a 200 linhas para não estourar contexto do LLM
        df_limited = df.head(200)
        partes.append(_df_para_texto(df_limited))
        if len(df) > 200:
            partes.append(f"_(... {len(df) - 200} linhas adicionais omitidas)_")
        partes.append("")

    if len(partes) == 1:
        # Nenhuma aba com dados foi encontrada
        partes.append("_(Nenhuma aba com dados encontrada neste arquivo.)_\n")

    return "\n".join(partes)


def extrair_dados_excel(
    llm: LLMClient,
    excel_files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    """Extrai dados financeiros estruturados de um ou mais arquivos Excel.

    Args:
        llm: Instância configurada de LLMClient.
        excel_files: Lista de tuplas (filename, file_bytes).

    Returns:
        Dicionário com chave ``dados`` (dict de indicadores) e ``resumo`` (str).
    """
    # 1. Converter todos os Excels para Markdown
    markdown_parts: list[str] = []
    for filename, file_bytes in excel_files:
        try:
            md = _excel_para_markdown(file_bytes, filename)
            n_chars = len(md)
            logger.info("Excel '%s' convertido: %d caracteres de conteúdo.", filename, n_chars)
            markdown_parts.append(md)
        except Exception as e:
            logger.error("Erro ao converter '%s' para markdown: %s", filename, e)
            markdown_parts.append(
                f"## Arquivo: {filename}\n"
                f"_(Erro ao processar planilha: {e}. "
                f"Verifique se o arquivo é um .xlsx/.xls válido.)_\n"
            )

    conteudo_excel = "\n---\n".join(markdown_parts)

    # 2. Chamar o LLM com o conteúdo
    user_message = (
        "Analise os dados abaixo extraídos de planilhas Excel do fechamento mensal "
        "e retorne o JSON estruturado conforme as instruções.\n\n"
        f"{conteudo_excel}"
    )

    resposta = llm.chat(SYSTEM_PROMPT_EXCEL_READER, user_message,
                        model=_modelo("excel_extractor"))

    # 3. Parsear o JSON da resposta
    if resposta.startswith("ERRO_LLM"):
        logger.error("LLM retornou erro: %s", resposta)
        return {"dados": {}, "resumo": f"Erro na extração: {resposta}", "erro": True}

    try:
        dados = _parse_json_resposta(resposta)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Falha ao parsear JSON do LLM: %s\nResposta: %s", e, resposta[:500])
        return {"dados": {}, "resumo": f"Erro ao parsear resposta do LLM: {e}", "erro": True}

    dados = _normalizar_resposta_excel(dados)
    n_periodos = len({v.get('periodo') for v in dados.get('dados', {}).values() if v.get('periodo')})
    logger.info("excel_reader: %d indicadores, %d período(s) distinto(s).",
                len(dados.get('dados', {})), n_periodos)
    return dados


def _normalizar_resposta_excel(dados: dict) -> dict:
    """Normaliza o retorno do LLM para o formato canônico {dados: {chave: {valor, periodo, ...}}}.

    Suporta três layouts que o LLM pode produzir:
      A) Já está no formato correto → passa por.
      B) Formato mes_atual/mes_anterior → converte para flat com sufixo de período.
      C) Sem chave 'dados' → encapsula.
    """
    # Caso A: formato correto — flat com chave 'dados'
    if "dados" in dados and isinstance(dados["dados"], dict):
        # Verificar se as entradas têm "periodo" — se sim, já está no formato correto
        entradas = dados["dados"]
        if entradas and any("periodo" in v for v in entradas.values() if isinstance(v, dict)):
            return dados
        # Flat sem 'periodo' — retorna como está (compatibilidade)
        return dados

    # Caso B: formato mes_atual / mes_anterior
    if "mes_atual" in dados or "mes_anterior" in dados:
        flat: dict = {}
        for chave_bloco in ("mes_anterior", "mes_atual"):  # anterior primeiro
            bloco = dados.get(chave_bloco, {})
            if not bloco:
                continue
            periodo_label = bloco.get("periodo") or "?"
            # Gera sufixo: "Mar/25" → "_mar25", "Fev/25" → "_fev25"
            sufixo = "_" + periodo_label.lower().replace("/", "").replace(" ", "")
            for k, v in bloco.get("dados", {}).items():
                if not isinstance(v, dict):
                    continue
                chave = f"{k}{sufixo}" if not k.endswith(sufixo) else k
                flat[chave] = {**v, "periodo": periodo_label}
        # Variações: associar ao mes_atual
        periodo_atual = dados.get("mes_atual", {}).get("periodo", "?")
        sufixo_atual = "_" + periodo_atual.lower().replace("/", "").replace(" ", "")
        for k, v in dados.get("variacoes", {}).items():
            base = k.removesuffix("_mom").removesuffix("_yoy")
            chave_atual = f"{base}{sufixo_atual}"
            if chave_atual in flat and "_mom" in k:
                flat[chave_atual]["variacao_mes"] = v
        return {"dados": flat, "resumo": dados.get("resumo", "")}

    # Caso C: sem 'dados' e sem estrutura conhecida
    return {"dados": dados, "resumo": "Dados extraídos (formato legado)."}


def _parse_json_resposta(resposta: str) -> dict:
    """Extrai JSON da resposta do LLM, removendo wrapping markdown se presente."""
    texto = resposta.strip()
    # Remove ```json ... ``` se o LLM incluiu
    if texto.startswith("```"):
        linhas = texto.split("\n")
        linhas = [l for l in linhas if not l.strip().startswith("```")]
        texto = "\n".join(linhas)
    # Tenta encontrar o JSON dentro da resposta
    inicio = texto.find("{")
    fim = texto.rfind("}") + 1
    if inicio == -1 or fim == 0:
        raise ValueError("Nenhum JSON encontrado na resposta do LLM")
    return json.loads(texto[inicio:fim])
