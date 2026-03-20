"""
extrai_padroes_do_pptx.py — Extração de padrões de formatação via LLM.

Lê o conteúdo textual do PPTX base, envia ao LLM para identificar os padrões
de formatação (datas, percentuais, valores, etc.) e retorna um dicionário
que é utilizado por todo o pipeline para manter consistência com o arquivo original.

Substitui o date_context.py — não usa regex hardcoded para datas.
"""

import json
import logging
import unicodedata
from io import BytesIO
from typing import Any

from pptx import Presentation

from cliente_modelos_de_linguagem import LLMClient
from configura_modelos_por_etapa import modelo as _modelo

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────
# Tabelas de meses em português
# ─────────────────────────────────────────────────

MESES_COMPLETOS = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

MESES_ABREV = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

# ─────────────────────────────────────────────────
# Prompt de sistema para extração de padrões
# ─────────────────────────────────────────────────

SYSTEM_PROMPT_PATTERNS = """\
Você é um analisador de padrões de documentos financeiros.
Analise o conteúdo do arquivo PowerPoint abaixo e extraia os padrões de formatação utilizados.

Retorne APENAS um JSON válido, sem texto adicional, com esta estrutura exata:
{
  "formato_data_capa": "<ex: Fevereiro 2025>",
  "formato_data_abrev": "<ex: Fev/25>",
  "formato_data_yoy": "<ex: Fev/24>",
  "formato_percentual_positivo": "<ex: +4,2%>",
  "formato_percentual_negativo": "<ex: -6,6%>",
  "formato_valor_total": "<ex: R$ 52,0 MM>",
  "formato_valor_tabela": "<ex: 19.230>",
  "separador_decimal": "<ex: ,>",
  "separador_milhar": "<ex: .>",
  "casas_decimais_pct": <numero inteiro, ex: 1>,
  "prefixo_positivo": "<ex: +>",
  "simbolo_moeda": "<ex: R$>",
  "unidade_valor": "<ex: MM ou mil>",
  "formato_coluna_mom": "<ex: Fev/25 vs Jan/25 (MoM)>",
  "formato_coluna_yoy": "<ex: vs Fev/24 (YoY)>",
  "formato_rodape": "<ex: Valores em R$ mil | Fonte: ...>",
  "mes_referencia_num": <1-12>,
  "mes_referencia_nome": "<ex: Fevereiro>",
  "ano_referencia": <ex: 2025>
}

REGRAS:
- Examine TODOS os slides para identificar os padrões mais frequentes.
- Se um padrão não for encontrado, use o valor mais provável baseado no contexto financeiro brasileiro.
- O mes_referencia é o mês do relatório no arquivo (NÃO o próximo mês).
- Para casas_decimais_pct, conte quantas casas decimais os percentuais usam no arquivo.
- Retorne APENAS o JSON, sem explicações, sem markdown code fences."""


# ─────────────────────────────────────────────────
# Extração de texto do PPTX
# ─────────────────────────────────────────────────

def _extrair_textos_pptx(pptx_bytes: bytes) -> str:
    """Extrai e concatena todos os textos legíveis dos slides."""
    prs = Presentation(BytesIO(pptx_bytes))
    fragmentos: list[str] = []
    for slide_idx, slide in enumerate(prs.slides, 1):
        fragmentos.append(f"\n--- Slide {slide_idx} ---")
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                fragmentos.append(shape.text.strip())
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        fragmentos.append(" | ".join(cells))
    return "\n".join(fragmentos)


def _parse_json_resposta(resposta: str) -> dict | None:
    """Parse JSON do retorno do LLM, removendo fences de markdown."""
    texto = resposta.strip()
    if texto.startswith("```"):
        linhas = texto.split("\n")
        linhas = [l for l in linhas if not l.strip().startswith("```")]
        texto = "\n".join(linhas)
    inicio = texto.find("{")
    fim = texto.rfind("}") + 1
    if inicio == -1 or fim == 0:
        return None
    try:
        return json.loads(texto[inicio:fim])
    except json.JSONDecodeError:
        return None


# ─────────────────────────────────────────────────
# Helpers de mês
# ─────────────────────────────────────────────────

