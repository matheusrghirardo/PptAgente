"""
gera_plano_de_edicao_do_pptx.py — Mapeamento inteligente entre dados do Excel e elementos do PPTX.

Recebe o dicionário de dados financeiros (output do extrai_dados_da_planilha) e a estrutura
textual dos slides do PPTX base. Usa o LLM para decidir quais dados do Excel
correspondem a quais elementos dos slides, e retorna um plano de edição
compatível com o formato de ações do DeckForge (agents.py).
"""

import json
import logging
from typing import Any

from cliente_modelos_de_linguagem import LLMClient
from configura_modelos_por_etapa import modelo as _modelo
from extrai_estrutura_do_pptx import extrair_estrutura_pptx, gerar_resumo_estrutura

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────
# Prompt do sistema para mapeamento
# ─────────────────────────────────────────────────
SYSTEM_PROMPT_MAPPER = """Você é um agente de fechamento mensal de controladoria.
Receberá três blocos:

1. **DADOS DO EXCEL** — JSON com indicadores financeiros do mês atual.
2. **PADRÕES EXTRAÍDOS** — formatação identificada no PPTX base.
3. **ESTRUTURA DO PPTX** — representação COMPLETA de cada slide, shape e célula do arquivo base.

Sua ÚNICA FONTE DE VERDADE é a ESTRUTURA DO PPTX recebida.
Toda decisão de mapeamento deve emergir da leitura desse conteúdo — nunca de regras suas.

=== MÉTODO DE TRABALHO ===

Para cada slide na estrutura recebida, leia cada shape e cada célula e classifique
o conteúdo PELO QUE VOCÊ LÊ, não pelo que imagina:

1. IDENTIFIQUE A NATUREZA de cada texto lendo seu conteúdo e contexto:

   A) LABEL DESCRITIVO (ex.: "Var. vs Jan/25", "Receita Total Fev/25"):
      → Labels NÃO recebem valores numéricos.
      → Se contêm referência de período, atualize APENAS a parte do período,
        preservando todo o restante do texto sem alteração.

   B) VALOR NUMÉRICO ISOLADO (shape com APENAS um número, percentual ou
      valor monetário — ex.: "18.450", "+3,8%", "R$ 52,0 MM", "-4,1%"):
      → Determine QUAL indicador esse valor representa lendo o LABEL ADJACENTE
        (shape vizinha no mesmo slide). Exemplos:
          · Label "Receita Total" → valor = Receita Total do Excel
          · Label "Var. vs Jan/25" (MoM) → valor = Var. MoM (%) do TOTAL no Excel
          · Label "Var. vs Fev/24" (YoY) → valor = Var. YoY (%) do TOTAL no Excel
      → Busque o indicador correspondente nos DADOS DO EXCEL e use ESSE VALOR.
        NÃO use o valor que está no PPTX como referência para o novo valor —
        o PPTX pode estar desatualizado. O Excel é a fonte de verdade dos valores.
      → Se não houver correspondente claro no Excel, omita.
      → ATENÇÃO: shapes de valor numérico DEVEM ter ação gerada se o Excel
        fornece um valor diferente do que está no PPTX — mesmo que o valor
        do PPTX coincida com outro contexto (ex.: tabela). Verifique.

      REGRA ESPECIAL — KPIs ISOLADOS NA CAPA:
      Shapes na capa (slide 1) que contêm apenas um percentual isolado
      (ex: '+3,8%', '+11,6%', '-4,1%') são KPIs de variação total.
      → O shape logo ABAIXO (ou adjacente) a um label 'Var. vs [mês anterior]'
        é o MoM total → use o campo variacao_mes do indicador TOTAL no Excel.
      → O shape logo ABAIXO (ou adjacente) a um label 'Var. vs [mês/ano anterior]'
        é o YoY total → use o campo variacao_yoy do indicador TOTAL no Excel.
      → SEMPRE gere ação para esses shapes se o Excel fornece um valor diferente,
        mesmo que o shape não tenha label próprio — o label adjacente é suficiente
        para identificar o indicador. Nunca omita esses shapes.

   C) SHAPE COMPOSTO: "VALOR + REFERÊNCIA" (ex.: "+11,6% vs Fev/24",
      "Prod. C  +6,9%", "+3,8% vs Jan/25"):
      → Esses shapes contêm AMBOS: um valor numérico E uma referência de período.
      → Gere UMA ação que atualiza o shape INTEIRO:
          · Substitua o VALOR pelo dado correto do Excel (linha TOTAL ou linha
            do produto indicado pelo rótulo).
          · Substitua a REFERÊNCIA DE PERÍODO avançando 1 mês.
          · valor_antigo = texto COMPLETO atual | valor_novo = novo texto COMPLETO.
      → Exemplo: "+11,6% vs Fev/24" → "+11,2% vs Mar/24" (valor E período mudam).

   D) TEXTO COM REFERÊNCIA DE PERÍODO EM TEXTO LONGO (ex.: footers como
      "...  |  Base: Fechamento Fev/25"):
      → Use "substituir_texto_global" com valor_antigo = APENAS a substring que
        contém a referência de período (ex.: "Fechamento Fev/25") e o valor_novo
        com a substring atualizada (ex.: "Fechamento Mar/25").
      → Isso evita problemas de espaçamento ao copiar textos longos.

   E) CABEÇALHO DE PERÍODO EM TABELA (ex.: "Fev/25 (R$ mil)"):
      → Identifique qual ponto no tempo esse cabeçalho representa
        (mês atual, anterior, YoY) pela data escrita.
      → Avance o período em 1 mês preservando o formato.
      → NÃO altere os VALORES da coluna YoY (essa coluna vai apenas renomear
        seu cabeçalho; os valores ficam iguais salvo se o Excel fornecer novos).

   F) CÉLULA DE DADO NA COLUNA DO MÊS ANTERIOR (ex.: coluna Jan/25 → vira Fev/25):
      → Essa coluna receberá os valores do mês "anterior" que o Excel fornece.
      → Use a coluna de dados do mês anterior no Excel (ex.: coluna Jan/25
        do Excel vira a nova coluna Fev/25 do PPTX).

   G) TEXTO ESTÁTICO (ex.: "Valores em R$ mil", rótulos fixos sem data):
      → Não mudam. Não gere ação.

2. LINHA TOTAL DA TABELA — REGRA ESPECIAL:
   A linha de TOTAL (ex.: "TOTAL RECEITA BRUTA") é especialmente crítica:
   - Valor absoluto da coluna do mês anterior → use dado do Excel linha TOTAL.
   - Var. MoM (%) → use Var. MoM (%) do TOTAL no Excel; NÃO confie no valor
     atual do PPTX pois pode estar inconsistente com os dados individuais.
   - Var. YoY (%) → use Var. YoY (%) do TOTAL no Excel pela mesma razão.
   Gere ações para TODOS os campos do TOTAL que diferem do Excel.

3. ANALISE RELAÇÕES TEMPORAIS lendo o próprio arquivo base:
   - Leia TODAS as referências de período em cabeçalhos de tabela e labels.
   - Deduza o papel de cada período (atual, anterior, YoY) pela data escrita.
   - Avance cada um independentemente em 1 mês.
   - NUNCA assuma quantas colunas de período existem — leia TODAS.

4. SOBRE SUBSTITUIÇÃO GLOBAL vs POR SHAPE:
   - "substituir_texto_global" APENAS quando o mesmo token aparece com o
     MESMO papel semântico em TODAS as ocorrências do deck.
   - Se um token como "Fev/25" aparece como mês atual num lugar e mês
     anterior em outro → papéis diferentes → ação separada, NUNCA global.
   - Para substrings únicas em textos longos (footers), prefira
     "substituir_texto_global" com a substring exata (ver item D acima).

=== PROIBIÇÕES ABSOLUTAS ===

❌ NUNCA recalcule valores — use exatamente o que o Excel fornece.
❌ NUNCA invente formatos — replique o padrão existente no PPTX.
❌ NUNCA substitua um label descritivo por um valor numérico.
❌ NUNCA crie shapes novos ou altere cores/fontes/layout.
❌ NUNCA gere ação onde valor_antigo é igual a valor_novo (ação vazia).
❌ NUNCA retorne valor_novo como string vazia — se não encontrar o dado
   correspondente no Excel, OMITA a ação completamente. Uma ação com
   valor_novo vazio corrompe o slide.
❌ NUNCA ignore slides — processe TODOS os slides da estrutura recebida.
❌ NUNCA assuma o que um shape contém — leia.
❌ NUNCA use o valor atual do PPTX como referência para shapes numéricos;
   sempre verifique se o Excel fornece um valor diferente.

=== FORMATAÇÃO ===

Use os PADRÕES EXTRAÍDOS para casas decimais, separadores e sinais.
Para percentuais do Excel fornecidos como float (ex.: 0.0196), formate
conforme o padrão detectado (ex.: "+2,0%" com 1 casa decimal, sinal positivo).

=== CORRESPONDÊNCIA PERÍODO → COLUNA DE TABELA ===

Os DADOS DO EXCEL contêm o campo "periodo" em cada indicador (ex.: "periodo": "Mar/25").
Use esse campo para correspondência DIRETA com o cabeçalho da coluna do PPTX:
  · Indicador com periodo="Fev/25" → vai para a coluna cujo cabeçalho é "Fev/25 (R$ mil)"
  · Indicador com periodo="Mar/25" → vai para a coluna cujo cabeçalho é "Mar/25 (R$ mil)"
Isso garante que mês anterior e mês atual sej am preenchidos corretamente em colunas distintas.

ATENÇÃO — Dois meses, duas colunas:
Quando o Excel fornecer dados para DOIS meses distintos (ex.: Fev/25 e Mar/25):
  → A coluna "Fev/25 (R$ mil)" deve receber os valores dos indicadores com periodo="Fev/25"
  → A coluna "Mar/25 (R$ mil)" deve receber os valores dos indicadores com periodo="Mar/25"
  → Gere ações para AMBAS as colunas — nunca omita uma coluna por ter o mesmo nome que
    o mês do Excel.

=== VERIFICAÇÃO FINAL ===

Antes de outputar, confirme mentalmente:
[ ] Processei TODOS os slides e TODOS os shapes da estrutura?
[ ] Shapes numéricos isolados adjacentes a labels foram atualizados com Excel?
[ ] Shapes compostos "VALOR + PERÍODO" tiveram ambos atualizados?
[ ] Linha TOTAL da tabela foi verificada campo a campo contra o Excel?
[ ] Footers com referência de período usam substituir_texto_global na substring?
[ ] Cada cabeçalho de período em tabela foi atualizado (incluindo YoY)?
[ ] Nenhum label descritivo foi confundido com valor numérico?
[ ] Nenhuma ação tem valor_antigo === valor_novo?
[ ] Todos os valor_antigo são cópias EXATAS do texto no PPTX?
[ ] Não usei substituição global para textos com papéis semânticos diferentes?

=== FORMATO DE SAÍDA ===

Retorne APENAS um array JSON (sem markdown, sem ```, sem texto):
[
  {
    "tipo": "edicao",
    "acao": "alterar_texto" | "alterar_celula_tabela" | "substituir_texto_global",
    "slide_numero": <1-based>,
    "shape_indice": <0-based>,
    "valor_antigo": "<texto EXATO atual no PPTX — copie letra por letra>",
    "valor_novo": "<novo valor formatado conforme padrão>",
    "tabela_linha": <row 0-based, só se tabela>,
    "tabela_coluna": <col 0-based, só se tabela>,
    "descricao": "<slide X | shape Y | o que está sendo alterado>"
  }
]

REGRAS DO JSON:
- Omita campos não utilizados (tabela_linha/tabela_coluna quando não é tabela)
- Ordene por slide_numero crescente
- descricao deve indicar slide, shape e natureza da mudança
"""