def _remover_acentos(s: str) -> str:
    """Remove diacríticos (ex: 'Março' → 'Marco')."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _proximo_mes(mes_num: int, ano: int) -> tuple[int, int]:
    """Retorna (mes, ano) do mês seguinte, com virada de ano."""
    if mes_num == 12:
        return 1, ano + 1
    return mes_num + 1, ano


# ─────────────────────────────────────────────────
# API pública — Extração de padrões
# ─────────────────────────────────────────────────

def extrair_padroes(llm: LLMClient, pptx_bytes: bytes) -> dict | None:
    """Extrai padrões de formatação do PPTX base via LLM.

    Args:
        llm: Instância configurada de LLMClient.
        pptx_bytes: Bytes brutos do arquivo PPTX.

    Returns:
        Dicionário de padrões ou None se a extração falhar.
    """
    logger.info("extrair_padroes: tipo=%s tamanho=%d bytes",
                type(pptx_bytes).__name__, len(pptx_bytes) if pptx_bytes else 0)

    try:
        texto = _extrair_textos_pptx(pptx_bytes)
    except Exception as exc:
        import traceback
        logger.error("Erro ao ler PPTX para extração de padrões: %s\n%s", exc, traceback.format_exc())
        return None

    if not texto.strip():
        logger.warning("PPTX não contém texto legível.")
        return None

    # Truncar se necessário para caber no contexto do LLM
    if len(texto) > 8000:
        texto = texto[:8000] + "\n\n[... conteúdo truncado ...]"

    user_message = (
        "Analise o conteúdo deste arquivo PowerPoint e extraia os "
        "padrões de formatação:\n\n"
        f"{texto}"
    )

    logger.info("Pattern extractor: chamando LLM, user_message=%d chars", len(user_message))
    try:
        resposta = llm.chat(SYSTEM_PROMPT_PATTERNS, user_message,
                            model=_modelo("pattern_extractor"))
    except Exception as _llm_exc:
        import traceback
        logger.error("Exceção ao chamar LLM: %s\n%s", _llm_exc, traceback.format_exc())
        return None

    if resposta.startswith("ERRO_LLM"):
        logger.error("LLM retornou erro na extração de padrões: %s", resposta)
        return None

    padroes = _parse_json_resposta(resposta)
    if not padroes:
        logger.error("Falha ao parsear JSON de padrões. Resposta: %s", resposta[:500])
        return None

    mes = padroes.get("mes_referencia_num")
    ano = padroes.get("ano_referencia")

    if not (isinstance(mes, int) and 1 <= mes <= 12):
        logger.warning("mes_referencia_num inválido ou ausente: %s", mes)
        return None
    if not (isinstance(ano, int) and 2000 <= ano <= 2100):
        logger.warning("ano_referencia inválido ou ausente: %s", ano)
        return None

    logger.info(
        "Padrões extraídos: ref=%s/%s, %d campos detectados",
        mes, ano, len(padroes),
    )
    return padroes


# ─────────────────────────────────────────────────
# API pública — Cálculo de contexto
# ─────────────────────────────────────────────────

def calcular_contexto(
    padroes: dict,
    override_mes: int | None = None,
    override_ano: int | None = None,
) -> dict:
    """Calcula o contexto completo a partir dos padrões extraídos.

    Mescla os padrões de formatação com os campos temporais calculados
    (mês novo, labels, nome do arquivo de saída).

    Args:
        padroes: Dict retornado por ``extrair_padroes()``.
        override_mes: Sobrescreve o mês base detectado (1-12).
        override_ano: Sobrescreve o ano base detectado.

    Returns:
        Dicionário unificado de contexto (padrões + campos temporais).
    """
    mes_base = override_mes if override_mes else padroes["mes_referencia_num"]
    ano_base = override_ano if override_ano else padroes["ano_referencia"]
    mes_novo, ano_novo = _proximo_mes(mes_base, ano_base)

    nome_base = MESES_COMPLETOS[mes_base - 1]
    abrev_base = MESES_ABREV[mes_base - 1]
    nome_novo = MESES_COMPLETOS[mes_novo - 1]
    abrev_novo = MESES_ABREV[mes_novo - 1]

    # Labels seguindo o formato extraído (ex: "Abr/25")
    label_anterior = f"{abrev_base}/{str(ano_base)[2:]}"
    label_novo = f"{abrev_novo}/{str(ano_novo)[2:]}"
    label_yoy = f"{abrev_novo}/{str(ano_novo - 1)[2:]}"

    # Nome de arquivo sem acentos
    nome_novo_limpo = _remover_acentos(nome_novo.lower())
    nome_saida = f"fechamento_{nome_novo_limpo}_{ano_novo}.pptx"

    return {
        # Padrões extraídos pelo LLM (pass-through)
        **padroes,
        # Campos temporais calculados
        "mes_base_nome": nome_base,
        "mes_base_abrev": abrev_base,
        "ano_base": ano_base,
        "mes_base_num": mes_base,
        "mes_novo_nome": nome_novo,
        "mes_novo_abrev": abrev_novo,
        "ano_novo": ano_novo,
        "mes_novo_num": mes_novo,
        "label_anterior": label_anterior,
        "label_novo": label_novo,
        "label_yoy": label_yoy,
        "nome_arquivo_saida": nome_saida,
    }


# ─────────────────────────────────────────────────
# API pública — Formatação de valores
# ─────────────────────────────────────────────────

def formatar_valor(valor: float, tipo: str, padroes: dict) -> str:
    """Formata um número seguindo os padrões extraídos do PPTX.

    Args:
        valor: Número a formatar.
        tipo: ``'percentual'``, ``'valor_tabela'`` ou ``'valor_total'``.
        padroes: Dicionário de padrões (ou contexto completo).

    Returns:
        String formatada.
    """
    sep_dec = padroes.get("separador_decimal", ",")
    sep_mil = padroes.get("separador_milhar", ".")

    if tipo == "percentual":
        casas = int(padroes.get("casas_decimais_pct", 1))
        prefixo = padroes.get("prefixo_positivo", "+") if valor > 0 else ""
        num_str = f"{abs(valor):.{casas}f}"
        if sep_dec != ".":
            num_str = num_str.replace(".", sep_dec)
        sinal = "-" if valor < 0 else prefixo
        return f"{sinal}{num_str}%"

    if tipo == "valor_tabela":
        negativo = valor < 0
        parte_inteira = int(abs(valor))
        # Formatar com separador de milhar usando placeholder temporário
        s = f"{parte_inteira:,}".replace(",", "\x00")
        s = s.replace("\x00", sep_mil)
        return f"-{s}" if negativo else s

    if tipo == "valor_total":
        simbolo = padroes.get("simbolo_moeda", "R$")
        unidade = padroes.get("unidade_valor", "MM")
        if unidade.upper() in ("MM", "MI", "MILHÃO", "MILHÕES"):
            divisor = 1_000_000
        elif unidade.lower() in ("mil", "k"):
            divisor = 1_000
        else:
            divisor = 1
        reduced = valor / divisor if divisor > 1 else valor
        num_str = f"{reduced:,.1f}".replace(",", "\x00").replace(".", "\x01")
        num_str = num_str.replace("\x00", sep_mil).replace("\x01", sep_dec)
        return f"{simbolo} {num_str} {unidade}"

    # Fallback genérico
    return str(valor)


# ─────────────────────────────────────────────────
# API pública — Helpers de exibição
# ─────────────────────────────────────────────────

def formatar_contexto_para_log(ctx: dict) -> str:
    """Formata o contexto para exibição em logs e UI."""
    linhas = [
        f"📅 **Período:** {ctx['mes_base_nome']} {ctx['ano_base']} "
        f"({ctx['label_anterior']}) → "
        f"{ctx['mes_novo_nome']} {ctx['ano_novo']} ({ctx['label_novo']})",
    ]
    for key, label in [
        ("formato_percentual_positivo", "Percentual (+)"),
        ("formato_percentual_negativo", "Percentual (–)"),
        ("formato_valor_total", "Valor total"),
        ("formato_valor_tabela", "Valor tabela"),
        ("formato_data_abrev", "Data abreviada"),
        ("casas_decimais_pct", "Casas decimais %"),
    ]:
        if key in ctx:
            linhas.append(f"  • {label}: `{ctx[key]}`")
    linhas.append(f"💾 Arquivo de saída: `{ctx['nome_arquivo_saida']}`")
    return "\n".join(linhas)