def gerar_plano_edicao(
    llm: LLMClient,
    dados_excel: dict[str, Any],
    pptx_bytes: bytes,
    contexto: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Gera plano de edição mapeando dados do Excel para elementos do PPTX.

    Args:
        llm: Instância configurada de LLMClient.
        dados_excel: Output do excel_reader (dicionário com chave ``dados``).
        pptx_bytes: Bytes do PPTX base (mês anterior).
        contexto: Dicionário unificado de contexto (padrões + campos temporais).

    Returns:
        Lista de comandos de edição no formato do DeckForge.
    """
    # 1. Extrair estrutura do PPTX
    estrutura = extrair_estrutura_pptx(pptx_bytes)
    resumo_pptx = gerar_resumo_estrutura(estrutura)

    logger.info("Mapper: resumo_pptx=%d chars", len(resumo_pptx))

    # 2. Montar prompt com os dois blocos de informação
    dados_json = json.dumps(dados_excel.get("dados", {}), ensure_ascii=False, indent=2)

    # Bloco de contexto (temporal + padrões de formatação)
    bloco_contexto = ""
    if contexto:
        bloco_contexto = (
            "=== CONTEXTO DO RELATÓRIO ===\n"
            f"Você está gerando o fechamento de {contexto['mes_novo_nome']}/{contexto['ano_novo']} "
            f"({contexto['label_novo']}).\n"
            f"O arquivo base é de {contexto['mes_base_nome']}/{contexto['ano_base']} "
            f"({contexto['label_anterior']}).\n\n"
            "PADRÕES DE FORMATAÇÃO DO ARQUIVO BASE — siga-os fielmente:\n"
            f"  - Datas na capa: {contexto.get('formato_data_capa', 'N/A')}\n"
            f"  - Datas abreviadas: {contexto.get('formato_data_abrev', 'N/A')}\n"
            f"  - Percentual positivo: {contexto.get('formato_percentual_positivo', 'N/A')}\n"
            f"  - Percentual negativo: {contexto.get('formato_percentual_negativo', 'N/A')}\n"
            f"  - Valor total: {contexto.get('formato_valor_total', 'N/A')}\n"
            f"  - Valor tabela: {contexto.get('formato_valor_tabela', 'N/A')}\n"
            f"  - Separador decimal: {contexto.get('separador_decimal', ',')}\n"
            f"  - Separador milhar: {contexto.get('separador_milhar', '.')}\n"
            f"  - Casas decimais percentual: {contexto.get('casas_decimais_pct', 1)}\n"
            f"  - Símbolo moeda: {contexto.get('simbolo_moeda', 'R$')}\n"
            f"  - Unidade de valor: {contexto.get('unidade_valor', 'MM')}\n\n"
            "Use esses padrões como referência de formatação. Para datas e períodos,\n"
            "deduza as substituições necessárias lendo o conteúdo do PPTX base abaixo.\n\n"
        )

    user_message = (
        f"{bloco_contexto}"
        "=== DADOS DO EXCEL (mês atual) ===\n"
        f"{dados_json}\n\n"
        "=== ESTRUTURA DO PPTX (mês anterior) ===\n"
        f"{resumo_pptx}\n\n"
        "Gere o plano de edição para atualizar o PPTX com os dados do mês atual."
    )

    logger.info("Mapper: user_message=%d chars", len(user_message))

    # 3. Parsear o plano (com retry em caso de resposta inválida ou truncada)
    for tentativa in range(3):
        resposta, finish_reason = llm.chat_with_finish(SYSTEM_PROMPT_MAPPER, user_message,
                                                        model=_modelo("pptx_mapper"))

        if resposta.startswith("ERRO_LLM"):
            logger.error("LLM retornou erro no mapper (tentativa %d): %s", tentativa + 1, resposta)
            break

        logger.info("Mapper resposta LLM (tentativa %d): %d chars, finish=%s",
                    tentativa + 1, len(resposta), finish_reason)

        # Se a resposta foi truncada, retenta diretamente
        if finish_reason == "length":
            logger.warning("Resposta truncada (finish_reason=length). Retentando...")
            if tentativa < 2:
                continue
            # Última tentativa: tentar recuperar o que tiver

        try:
            plano = _parse_plano_resposta(resposta)
            if not plano:
                logger.warning("Plano retornou lista vazia (tentativa %d).", tentativa + 1)
                if tentativa < 2:
                    logger.info("Retentando mapper...")
                    continue
            # Filter out no-op actions where valor_antigo == valor_novo
            plano_filtrado = [
                a for a in plano
                if a.get("valor_antigo", "") != a.get("valor_novo", "")
            ]
            n_removed = len(plano) - len(plano_filtrado)
            if n_removed > 0:
                logger.info("Removidas %d ações no-op (valor_antigo == valor_novo).", n_removed)
            logger.info("Plano de edição gerado com %d ação(ões).", len(plano_filtrado))
            return plano_filtrado
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "Falha ao parsear plano (tentativa %d/%d): %s\nResposta (500 chars): %s",
                tentativa + 1, 3, e, resposta[:500],
            )
            if tentativa < 2:
                logger.info("Retentando mapper...")

    return []


def _parse_plano_resposta(resposta: str) -> list[dict]:
    """Extrai lista JSON de ações da resposta do LLM."""
    texto = resposta.strip()

    # Remove todos os blocos de markdown ``` independente de posição
    import re
    texto = re.sub(r"```[a-zA-Z]*\n?", "", texto).strip()

    # Tenta parse direto primeiro (resposta já é JSON puro)
    try:
        resultado = json.loads(texto)
        if isinstance(resultado, list):
            return resultado
        if isinstance(resultado, dict):
            # Procura o primeiro valor que seja uma lista
            for v in resultado.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError:
        pass

    # Localiza o maior array JSON válido na resposta
    inicio = texto.find("[")
    if inicio == -1:
        raise ValueError("Nenhum array JSON encontrado na resposta do LLM")

    fim = texto.rfind("]") + 1
    if fim == 0:
        # JSON truncado (sem ] final) — tentar recuperar
        # Encontrar último } completo e fechar o array
        ultimo_obj = texto.rfind("}")
        if ultimo_obj == -1:
            raise ValueError("Nenhum array JSON encontrado na resposta do LLM")
        candidato = texto[inicio:ultimo_obj + 1].rstrip().rstrip(",") + "]"
        try:
            resultado = json.loads(candidato)
            if isinstance(resultado, list):
                logger.warning("JSON truncado recuperado: %d ação(ões) extraídas.", len(resultado))
                return resultado
        except json.JSONDecodeError:
            raise ValueError("JSON truncado e irrecuperável na resposta do LLM")

    resultado = json.loads(texto[inicio:fim])
    if not isinstance(resultado, list):
        raise ValueError(f"Esperado lista, recebido {type(resultado)}")
    return resultado
