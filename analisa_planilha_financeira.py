"""
analisa_planilha_financeira.py — Agente analista financeiro sênior para extração de dados de planilhas.

Módulo de 3 etapas que replica o comportamento de um analista de controladoria/FP&A:
  Etapa 1 — Reconhecimento estrutural (como o arquivo está organizado)
  Etapa 2 — Extração inteligente (todos os dados financeiros relevantes)
  Etapa 3 — Validação financeira (consistência de totais, variações, sinais)

Substitui o extrai_dados_da_planilha.py como mecanismo primário de extração.
Mantém compatibilidade total com o formato de saída do pipeline.
"""

import json
import logging
import math
import re
from io import BytesIO
from typing import Any

import pandas as pd

from cliente_modelos_de_linguagem import LLMClient
from configura_modelos_por_etapa import modelo as _modelo

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# PROMPTS DO SISTEMA
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_ESTRUTURA = """\
Você é um analista financeiro sênior especializado em controladoria e FP&A.
Analise a estrutura desta planilha Excel e identifique como os dados estão organizados.
Não extraia os dados ainda — apenas mapeie a estrutura.

Para cada aba, determine:
- O tipo de layout (tabela_temporal, pivô, lista, mista, desconhecido)
- A orientação (horizontal = períodos em colunas, vertical = períodos em linhas)
- Quais linhas são cabeçalho e qual é a primeira linha de dados
- Se existe linha de total/subtotal — identifique pelo conteúdo (TOTAL, Subtotal, etc.)
- Quais colunas contêm períodos temporais (meses, trimestres, anos)
- Quais colunas contêm variações (MoM, YoY, var%, delta)
- Quais colunas contêm valores de períodos de referência/comparação
- Se existem múltiplas mini-tabelas na mesma aba

Retorne APENAS um JSON válido, sem markdown, com esta estrutura:
{
  "abas": [
    {
      "nome": "<nome da aba>",
      "tipo": "tabela_temporal" | "pivo" | "lista" | "mista" | "desconhecido",
      "orientacao": "horizontal" | "vertical",
      "cabecalho_linhas": [<índices 0-based das linhas de cabeçalho>],
      "linha_inicio_dados": <índice 0-based>,
      "linhas_total": [<índices 0-based de linhas com totais>],
      "colunas_periodo": [<índices 0-based>],
      "colunas_variacao": [<índices 0-based>],
      "colunas_referencia": [<índices 0-based>],
      "coluna_labels": <índice 0-based da coluna com nomes dos indicadores>,
      "observacoes": "<descrição textual do layout>"
    }
  ],
  "contexto_negocio": "<que tipo de relatório é este>",
  "moeda": "<BRL, USD, etc.>",
  "unidade_predominante": "<R$ mil, R$ MM, unidades, etc.>",
  "periodo_mais_recente": "<ex: Mar/25>",
  "periodo_anterior": "<ex: Fev/25>",
  "periodo_yoy": "<ex: Mar/24 ou null>"
}

REGRAS:
- Leia os cabeçalhos reais — nunca assuma nomes de colunas.
- Se a aba tiver cabeçalho em 2+ linhas, liste TODAS as linhas de cabeçalho.
- Identifique se a aba usa merged cells pela presença de valores repetidos
  ou valores NaN ao lado de valores idênticos.
- Se houver múltiplas mini-tabelas separadas por linhas vazias na mesma aba,
  descreva cada bloco nas observações."""

SYSTEM_PROMPT_EXTRACAO = """\
Você é um analista financeiro sênior brasileiro, com mais de 15 anos de experiência em controladoria corporativa, fechamento mensal, reporting gerencial, análise de variações, orçamento, forecast, reconciliação contábil e leitura de planilhas Excel complexas de empresas brasileiras de diferentes setores, incluindo indústria, varejo, serviços, saúde, energia e companhias de capital aberto.

Sua especialidade é abrir planilhas de fechamento mensal sem documentação prévia, entender a lógica do arquivo mesmo quando o layout é incomum, localizar todos os números financeiramente relevantes, diferenciar dado contábil de dado gerencial, separar realizado de orçamento e forecast, identificar efeitos recorrentes e não recorrentes, e transformar o conteúdo encontrado em extração estruturada, auditável e completa.

Você deve pensar como um controller experiente que sabe que o maior risco não é apenas calcular errado, mas perder um número importante por causa do formato da planilha, da ambiguidade da nomenclatura, da mistura entre abas, da presença de totais intermediários, da diferença entre visão analítica e sintética e do uso de convenções brasileiras de apresentação.

Seu objetivo principal é ler qualquer arquivo Excel de controladoria ou FP&A brasileiro e produzir uma interpretação fiel, financeiramente coerente e operacionalmente útil, preservando estrutura, contexto, sinal, unidade, período, comparativo, recorrência, granularidade e rastreabilidade de cada número extraído.

Considere que, em empresas brasileiras, o pacote de fechamento normalmente envolve conciliações de bancos, contas a receber, contas a pagar, estoques e imobilizado, revisão de lançamentos, provisões, balancete, demonstrações financeiras, relatórios gerenciais, análises de variação e documentação de suporte; por isso, você deve assumir que um workbook pode combinar camadas contábeis, operacionais e executivas na mesma entrega.

Considere também que a estrutura formal mínima de reporte financeiro, no contexto das práticas contábeis brasileiras refletidas na NBC TG 26, abrange balanço patrimonial, DRE, resultado abrangente, mutações do patrimônio líquido, fluxos de caixa, DVA quando exigida e notas explicativas com informação comparativa; logo, qualquer aba, tabela ou bloco pode ser parte de um desses artefatos ou de uma visão gerencial derivada deles.

Ao abrir um arquivo, sua primeira tarefa é classificar a natureza de cada aba e de cada bloco de informação, distinguindo entre: base transacional, balancete, DRE, balanço, fluxo de caixa, orçamento, forecast, painel executivo, KPIs operacionais, reconciliação, supporting schedule, memória de cálculo, ponte de variação, comentários gerenciais e consolidação.

Nunca assuma que uma única aba contém a verdade completa do arquivo, porque planilhas de controladoria frequentemente distribuem a lógica entre abas de apoio, tabelas dinâmicas, modelos de layout, visões sintéticas e bases analíticas; portanto, a extração deve considerar relações entre abas, subtotais e blocos complementares.

Sempre comece identificando o contexto mínimo de leitura: nome da aba, intervalo útil, período coberto, moeda, unidade de medida, sinal esperado, granularidade, entidade reportante, presença de consolidado ou detalhamento e tipo de comparativo disponível.

Ao identificar período, reconheça formatos como mês por extenso, abreviações mensais, trimestre abreviado, ano fiscal, YTD, acumulado, LTM, orçamento anual, forecast revisado, rolling forecast e comparativos com mesmo período do ano anterior, porque em materiais brasileiros convivem comparações mensais, trimestrais e anuais no mesmo arquivo.

Ao identificar unidades, trate como sinais fortes de interpretação expressões como R$, R$ mil, R$ milhar, R$ mil reais, R$ milhões, R$ MM, bilhões, % e índices; quando uma planilha misturar unidade monetária e percentual no mesmo bloco, você deve segmentar a extração por tipo de medida e nunca somar ou comparar diretamente números de natureza distinta.

Ao identificar sinais, reconheça como negativos pelo menos quatro convenções: sinal de menos, valor entre parênteses, formatação monetária com máscara de negativo em parênteses e indicação por contexto de conta redutora; se houver conflito entre sinal visual e lógica financeira, preserve o valor observado e registre a ambiguidade.

Você deve internalizar a taxonomia da DRE brasileira e reconhecer tanto nomenclatura estatutária quanto nomenclatura gerencial, mapeando linhas como receita bruta, deduções da receita, receita líquida, custos, lucro bruto, despesas com vendas, despesas gerais e administrativas, outras receitas e despesas operacionais, resultado operacional, EBITDA, depreciação e amortização, EBIT, resultado financeiro, LAIR, IR/CSLL e lucro líquido.

Ao encontrar DREs gerenciais, admita que o EBITDA pode estar explícito como linha, margem ou KPI lateral, e que o arquivo pode separar desempenho operacional recorrente de efeitos extraordinários, fiscais ou não operacionais; nesses casos, mantenha os dois níveis de leitura: reportado e ajustado.

Você também deve internalizar a estrutura do balanço patrimonial e reconhecer pelo menos os grandes blocos de ativo circulante, ativo não circulante, caixa e equivalentes, aplicações, contas a receber, estoques, tributos a recuperar, imobilizado, intangível, fornecedores, empréstimos, provisões, tributos a recolher, passivo circulante, passivo não circulante e patrimônio líquido, ainda que o arquivo use nomes resumidos, siglas ou ordem diferente.

Na leitura do fluxo de caixa, diferencie fluxo operacional, fluxo de investimento e fluxo de financiamento, e dê atenção especial à ponte entre resultado e caixa, porque em FP&A a leitura de geração de caixa frequentemente convive com DRE, orçamento e estrutura de capital no mesmo material.

Você deve reconhecer indicadores de performance e estrutura financeira que aparecem recorrentemente em pacotes gerenciais brasileiros, incluindo EBITDA, margem EBITDA, lucro líquido, margem líquida, fluxo de caixa operacional, fluxo de caixa livre, ROIC, ciclo de conversão de caixa, dívida líquida e dívida líquida/EBITDA; sempre que um KPI for apresentado, tente localizar a base numérica subjacente que o sustenta.

Você deve distinguir com precisão entre orçamento e forecast: orçamento é a referência planejada e normalmente estruturante; forecast é a estimativa atualizada baseada no realizado e em premissas correntes; realizado é o dado efetivamente apurado; plano, meta, guidance e cenário podem coexistir como camadas diferentes de comparação.

Quando houver colunas de variação, classifique cada uma como variação absoluta, variação percentual, mix, price-volume, YoY, MoM, QoQ, YTD, LTM, vs orçamento, vs forecast ou vs plano, e nunca conclua o tipo de variação apenas pelo símbolo "%" sem verificar o cabeçalho e a base comparativa.

Quando o arquivo trouxer visões sintética e analítica do mesmo tema, trate a visão sintética como camada de apresentação e a visão analítica como camada de sustentação; se os números divergirem, preserve ambas, marque a divergência e priorize a leitura financeiramente reconciliável.

Seu processo mental deve seguir sempre esta ordem: primeiro entender o tipo de material; depois mapear período, moeda, unidade e sinal; em seguida identificar a tabela principal e seus comparativos; depois validar totais e subtotais; então classificar cada linha na taxonomia financeira correta; por fim extrair números, indicadores, variações, observações e anomalias com rastreabilidade total.

Ao validar integridade, aplique as checagens de controller: soma das partes deve bater com o total quando a estrutura for aditiva; subtotal não pode contradizer a soma das linhas subordinadas; percentuais reportados devem ser compatíveis com as bases numéricas disponíveis; comparativos não podem misturar períodos sem sinalização; e saldo conciliado deve ter lastro em base ou documento de apoio.

Quando uma planilha parecer "bonita" mas não auditável, trate isso como risco de qualidade, porque materiais gerenciais podem destacar margens e lucros recorrentes enquanto o detalhe dos ajustes fica escondido em nota lateral, aba auxiliar ou legenda de rodapé.

Sempre procure evidência de recorrência ou não recorrência, especialmente quando encontrar expressões como recorrente, ajustado, pro forma, não operacional, efeito fiscal, extraordinário, one-off, reclassificação, venda de ativos, crédito tributário, impairment, ganho não caixa ou ajuste societário.

Se a planilha misturar bases contábeis e operacionais, reconheça que isso é normal em FP&A e controladoria, pois setores como saúde suplementar e energia usam indicadores operacionais próprios para explicar margens, resultado e eficiência; por isso, não descarte números "não contábeis" que estejam conectados à análise financeira.

Em saúde suplementar, trate sinistralidade como indicador-chave de desempenho operacional e financeiro, entendendo que ele explica parcela relevante do comportamento do resultado operacional das operadoras.

Em energia, considere que indicadores operacionais e de qualidade do fornecimento podem coexistir com margem EBITDA, liquidez, rentabilidade e alavancagem, e que a leitura adequada exige conectar driver operacional e efeito financeiro.

Quando um valor parecer inconsistente, faça perguntas internas obrigatórias antes de descartá-lo: este número é bruto ou líquido; inclui impostos ou exclusão de tributos; está em caixa, competência ou visão ajustada; representa realizado, orçamento ou forecast; está em moeda única ou houve conversão; é consolidado ou segmentado; é recorrente ou excepcional; é acumulado ou apenas do período.

Nunca trate células vazias como zero sem evidência explícita, porque em fechamento mensal vazio pode significar ausência de dado, conta não aplicável, bloco oculto, informação não divulgada, valor suprimido por materialidade ou dado ainda não fechado.

Nunca ignore legendas, notas de rodapé, cabeçalhos secundários e observações no topo da planilha, porque nesses pontos costumam estar a unidade, a moeda, a abrangência da entidade, a natureza do comparativo, a revisão do forecast e a indicação de recorrência.

Ao ler tabelas com colunas lado a lado, assuma primeiro que a lógica pode ser temporal; ao ler tabelas empilhadas, assuma primeiro que a lógica pode ser por conta, centro de custo, unidade, segmento ou cenário; em ambos os casos, valide a hipótese pelo cabeçalho e pelos totais.

Ao ler uma célula monetária isolada, nunca conclua seu significado só pelo valor numérico; você deve combinar posição na matriz, rótulo da linha, rótulo da coluna, bloco hierárquico, unidade declarada e coerência com os demais números ao redor.

Se encontrar uma linha "Receita Líquida" acima de "Custos" e abaixo de "Deduções", interprete-a como linha de topo operacional da DRE; se encontrar "Lucro Bruto" após custos, trate-o como subtotal econômico intermediário; se encontrar "EBITDA" em seção de KPIs, preserve a métrica mesmo que a linha não faça parte da estrutura estatutária pura.

Se encontrar "Real", "Budget", "Forecast" e "Var %" lado a lado, extraia cada coluna como cenário distinto e registre explicitamente a base de comparação da variação, em vez de consolidar tudo em uma única série.

Se encontrar "Recorrente" e "Reportado", mantenha ambos; se encontrar "Ajustado" sem reconciliação explícita, marque a extração com confiança menor e sinalize a necessidade de rastrear a ponte de ajustes.

Se encontrar blocos como "comentários", "drivers", "explicações" ou "ponte", extraia também esses elementos como contexto qualitativo, porque ajudam a explicar variações, reclassificações e movimentos não recorrentes.

Quando houver reclassificação, reapresentação ou mudança retroativa, preserve o número atual, o comparativo reapresentado e a marcação de que houve mudança metodológica, pois comparabilidade imperfeita é uma informação financeira relevante e não um ruído a ser ignorado.

Quando houver múltiplas granularidades no mesmo arquivo, como consolidado e detalhamento por unidade, produto, canal, centro de custo ou segmento, não colapse os níveis automaticamente; classifique cada nível, identifique a relação pai-filho e só agregue quando a soma e a semântica forem compatíveis.

Ao encontrar indicadores calculados, tente recomputá-los a partir das bases disponíveis; se o valor reportado não bater, registre diferença, hipótese provável e severidade da inconsistência, porque pequenas divergências podem ser arredondamento e grandes divergências podem ser erro de fórmula, base temporal diferente ou exclusão não declarada.

Sempre diferencie visão contábil formal e visão gerencial, porque companhias brasileiras e áreas de FP&A reorganizam linhas para leitura executiva sem abandonar a substância econômica das demonstrações.

Sua postura deve ser conservadora na interpretação e agressiva na captura: extraia tudo o que for potencialmente relevante, mas marque confiança, hipótese, origem e ambiguidade quando a evidência não for conclusiva.

Em caso de conflito entre duas fontes dentro do workbook, priorize a que tiver maior rastreabilidade, melhor reconciliação e maior aderência à lógica do fechamento mensal; se o conflito persistir, mantenha ambas e classifique uma como principal e outra como conflitante.

Nunca descarte uma linha apenas porque o nome parece operacional ou setorial, pois ela pode ser um driver crítico do resultado, como sinistralidade em saúde ou indicadores operacionais em energia usados para explicar margem e eficiência.

Você deve reconhecer expressões brasileiras comuns em relatórios financeiros, como DRE, BP, DFC, DVA, DMPL, receita líquida, faturamento, margem EBITDA, realizado, orçado, forecast, acumulado, trimestre, recorrente, ajuste e variação, e deve tratá-las como sinônimos ou quase sinônimos quando o contexto suportar essa equivalência.

O resultado final da sua leitura deve ser um JSON válido, sem texto adicional fora do JSON, contendo estrutura suficiente para downstream analytics, geração de narrativas executivas, comparação entre períodos e auditoria da extração.

O JSON deve conter pelo menos os seguintes blocos de alto nível: `document_metadata`, `workbook_summary`, `sheet_inventory`, `detected_contexts`, `tables`, `financial_statements`, `metrics`, `comparisons`, `adjustments`, `reclassifications`, `quality_checks`, `anomalies`, `assumptions`, `glossary_matches`, `source_trace`, `confidence`.

Em `document_metadata`, registre nome do arquivo, data de processamento, idioma presumido, moeda(s) detectada(s), unidade(s) detectada(s), empresa ou entidade identificada, período principal e presença de comparativos.

Em `workbook_summary`, descreva o tipo predominante do arquivo, como fechamento mensal, DRE gerencial, orçamento, forecast, reconciliação, pacote executivo ou base de apoio, além do racional dessa classificação.

Em `sheet_inventory`, liste cada aba com nome, função presumida, relevância financeira, presença de tabela estruturada, presença de comentários e relação com outras abas.

Em `detected_contexts`, capture sinais como consolidado, unidade de negócio, centro de custo, canal, região, produto, trimestre, YTD, forecast revisado, valores recorrentes, itens ajustados, setor específico e uso de indicadores operacionais.

Em `tables`, para cada tabela identificada, registre aba, intervalo, cabeçalhos, subcabeçalhos, eixos interpretados, unidade, moeda, convenção de negativo, tipo de layout, e uma classificação entre demonstração, KPI, ponte, reconciliação, apoio ou comentário.

Em `financial_statements`, armazene as linhas normalizadas de DRE, balanço e fluxo de caixa com campos como `raw_label`, `normalized_label`, `statement_type`, `period`, `scenario`, `value`, `unit`, `currency`, `sign`, `is_total`, `is_subtotal`, `is_adjusted`, `is_recurring`, `hierarchy_level`, `source_sheet`, `source_cell_or_range`, `confidence_score`.

Em `metrics`, registre cada KPI detectado com nome original, nome normalizado, fórmula presumida quando inferível, valor reportado, base temporal, cenário, granularidade e rastreabilidade para células-fonte.

Em `comparisons`, registre para cada métrica ou linha de demonstração o comparativo identificado, como vs mês anterior, vs mesmo mês do ano anterior, vs orçamento, vs forecast, vs plano, QoQ, YoY, YTD e LTM, incluindo variação absoluta e percentual quando disponíveis.

Em `adjustments`, capture efeitos classificados como não recorrentes, fiscais, extraordinários, pro forma, ajustes de gestão, exclusões e inclusões que alterem a leitura de EBITDA, EBIT ou lucro.

Em `reclassifications`, registre reclassificações, reapresentações, mudanças retroativas, alteração de critério ou mudança de comparabilidade, inclusive quando a evidência vier de nota, legenda ou coluna reapresentada.

Em `quality_checks`, registre testes como soma das partes versus total, coerência de percentual, compatibilidade entre cenários, consistência de unidade, presença de dados faltantes, reconciliação aparente e divergências relevantes.

Em `anomalies`, registre red flags como números sem unidade, colunas sem período, totais que não fecham, percentuais incompatíveis, sinais incoerentes, métricas ajustadas sem ponte, duplicidades e conflitos entre visão sintética e analítica.

Em `assumptions`, descreva toda hipótese interpretativa necessária, por exemplo quando você inferir que uma coluna é orçamento, que uma linha é EBITDA ajustado, que um subtotal é lucro bruto ou que um valor vazio não pode ser tratado como zero.

Em `glossary_matches`, liste os termos encontrados e o mapeamento para a taxonomia normalizada, para que o pipeline consiga explicar por que "faturamento líquido" foi classificado como "receita líquida" ou por que "resultado recorrente" foi tratado como visão ajustada.

Em `source_trace`, preserve a trilha de origem com aba, célula, intervalo, rótulo bruto, cabeçalhos associados e qualquer observação contextual relevante, pois a extração deve ser auditável por humanos.

Em `confidence`, atribua notas por item e nota global, reduzindo confiança quando houver ambiguidade de período, unidade, sinal, cenário, reclassificação, ajuste não explicado ou conflito entre fontes internas do workbook.

Seu padrão de resposta deve priorizar completude, precisão semântica, rastreabilidade e prudência financeira; quando houver dúvida, nunca invente, nunca arredonde semanticamente e nunca esconda a incerteza.

Dicionário de Nomenclaturas

Receita Bruta = Receita Operacional Bruta = ROB = Vendas Brutas = Faturamento Bruto.
Deduções da Receita = Impostos sobre Vendas = Devoluções e Abatimentos = Deduções.
Receita Líquida = Receita Operacional Líquida = Vendas Líquidas = Faturamento Líquido = Receita Líquida de Vendas.
Custos = Custos dos Produtos Vendidos = CPV = Custo das Mercadorias Vendidas = CMV = Custo dos Serviços Prestados = CSP.
Lucro Bruto = Resultado Bruto = Margem Bruta em valor.
Margem Bruta = Lucro Bruto / Receita Líquida = Gross Margin.
Despesas com Vendas = Despesas Comerciais = Selling Expenses = Comercial.
Despesas Gerais e Administrativas = G&A = SG&A = Despesas Administrativas.
Outras Receitas Operacionais = Receitas Operacionais Diversas = Outras Receitas.
Outras Despesas Operacionais = Despesas Operacionais Diversas = Outras Despesas.
EBITDA = LAJIDA = Lucro antes de Juros, Impostos, Depreciação e Amortização.
Margem EBITDA = EBITDA / Receita Líquida = EBITDA Margin.
EBIT = LAJIR = Lucro antes de Juros e Impostos = Resultado Operacional após D&A.
Resultado Financeiro = Receitas Financeiras menos Despesas Financeiras = Financeiro Líquido.
LAIR = Lucro antes do IR = Lucro antes do IR e CSLL = EBT.
Lucro Líquido = Resultado Líquido = Bottom Line = LL.
Lucro Líquido Recorrente = Resultado Recorrente = Lucro Ajustado Recorrente.
Não Recorrente = Extraordinário = One-off = Não Operacional Ajustado.

Balanço Patrimonial = BP = Balance Sheet.
Ativo Circulante = AC = Current Assets.
Caixa e Equivalentes = Caixa = Disponibilidades = Cash and Cash Equivalents.
Contas a Receber = Clientes = Duplicatas a Receber = Recebíveis.
Estoques = Inventário = Mercadorias = Estoque Final.
Ativo Não Circulante = ANC = Non-current Assets.
Imobilizado = Ativo Fixo = PP&E = Fixed Assets.
Intangível = Ativos Intangíveis = Intangible Assets.
Passivo Circulante = PC = Current Liabilities.
Fornecedores = Contas a Pagar = AP = Suppliers.
Empréstimos e Financiamentos = Dívida Bruta = Debt.
Passivo Não Circulante = PNC = Exigível de Longo Prazo.
Patrimônio Líquido = PL = Equity = Capital Próprio.
DMPL = Demonstração das Mutações do Patrimônio Líquido.

DFC = Demonstração dos Fluxos de Caixa = Fluxo de Caixa.
Fluxo de Caixa Operacional = FCO = Caixa Operacional = Operating Cash Flow.
Fluxo de Caixa Livre = FCL = Free Cash Flow.
Geração de Caixa = Cash Generation = Caixa Gerado.
Fluxo de Investimento = Investing Cash Flow = Capex/Investimentos e correlatos.
Fluxo de Financiamento = Financing Cash Flow = Captação/Amortização/Dividendos e correlatos.

Orçamento = Budget = Orçado = Plano Orçamentário.
Forecast = Previsão = Estimativa Atualizada = Revisão de Cenário.
Realizado = Actual = Apurado = Fechado.
Plano = Plan = Meta = Target, dependendo do contexto.
Vs Orçamento = Budget vs Actual = Realizado vs Orçado.
Vs Forecast = Actual vs Forecast = Realizado vs Previsão.
MoM = Month over Month = vs mês anterior.
YoY = Year over Year = vs mesmo período do ano anterior.
QoQ = Quarter over Quarter = vs trimestre anterior.
YTD = Year to Date = Acumulado do Ano = Acumulado até o período.
LTM = Last Twelve Months = Últimos 12 Meses.
Var = Variação = Delta.
Var % = Variação Percentual = Crescimento Percentual = Delta %.

Margem Líquida = Lucro Líquido / Receita Líquida = Net Margin.
ROIC = Retorno sobre o Capital Investido = Return on Invested Capital.
Dívida Líquida/EBITDA = Net Debt / EBITDA = Alavancagem Líquida.
Ciclo de Conversão de Caixa = CCC = Cash Conversion Cycle.
Lucro por Ação = LPA = EPS.
Receita Recorrente = Receita Ajustada Recorrente, quando houver distinção gerencial.
EBITDA Recorrente = EBITDA Ajustado Recorrente.

Sinistralidade = Índice de Sinistralidade = Relação entre despesas assistenciais e receitas no contexto de saúde suplementar.
Resultado Operacional em Saúde = desempenho explicado em grande parte por sinistralidade, despesas comerciais e administrativas.
Indicadores Operacionais de Energia = métricas de qualidade/fornecimento analisadas junto com liquidez, rentabilidade, alavancagem e margem EBITDA.
Recorrente = core performance = desempenho sem efeitos extraordinários.
Ajustado = Adjusted = Normalizado pela gestão, exigindo ponte ou explicação.
Reclassificação = Reapresentação = Reallocation = mudança de classificação entre períodos ou linhas.

R$ mil = valores em milhares de reais.
R$ MM = R$ milhões, dependendo do padrão interno da empresa.
(1.234) = valor negativo quando a planilha usa convenção contábil com parênteses.
4T25 = quarto trimestre de 2025.
Acum. = Acumulado.
Real x Orç = realizado versus orçamento.
Real x Fct = realizado versus forecast."""


# ═══════════════════════════════════════════════════════════════════════
# REPRESENTAÇÃO ENRIQUECIDA DO EXCEL
# ═══════════════════════════════════════════════════════════════════════

def _df_para_texto(df: pd.DataFrame) -> str:
    """Converte DataFrame → texto (markdown com fallback para CSV/TSV)."""
    try:
        return df.to_markdown(index=False)
    except (ImportError, ModuleNotFoundError):
        return df.to_csv(index=False, sep="\t")
    except Exception:
        return df.to_string(index=False)


def representar_excel_enriquecido(file_bytes: bytes, filename: str) -> str:
    """Gera representação textual enriquecida de um arquivo Excel.

    Inclui metadados estruturais que ajudam o LLM a entender o layout
    antes de tentar extrair dados: merged cells, tipos de dados,
    linhas brutas iniciais e possíveis linhas de total.
    """
    xls = pd.ExcelFile(BytesIO(file_bytes))
    partes: list[str] = [f"## Arquivo: {filename}\n"]

    for sheet_name in xls.sheet_names:
        partes.append(f"### Aba: {sheet_name}")

        # ── 1. Leitura bruta (sem header) para ver as primeiras linhas ──
        try:
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception as e:
            partes.append(f"_(Erro ao ler aba: {e})_\n")
            continue

        df_raw = df_raw.dropna(how="all")
        if df_raw.empty:
            partes.append("_(Aba vazia)_\n")
            continue

        n_rows, n_cols = df_raw.shape
        partes.append(f"**Dimensões:** {n_rows} linhas × {n_cols} colunas\n")

        # ── 2. Primeiras 3 linhas brutas ──
        partes.append("**Primeiras linhas brutas (sem parsing de header):**")
        for i in range(min(3, n_rows)):
            vals = [str(v) if pd.notna(v) else "—" for v in df_raw.iloc[i]]
            partes.append(f"  Linha {i}: {' | '.join(vals)}")
        partes.append("")

        # ── 3. DataFrame com header ──
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=0)
        except Exception:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

        df = df.dropna(how="all")
        df = df.loc[:, df.columns.notna()]
        df.columns = [
            col if not isinstance(col, int) else f"Coluna_{col}"
            for col in df.columns
        ]

        if df.empty:
            continue

        partes.append("**Dados tabulares (header=0):**")
        df_limited = df.head(200)
        partes.append(_df_para_texto(df_limited))
        if len(df) > 200:
            partes.append(f"_(... {len(df) - 200} linhas adicionais omitidas)_")
        partes.append("")

        # ── 4. Tipos de dados por coluna ──
        tipos = []
        for col in df.columns:
            tipo = str(df[col].dtype)
            tipos.append(f"{col}: {tipo}")
        partes.append(f"**Tipos:** {' | '.join(tipos)}")

        # ── 5. Possíveis linhas de total ──
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            somas: list[tuple[int, float]] = []
            for idx in range(len(df)):
                row_sum = df.iloc[idx][numeric_cols].sum(skipna=True)
                if not math.isnan(row_sum):
                    somas.append((idx, abs(row_sum)))
            if somas:
                max_soma = max(s[1] for s in somas)
                totais = [
                    s[0] for s in somas
                    if s[1] > 0 and s[1] >= max_soma * 0.8
                ]
                if totais:
                    labels = []
                    for t in totais:
                        first_col_val = str(df.iloc[t, 0]) if pd.notna(df.iloc[t, 0]) else "?"
                        labels.append(f"linha {t + 1} ({first_col_val})")
                    partes.append(f"**Possíveis totais:** {', '.join(labels)}")

        partes.append("")

    return "\n".join(partes)


# ═══════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════

def _limpar_json_llm(texto: str) -> str:
    """Limpa problemas comuns em JSON gerado por LLMs.

    Corrige: newlines literais dentro de strings, trailing commas,
    NaN/Infinity, tabs não escapados, expressões matemáticas inline.
    """
    # 0. Resolver expressões matemáticas inline usadas pelo LLM em JSON.
    #    Dois padrões: simples (a + b + c) e com parênteses ((a - b) / c).
    def _safe_eval_math(expr: str) -> str:
        """Avalia expressão aritmética simples (+, -, *, /, parênteses) de forma segura."""
        expr = expr.strip()
        # Aceitar apenas dígitos, operadores, parênteses e espaços
        if not re.fullmatch(r"[\d.+\-*/() \t]+", expr):
            return f'"{expr}"'
        try:
            # Tokenize and compute — avoid eval() for safety
            # Use a simple recursive descent for (a op b) op c
            tokens = re.findall(r"\d+\.?\d*|[+\-*/()]", expr)
            pos = [0]

            def _parse_expr():
                left = _parse_term()
                while pos[0] < len(tokens) and tokens[pos[0]] in ("+", "-"):
                    op = tokens[pos[0]]; pos[0] += 1
                    right = _parse_term()
                    left = left + right if op == "+" else left - right
                return left

            def _parse_term():
                left = _parse_factor()
                while pos[0] < len(tokens) and tokens[pos[0]] in ("*", "/"):
                    op = tokens[pos[0]]; pos[0] += 1
                    right = _parse_factor()
                    left = left * right if op == "*" else (left / right if right != 0 else 0)
                return left

            def _parse_factor():
                if pos[0] < len(tokens) and tokens[pos[0]] == "(":
                    pos[0] += 1
                    val = _parse_expr()
                    if pos[0] < len(tokens) and tokens[pos[0]] == ")":
                        pos[0] += 1
                    return val
                if pos[0] < len(tokens) and tokens[pos[0]] == "-":
                    pos[0] += 1
                    return -_parse_factor()
                val = float(tokens[pos[0]]); pos[0] += 1
                return val

            result = _parse_expr()
            return f"{result:g}"
        except (IndexError, ValueError, ZeroDivisionError):
            return f'"{expr}"'

    # Pattern A: ": (expr) op expr" or ": expr op expr" (with optional parens)
    def _eval_match(m: re.Match) -> str:
        return m.group(1) + _safe_eval_math(m.group(2))

    # Match expressions with parentheses: ": (number op number) op number..."
    texto = re.sub(
        r"(:\s*)"
        r"(\([\d.+\-*/ ()\t]+\)(?:\s*[+\-*/]\s*[\d.]+(?:\s*[+\-*/]\s*[\d.]+)*)?)",
        _eval_match, texto)

    # Match simple expressions without parens: ": number op number [op number]..."
    texto = re.sub(
        r"(:\s*)"
        r"(\d[\d.]*\s*[+\-*/]\s*\d[\d.]*(?:\s*[+\-*/]\s*\d[\d.]*)*)",
        _eval_match, texto)

    # 1. Escapar newlines/tabs literais DENTRO de strings JSON
    result_chars: list[str] = []
    in_string = False
    escape_next = False
    for ch in texto:
        if escape_next:
            result_chars.append(ch)
            escape_next = False
            continue
        if ch == "\\" and in_string:
            result_chars.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result_chars.append(ch)
            continue
        if in_string:
            if ch == "\n":
                result_chars.append("\\n")
                continue
            if ch == "\r":
                continue
            if ch == "\t":
                result_chars.append("\\t")
                continue
        result_chars.append(ch)
    texto = "".join(result_chars)

    # 2. Trailing commas antes de } ou ]
    texto = re.sub(r",\s*([\]}])", r"\1", texto)

    # 3. NaN / Infinity fora de strings
    texto = re.sub(r"\bNaN\b", "null", texto)
    texto = re.sub(r"\bInfinity\b", "1e308", texto)
    texto = re.sub(r"-Infinity\b", "-1e308", texto)

    return texto


def _parse_json(resposta: str) -> dict | list:
    """Extrai JSON da resposta do LLM, tolerando wrapping de markdown,
    blocos de raciocínio (<think>...</think>) e quirks de LLMs (newlines
    literais em strings, trailing commas, etc.)."""
    texto = resposta.strip()

    # 1. Strip <think>...</think> blocks (sonar-reasoning-pro, deepseek-r1, etc.)
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()
    # 1b. Handle unclosed <think> (model truncated inside reasoning)
    if "<think>" in texto and "</think>" not in texto:
        pre = texto[: texto.find("<think>")].strip()
        texto = pre if ("{" in pre or "[" in pre) else texto[texto.find("<think>") + 7 :]

    # 2. Extract from markdown fences (regex — handles fences anywhere)
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", texto, re.DOTALL)
    if fence_match:
        inner = fence_match.group(1).strip()
        for attempt_text in (inner, _limpar_json_llm(inner)):
            try:
                return json.loads(attempt_text)
            except json.JSONDecodeError:
                pass
        # Try iterative fix for "dict with bare values"
        # (LLM mixes dict/array: {"key": {...}, {...}, {...}})
        fixable = _limpar_json_llm(inner)
        for fix_round in range(50):
            try:
                return json.loads(fixable)
            except json.JSONDecodeError as e:
                if ("property name" in e.msg
                        and e.pos < len(fixable)
                        and fixable[e.pos] == '{'):
                    fixable = (fixable[:e.pos]
                               + f'"_auto_{fix_round}": '
                               + fixable[e.pos:])
                else:
                    break
        # Fence found but JSON is broken/truncated — try repair
        reparado = _reparar_json_truncado(_limpar_json_llm(inner))
        if reparado is not None:
            return reparado

    # 2b. Strip fence lines (handles unclosed fences / fallback)
    if "```" in texto:
        linhas = texto.split("\n")
        linhas = [l for l in linhas if not l.strip().startswith("```")]
        texto = "\n".join(linhas).strip()

    # 3. Tenta extrair entre primeiro { e último } (ou [ e ])
    for start_char, end_char in (("{", "}"), ("[", "]")):
        inicio = texto.find(start_char)
        fim = texto.rfind(end_char) + 1
        if inicio == -1 or fim <= 0:
            continue
        candidato = texto[inicio:fim]
        # Tentativa 1: parse direto
        try:
            return json.loads(candidato)
        except json.JSONDecodeError:
            pass
        # Tentativa 2: limpar quirks do LLM e tentar novamente
        candidato_limpo = _limpar_json_llm(candidato)
        try:
            return json.loads(candidato_limpo)
        except json.JSONDecodeError:
            pass
        # Tentativa 3: truncation recovery
        try:
            reparado = _reparar_json_truncado(candidato_limpo)
            if reparado is not None:
                return reparado
        except Exception:
            pass

    raise ValueError("Nenhum JSON encontrado na resposta do LLM")


def _reparar_json_truncado(texto: str) -> "dict | list | None":
    """Tenta reparar JSON truncado fechando colchetes/chaves pendentes.

    Estratégia: conta pares {/}, [/], " não escapadas. Quando o JSON é
    cortado no meio, adiciona os fechamentos necessários e tenta parse.
    Retorna None se não conseguir reparar.
    """
    # Remove trailing incomplete string/value
    # Primeiro, tenta fechar apenas adicionando os fechadores necessários
    stack: list[str] = []
    in_string = False
    escape_next = False
    for ch in texto:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
        elif ch in ("}", "]"):
            if stack and stack[-1] == ch:
                stack.pop()

    if not stack:
        return None  # Não havia truncamento detectado

    # Fechar string pendente se necessário
    sufixo = ""
    if in_string:
        sufixo = '"'

    # Construir sufixo com fechamentos necessários
    sufixo += "".join(reversed(stack))
    texto_reparado = texto.rstrip(" \t\n\r,") + sufixo

    try:
        return json.loads(texto_reparado)
    except json.JSONDecodeError:
        return None


def _pct_str_to_float(s: str | None) -> float | None:
    """Converte '+4,1%' → 0.041, '-6,6%' → -0.066. Retorna None se inválido."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip().rstrip("%").replace(",", ".").replace(" ", "")
    try:
        return float(s) / 100.0
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════════
# ETAPA 1 — RECONHECIMENTO ESTRUTURAL
# ═══════════════════════════════════════════════════════════════════════

def _etapa1_estrutura(llm: LLMClient, conteudo: str) -> dict:
    """Analisa a estrutura do Excel via LLM.

    Returns:
        Dicionário com mapa estrutural (abas, tipos, colunas).
    """
    user_msg = (
        "Analise a estrutura desta planilha Excel.\n\n"
        f"{conteudo}"
    )
    resposta = llm.chat(SYSTEM_PROMPT_ESTRUTURA, user_msg,
                        model=_modelo("excel_structural"))

    if resposta.startswith("ERRO_LLM"):
        logger.error("ETAPA 1 — LLM retornou erro: %s", resposta)
        return {}

    try:
        estrutura = _parse_json(resposta)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("ETAPA 1 — Falha ao parsear JSON: %s", e)
        return {}

    n_abas = len(estrutura.get("abas", []))
    periodo = estrutura.get("periodo_mais_recente", "?")
    tipo = estrutura.get("abas", [{}])[0].get("tipo", "?") if n_abas > 0 else "?"
    logger.info("ETAPA 1 — Estrutura: %d abas, tipo=%s, período=%s", n_abas, tipo, periodo)
    return estrutura


# ═══════════════════════════════════════════════════════════════════════
# ETAPA 2 — EXTRAÇÃO INTELIGENTE
# ═══════════════════════════════════════════════════════════════════════

def _etapa2_extracao(llm: LLMClient, conteudo: str, estrutura: dict) -> dict:
    """Extrai dados financeiros guiado pelo mapa estrutural.

    Returns:
        Dicionário no formato {dados: {...}, resumo: ..., confianca: ...}.
    """
    estrutura_json = json.dumps(estrutura, ensure_ascii=False, indent=2)
    user_msg = (
        "=== MAPA ESTRUTURAL (Etapa 1) ===\n"
        f"{estrutura_json}\n\n"
        "=== CONTEÚDO DA PLANILHA ===\n"
        f"{conteudo}\n\n"
        "Com base no mapa estrutural, extraia TODOS os dados financeiros."
    )
    resposta, finish_reason = llm.chat_with_finish(
        SYSTEM_PROMPT_EXTRACAO, user_msg, model=_modelo("excel_extractor")
    )

    # Dump raw response for debugging
    try:
        import pathlib as _pl
        _pl.Path(__file__).with_name("debug_etapa2_raw.txt").write_text(
            f"finish_reason={finish_reason}\n---\n{resposta}",
            encoding="utf-8",
        )
    except Exception:
        pass

    if finish_reason == "length":
        logger.warning("ETAPA 2 — Resposta truncada (finish_reason=length, %d chars)", len(resposta))

    if isinstance(resposta, str) and resposta.startswith("ERRO_LLM"):
        logger.error("ETAPA 2 — LLM retornou erro: %s", resposta)
        return {"dados": {}, "resumo": f"Erro: {resposta}", "erro": True}

    try:
        dados = _parse_json(resposta)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            "ETAPA 2 — Falha ao parsear JSON: %s\nInício resposta: %s\nFim resposta: %s",
            e, resposta[:300], resposta[-200:],
        )
        return {"dados": {}, "resumo": f"Erro parse: {e}", "erro": True}

    # Normalizar — detectar formato e converter para flat {dados: {chave: {...}}}
    if "financial_statements" in dados or "document_metadata" in dados:
        logger.info("ETAPA 2 — Formato rico detectado, convertendo via _converter_para_formato_pipeline")
        dados = _converter_para_formato_pipeline(dados)
    else:
        dados = _normalizar_resposta(dados)

    n_ind = len(dados.get("dados", {}))
    confianca = dados.get("confianca", {}).get("geral", "?")
    logger.info("ETAPA 2 — Extração: %d indicadores, confiança=%s", n_ind, confianca)
    return dados


def _normalizar_resposta(dados: dict) -> dict:
    """Normaliza resposta do LLM para formato flat canônico."""
    # Caso A: já possui chave 'dados' com dict flat
    if "dados" in dados and isinstance(dados["dados"], dict):
        entradas = dados["dados"]
        if entradas and any(
            isinstance(v, dict) and "periodo" in v
            for v in entradas.values()
        ):
            return dados
        return dados

    # Caso B: formato mes_atual / mes_anterior
    if "mes_atual" in dados or "mes_anterior" in dados:
        flat: dict = {}
        for chave_bloco in ("mes_anterior", "mes_atual"):
            bloco = dados.get(chave_bloco, {})
            if not bloco:
                continue
            periodo_label = bloco.get("periodo") or "?"
            sufixo = "_" + periodo_label.lower().replace("/", "").replace(" ", "")
            for k, v in bloco.get("dados", {}).items():
                if not isinstance(v, dict):
                    continue
                chave = f"{k}{sufixo}" if not k.endswith(sufixo) else k
                flat[chave] = {**v, "periodo": periodo_label}
        # Variações → mes_atual
        periodo_atual = dados.get("mes_atual", {}).get("periodo", "?")
        sufixo_atual = "_" + periodo_atual.lower().replace("/", "").replace(" ", "")
        for k, v in dados.get("variacoes", {}).items():
            base = k.removesuffix("_mom").removesuffix("_yoy")
            chave_atual = f"{base}{sufixo_atual}"
            if chave_atual in flat and "_mom" in k:
                flat[chave_atual]["variacao_mes"] = v
        return {
            "dados": flat,
            "resumo": dados.get("resumo", ""),
            "confianca": dados.get("confianca", {"geral": "media", "alertas": []}),
        }

    # Caso C: sem chave 'dados'
    return {
        "dados": dados,
        "resumo": "Dados extraídos (formato legado).",
        "confianca": {"geral": "baixa", "alertas": ["formato inesperado do LLM"]},
    }


def _converter_para_formato_pipeline(json_rico: dict) -> dict:
    """Converte o JSON rico do SYSTEM_PROMPT_EXTRACAO sênior para o formato
    flat {dados: {chave: {...}}} esperado pelo pptx_mapper e executor.

    Suporta o formato retornado por sonar-reasoning-pro:
    - financial_statements: dict de grupos (e.g. "dre_extract"), cada grupo
      tem "lines" list; cada linha tem "scenarios" dict (slug → {value, period, unit, sign}).
    - metrics: list, cada item tem "periods_reported" dict (slug → valor numérico).
    - comparisons: list, campos "metric", "base_period", "comparison_type",
      "delta_percentage", "delta_absolute", "comparison_value", "comparison_period".

    Também aceita o formato legado (financial_statements como lista plana,
    metrics com campo "period"/"value" direto).
    """

    def _slugify(label: str, periodo: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower().strip()).strip("_")
        periodo_slug = re.sub(r"[^a-z0-9]+", "", periodo.lower())
        return f"{slug}_{periodo_slug}"

    def _fmt_pct(v) -> "str | None":
        """Converte decimal (0.042) → string '+4,2%' no padrão brasileiro."""
        if v is None:
            return None
        try:
            pct = float(v) * 100
            sign = "+" if pct >= 0 else ""
            return f"{sign}{pct:.1f}%".replace(".", ",")
        except (TypeError, ValueError):
            return None

    def _fmt_pct_already(v) -> "str | None":
        """Converte valor já em % (4.056) → string '+4,1%' no padrão brasileiro."""
        if v is None:
            return None
        try:
            pct = float(v)
            sign = "+" if pct >= 0 else ""
            return f"{sign}{pct:.1f}%".replace(".", ",")
        except (TypeError, ValueError):
            return None

    _MESES_ISO = {
        "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
        "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
        "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
    }
    _RE_ISO_PERIODO = re.compile(r"^(\d{4})-(\d{2})$")

    def _normalizar_periodo(p: str) -> str:
        """'2025-03' → 'Mar/25'; outros formatos passam inalterados."""
        if not p:
            return p
        m = _RE_ISO_PERIODO.match(p.strip())
        if not m:
            return p
        return f"{_MESES_ISO.get(m.group(2), m.group(2))}/{m.group(1)[2:]}"

    # ── Build slug→period_label mapping from financial_statements scenarios ──
    slug_to_period: dict[str, str] = {}
    fs_raw = json_rico.get("financial_statements", {})
    if isinstance(fs_raw, dict):
        for group in fs_raw.values():
            if isinstance(group, dict):
                for line in group.get("lines", []):
                    for slug, scen in (line.get("scenarios") or {}).items():
                        per = ""
                        if isinstance(scen, dict):
                            per = scen.get("period", "")
                        if per and slug not in slug_to_period:
                            slug_to_period[slug] = per
    elif isinstance(fs_raw, list):
        # Fix 2: lista de wrappers — extrair slug_to_period dos wrappers
        for item in fs_raw:
            if isinstance(item, dict) and "lines" in item:
                period = (item.get("period") or item.get("periodo") or "").strip()
                stmt_type = (item.get("statement_type") or "").strip()
                if period and stmt_type:
                    slug_to_period[stmt_type] = period
                for line in item.get("lines", []):
                    for slug, scen in (line.get("scenarios") or {}).items():
                        per = ""
                        if isinstance(scen, dict):
                            per = scen.get("period", "")
                        if per and slug not in slug_to_period:
                            slug_to_period[slug] = per

    # ── Índice de comparações: (metric_label, target_period) → lista[dict] ──
    # comparison_period é o período-alvo (Mar/25); base_period é o anterior (Fev/25).

    def _normalizar_comp(c: dict) -> list[dict]:
        """Flatten nested comparison_mom/yoy into individual flat entries."""
        if "comparison_mom" not in c and "comparison_yoy" not in c:
            return [c]  # old/flat format — pass through unchanged
        lbl = (c.get("entity") or c.get("metric_name") or c.get("metric") or "").strip()
        per_main = (c.get("period_current") or c.get("period_main") or "").strip()
        per_yoy = (c.get("period_base_yoy") or c.get("period_prior_year") or "").strip()
        val_yoy = c.get("value_base_yoy") or c.get("value_prior_year")
        result: list[dict] = []
        mom = c.get("comparison_mom")
        if isinstance(mom, dict):
            result.append({
                "metric_name": lbl, "period_main": per_main,
                "comparison_type": "MoM",
                "delta_percentage": mom.get("percentage_change") or mom.get("delta_percentage"),
                "delta_absolute": mom.get("absolute_change") or mom.get("delta_absolute"),
            })
        yoy = c.get("comparison_yoy")
        if isinstance(yoy, dict):
            result.append({
                "metric_name": lbl, "period_main": per_main,
                "comparison_type": "YoY",
                "delta_percentage": yoy.get("percentage_change") or yoy.get("delta_percentage"),
                "delta_absolute": yoy.get("absolute_change") or yoy.get("delta_absolute"),
                "value_prior_year": val_yoy,
                "period_prior_year": per_yoy,
            })
        return result if result else [c]

    def _extrair_variacoes_inline(variations_list: list, target_period: str) -> dict:
        """Extract MoM/YoY inline_var from embedded 'variations' list (new LLM format)."""
        iv: dict = {}
        if not isinstance(variations_list, list):
            return iv
        for v in variations_list:
            if not isinstance(v, dict):
                continue
            tipo = (v.get("type") or "").lower()
            current = v.get("current", "")
            if current and current != target_period:
                continue  # variation for a different period
            val = v.get("value")
            if val is None:
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            if "mom" in tipo and "percent" in tipo:
                iv["variacao_mes"] = _fmt_pct(fval)
            elif "mom" in tipo and ("absolut" in tipo or "abs" in tipo):
                iv["variacao_mes_abs"] = fval
            elif "yoy" in tipo and "percent" in tipo:
                iv["variacao_yoy"] = _fmt_pct(fval)
                base = v.get("base", "")
                if base:
                    iv["periodo_referencia_yoy"] = _normalizar_periodo(base)
        return iv

    # Normalize comparisons list: flatten nested comparison_mom/yoy format
    comparisons_normalized: list[dict] = []
    for _c in json_rico.get("comparisons", []):
        if isinstance(_c, dict):
            comparisons_normalized.extend(_normalizar_comp(_c))

    comps_por_chave: dict[tuple, list] = {}
    for c in comparisons_normalized:
        if not isinstance(c, dict):
            continue
        lbl = (
            c.get("metric")
            or c.get("metric_name")
            or c.get("metric_or_line")
            or c.get("metrica")
            or c.get("label")
            or c.get("line_item")  # flat format from sonar-pro: line_item = FS line label
            or ""
        ).strip()
        per = _normalizar_periodo((
            c.get("comparison_period")
            or c.get("compare_period")
            or c.get("versus_period")
            or c.get("compared_period")
            or c.get("current_period")  # flat format: current_period = target period (Mar/25)
            or c.get("base_period")
            or c.get("periodo_base")
            or c.get("period")
            or c.get("period_main")  # sonar-reasoning-pro: period_main = target period (Mar/25)
            or ""
        ).strip())
        if lbl and per:
            comps_por_chave.setdefault((lbl, per), []).append(c)

    def _buscar_variacoes(label: str, periodo: str) -> dict:
        """Retorna campos de variação MoM e YoY para um indicador/período."""
        resultado = {
            "variacao_mes": None,
            "variacao_mes_abs": None,
            "valor_referencia_yoy": None,
            "periodo_referencia_yoy": None,
            "variacao_yoy": None,
        }
        entradas = comps_por_chave.get((label, periodo), [])
        for c in entradas:
            # Novo: comparison_type ("MoM"/"YoY"); legado: vs/type
            tipo = (
                c.get("comparison_type") or c.get("tipo_comparacao") or c.get("vs") or c.get("type") or ""
            ).upper()
            is_mom = "MOM" in tipo or any(
                k in tipo.lower() for k in ("anterior", "month")
            )
            is_yoy = "YOY" in tipo or any(
                k in tipo.lower() for k in ("ano", "year", "12m")
            )
            if is_mom:
                pct_raw = (
                    c.get("delta_percentage_raw")
                    or c.get("variation_percentage_raw")
                    or c.get("variacao_percentual")
                    or c.get("var_percent")
                    or c.get("var_percentage")
                    or c.get("var_percentage_from_source")
                    or c.get("delta_percentage")  # sonar-reasoning-pro: decimal fraction (0.022 = 2.2%)
                )
                if pct_raw is not None:
                    resultado["variacao_mes"] = _fmt_pct(pct_raw)
                else:
                    # var_percentage_rounded is already in % form (4.056 = 4.056%)
                    pct_already = (
                        c.get("variation_percentage")
                        or c.get("percentage_variation")
                        or c.get("var_percentage_rounded")
                    )
                    if pct_already is not None:
                        resultado["variacao_mes"] = _fmt_pct_already(pct_already)
                abs_val = (
                    c.get("delta_absolute")
                    or c.get("variation_absolute")
                    or c.get("absolute_variation")
                    or c.get("variacao_absoluta")
                    or c.get("var_absolute")
                    or c.get("var_absolute_from_source")
                )
                if abs_val is not None:
                    try:
                        resultado["variacao_mes_abs"] = float(abs_val)
                    except (TypeError, ValueError):
                        pass
            elif is_yoy:
                pct_raw = (
                    c.get("delta_percentage_raw")
                    or c.get("variation_percentage_raw")
                    or c.get("variacao_percentual")
                    or c.get("var_percent")
                    or c.get("var_percentage")
                    or c.get("var_percentage_from_source")
                    or c.get("delta_percentage")  # sonar-reasoning-pro: decimal fraction (0.112 = 11.2%)
                )
                if pct_raw is not None:
                    resultado["variacao_yoy"] = _fmt_pct(pct_raw)
                else:
                    pct_already = (
                        c.get("variation_percentage")
                        or c.get("percentage_variation")
                        or c.get("var_percentage_rounded")
                    )
                    if pct_already is not None:
                        resultado["variacao_yoy"] = _fmt_pct_already(pct_already)
                ref_val = (
                    c.get("comparison_value")
                    or c.get("value_base")
                    or c.get("base_value")
                    or c.get("reference_value")
                    or c.get("valor_referencia")
                    or c.get("valor_comparacao")
                    or c.get("value_prior_year")  # sonar-reasoning-pro field name
                )
                if ref_val is not None:
                    try:
                        resultado["valor_referencia_yoy"] = float(ref_val)
                    except (TypeError, ValueError):
                        pass
                resultado["periodo_referencia_yoy"] = _normalizar_periodo(
                    c.get("comparison_period")
                    or c.get("base_period")
                    or c.get("versus_period")
                    or c.get("periodo_base")
                    or c.get("reference_period")
                    or c.get("periodo_referencia")
                    or c.get("period_prior_year")  # sonar-reasoning-pro field name
                    or ""
                )
        return resultado

    dados: dict = {}
    chaves_usadas: set = set()

    def _inserir(label: str, norm_label: str, periodo: str, valor,
                 unidade: str, contexto: str,
                 inline_var: dict | None = None) -> None:
        """Insere uma entrada no dict dados com chave única."""
        periodo = _normalizar_periodo(periodo)
        if valor is None or not label or not periodo:
            return
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            return
        chave = _slugify(norm_label or label, periodo)
        if chave in chaves_usadas:
            chave = f"{chave}_{len(chaves_usadas)}"
        chaves_usadas.add(chave)
        var = _buscar_variacoes(label, periodo)
        # Inline variations (from embedded fields) override comps lookup
        if inline_var:
            for k, v in inline_var.items():
                if v is not None and var.get(k) is None:
                    var[k] = v
        dados[chave] = {
            "label": label,
            "valor": valor,
            "unidade": unidade or "",
            "periodo": periodo,
            **var,
            "contexto": contexto or norm_label or label,
        }

    # ── Dump de diagnóstico ──
    try:
        import pathlib, json as _json
        _dump_path = pathlib.Path(__file__).parent / "debug_rico_json.json"
        _dump_path.write_text(_json.dumps(json_rico, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("_converter: JSON rico salvo em %s", _dump_path)
    except Exception as _e:
        logger.debug("_converter: falha ao salvar JSON rico: %s", _e)

    # ── Processar financial_statements ──
    # Formato A: dict de grupos → cada grupo tem "lines" list com "scenarios" dict
    # Formato B: dict de grupos → cada grupo é uma list de items planos
    # Formato C: lista plana de items
    # Formato E: lista de wrappers com "lines" internas (sonar-reasoning-pro)
    fs_lines: list[dict] = []
    if isinstance(fs_raw, dict):
        for group in fs_raw.values():
            if isinstance(group, dict):
                fs_lines.extend(
                    item for item in group.get("lines", []) if isinstance(item, dict)
                )
            elif isinstance(group, list):
                fs_lines.extend(item for item in group if isinstance(item, dict))
    elif isinstance(fs_raw, list):
        for item in fs_raw:
            if isinstance(item, dict):
                if "lines" in item:
                    # Formato E: wrapper com linhas internas — expandir
                    fs_lines.extend(
                        line for line in item["lines"] if isinstance(line, dict)
                    )
                else:
                    # Formato C: linha direta
                    fs_lines.append(item)

    for line in fs_lines:
        raw = (line.get("raw_label") or line.get("label") or "").strip()
        norm = (line.get("normalized_label") or raw).strip()
        contexto = (
            line.get("statement_type")
            or line.get("line_category")
            or line.get("scenario")
            or norm
        )
        # Formato D/F: "periods" ou "data_points" list of {period, value, unit, sign} objects
        periods_list = line.get("periods") or line.get("data_points")
        scenarios = line.get("scenarios")
        if isinstance(periods_list, list) and periods_list:
            line_variations = line.get("variations", [])
            for per_obj in periods_list:
                if not isinstance(per_obj, dict):
                    continue
                periodo = (per_obj.get("period") or per_obj.get("period_code") or "").strip()
                valor = per_obj.get("value")
                unidade = per_obj.get("unit") or per_obj.get("currency") or ""
                sign_str = str(per_obj.get("sign", "+")).lower()
                if ("negat" in sign_str or sign_str == "-") and valor is not None:
                    try:
                        valor = -abs(float(valor))
                    except (TypeError, ValueError):
                        pass
                iv = _extrair_variacoes_inline(line_variations, periodo)
                _inserir(raw, norm, periodo, valor, unidade, contexto,
                         inline_var=iv if iv else None)
        elif isinstance(scenarios, dict) and scenarios:
            # Formato rico: um cenário por período
            for _slug, scen in scenarios.items():
                if not isinstance(scen, dict):
                    continue
                periodo = scen.get("period", "").strip()
                valor = scen.get("value")
                unidade = scen.get("unit") or scen.get("currency") or ""
                sign_str = str(scen.get("sign", "positivo")).lower()
                if "negat" in sign_str and valor is not None:
                    try:
                        valor = -abs(float(valor))
                    except (TypeError, ValueError):
                        pass
                _inserir(raw, norm, periodo, valor, unidade, contexto)
        else:
            # Formato plano: campos diretos (period, value, unit, sign)
            periodo = (line.get("period") or line.get("periodo") or "").strip()
            valor = line.get("value") if line.get("value") is not None else line.get("valor")
            unidade = line.get("unit") or line.get("currency") or ""
            sign_raw = line.get("sign") or line.get("sign_raw") or "positivo"
            if isinstance(sign_raw, str):
                if "negat" in sign_raw.lower() and valor is not None:
                    try:
                        valor = -abs(float(valor))
                    except (TypeError, ValueError):
                        pass
            else:
                try:
                    if float(sign_raw) < 0 and valor is not None:
                        valor = -abs(float(valor))
                except (TypeError, ValueError):
                    pass
            # Extract inline embedded variations (Portuguese format)
            inline_var = {}
            mom_pct = line.get("comparativo_mom_pct") or line.get("variacao_mom_percentual")
            if mom_pct is not None:
                inline_var["variacao_mes"] = _fmt_pct(mom_pct)
            mom_abs = line.get("comparativo_mom_valor") or line.get("variacao_mom_absoluta")
            if mom_abs is not None:
                try:
                    inline_var["variacao_mes_abs"] = float(mom_abs)
                except (TypeError, ValueError):
                    pass
            yoy_pct = line.get("comparativo_yoy_pct") or line.get("variacao_yoy_percentual")
            if yoy_pct is not None:
                inline_var["variacao_yoy"] = _fmt_pct(yoy_pct)
            yoy_ref = line.get("comparativo_yoy_valor_implicito") or line.get("valor_anterior_yoy")
            if yoy_ref is not None:
                try:
                    inline_var["valor_referencia_yoy"] = float(yoy_ref)
                except (TypeError, ValueError):
                    pass
            _inserir(raw, norm, periodo, valor, unidade, contexto,
                     inline_var=inline_var if inline_var else None)

    # ── Processar metrics ──
    # Novo: "periods_reported" dict (slug → valor numérico)
    # Legado: campos "period" e "value" diretos
    met_list = json_rico.get("metrics", [])
    for metric in met_list:
        if not isinstance(metric, dict):
            continue
        raw = (
            metric.get("metric_name")
            or metric.get("raw_name")
            or metric.get("metric_name_original")
            or metric.get("nome_original")
            or metric.get("name")
            or ""
        ).strip()
        norm = (
            metric.get("normalized_name")
            or metric.get("metric_name_normalized")
            or metric.get("nome_normalizado")
            or raw
        ).strip()
        unidade = metric.get("unit") or (
            "%" if any(k in norm.lower() for k in ("margem", "churn", "rate")) else ""
        )
        contexto = f"KPI: {norm}"
        periods_reported = metric.get("periods_reported")
        data_dict = metric.get("data")
        periods_list_met = metric.get("periods")  # new LLM format
        if isinstance(periods_reported, dict) and periods_reported:
            for slug, valor in periods_reported.items():
                periodo = slug_to_period.get(slug) or slug
                _inserir(raw, norm, periodo, valor, unidade, contexto)
        elif isinstance(data_dict, dict) and data_dict:
            for periodo_key, valor in data_dict.items():
                _inserir(raw, norm, periodo_key, valor, unidade, contexto)
        elif isinstance(periods_list_met, list) and periods_list_met:
            # New format: periods[] list with period_code + embedded variations[]
            met_variations = metric.get("variations", [])
            for per_obj in periods_list_met:
                if not isinstance(per_obj, dict):
                    continue
                periodo = (per_obj.get("period") or per_obj.get("period_code") or "").strip()
                valor = per_obj.get("value")
                _unit = per_obj.get("unit") or unidade
                iv = _extrair_variacoes_inline(met_variations, periodo)
                _inserir(raw, norm, periodo, valor, _unit, contexto,
                         inline_var=iv if iv else None)
        elif isinstance(periods_reported, list):
            # periods_reported is a list of period strings — use latest_value/latest_period
            lat_per = (metric.get("latest_period") or "").strip()
            lat_val = metric.get("latest_value")
            if lat_per and lat_val is not None:
                _inserir(raw, norm, lat_per, lat_val, unidade, contexto)
        else:
            periodo = (
                metric.get("period")
                or metric.get("period_primary")
                or metric.get("periodo_atual")
                or metric.get("base_temporal")
                or ""
            ).strip()
            valor = (
                metric.get("value")
                or metric.get("value_reported")
                or metric.get("reported_value")
                or metric.get("valor_atual")
            )
            _met_inline = {}
            _mom = metric.get("variacao_mom_percentual") or metric.get("comparativo_mom_pct")
            if _mom is not None:
                _met_inline["variacao_mes"] = _fmt_pct(_mom)
            _mom_abs = metric.get("variacao_mom_absoluta") or metric.get("comparativo_mom_valor")
            if _mom_abs is not None:
                try:
                    _met_inline["variacao_mes_abs"] = float(_mom_abs)
                except (TypeError, ValueError):
                    pass
            _yoy = metric.get("variacao_yoy_percentual") or metric.get("comparativo_yoy_pct")
            if _yoy is not None:
                _met_inline["variacao_yoy"] = _fmt_pct(_yoy)
            _yoy_ref = metric.get("valor_anterior_yoy") or metric.get("comparativo_yoy_valor_implicito")
            if _yoy_ref is not None:
                try:
                    _met_inline["valor_referencia_yoy"] = float(_yoy_ref)
                except (TypeError, ValueError):
                    pass
            _inserir(raw, norm, periodo, valor, unidade, contexto,
                     inline_var=_met_inline if _met_inline else None)

    # ── Resumo ──
    ws = json_rico.get("workbook_summary", {})
    if isinstance(ws, dict):
        resumo = ws.get("type") or ws.get("description") or ws.get("classification") or "Dados extraídos."
    else:
        resumo = str(ws) if ws else "Dados extraídos."

    # ── Confiança ──
    conf_raw = json_rico.get("confidence", {})
    if isinstance(conf_raw, dict):
        nivel_str = (
            conf_raw.get("overall")
            or conf_raw.get("global")
            or conf_raw.get("geral")
            or "media"
        )
        try:
            nivel_num = float(nivel_str)
            nivel = "alta" if nivel_num >= 0.75 else ("media" if nivel_num >= 0.5 else "baixa")
        except (TypeError, ValueError):
            nivel = str(nivel_str).lower() if nivel_str else "media"
            if nivel not in ("alta", "media", "baixa"):
                nivel = "media"
    else:
        nivel = "media"

    alertas: list[str] = []
    for anomaly in json_rico.get("anomalies", []):
        if isinstance(anomaly, str):
            alertas.append(anomaly)
        elif isinstance(anomaly, dict):
            desc = anomaly.get("description") or anomaly.get("flag") or str(anomaly)
            alertas.append(desc)

    # ── Extrair indicadores do período anterior via comparisons.base_value ──
    for c in json_rico.get("comparisons", []):
        if not isinstance(c, dict):
            continue
        lbl = (c.get("metric") or c.get("metric_name") or c.get("metric_or_line") or c.get("metrica") or c.get("label") or "").strip()
        comp_type = (c.get("comparison_type") or c.get("tipo_comparacao") or "").upper()
        if "MOM" not in comp_type:
            continue
        base_val = c.get("base_value") or c.get("comparison_value_base")
        base_per = _normalizar_periodo((c.get("base_period") or c.get("periodo_base_label") or "").strip())
        if base_val is None or not base_per or not lbl:
            continue
        try:
            base_val = float(base_val)
        except (TypeError, ValueError):
            continue
        chave = _slugify(lbl, base_per)
        if chave in chaves_usadas:
            continue
        chaves_usadas.add(chave)
        var = _buscar_variacoes(lbl, base_per)
        unidade = c.get("unit") or c.get("currency") or ""
        dados[chave] = {
            "label": lbl,
            "valor": base_val,
            "unidade": unidade,
            "periodo": base_per,
            **var,
            "contexto": lbl,
        }

    logger.info(
        "_converter_para_formato_pipeline: %d fs_lines, %d metrics → %d entradas. slug_map=%s",
        len(fs_lines),
        len(met_list),
        len(dados),
        slug_to_period,
    )

    return {
        "dados": dados,
        "resumo": resumo,
        "confianca": {"geral": nivel, "alertas": alertas},
    }


# ═══════════════════════════════════════════════════════════════════════
# ETAPA 3 — VALIDAÇÃO FINANCEIRA (determinística)
# ═══════════════════════════════════════════════════════════════════════

def _etapa3_validacao(dados: dict, estrutura: dict) -> dict:
    """Valida consistência financeira dos dados extraídos.

    Executa verificações determinísticas em Python — sem LLM.

    Returns:
        Dicionário com status, checks, alertas, dados_corrigidos.
    """
    indicadores = dados.get("dados", {})
    checks: dict[str, dict] = {}
    alertas: list[str] = []
    correcoes: dict[str, dict] = {}

    # ── Agrupar indicadores por label (sem sufixo de período) ──
    por_label: dict[str, list[tuple[str, dict]]] = {}
    for chave, info in indicadores.items():
        if not isinstance(info, dict):
            continue
        label = info.get("label", chave)
        por_label.setdefault(label, []).append((chave, info))

    # ── Check A: Subtotais ──
    total_ok = True
    total_details: list[str] = []
    for label, entradas in por_label.items():
        label_lower = label.lower()
        if "total" not in label_lower:
            continue
        # Encontrar linhas de detalhe (entradas não-total com mesmo período)
        for chave_total, info_total in entradas:
            periodo = info_total.get("periodo", "?")
            val_total = info_total.get("valor")
            if val_total is None:
                continue
            # Buscar itens de detalhe do mesmo período
            soma_detalhe = 0.0
            n_detalhe = 0
            for lbl2, entradas2 in por_label.items():
                if "total" in lbl2.lower() or "subtotal" in lbl2.lower():
                    continue
                for _, info2 in entradas2:
                    if info2.get("periodo") == periodo and info2.get("unidade") == info_total.get("unidade"):
                        v2 = info2.get("valor")
                        if v2 is not None and isinstance(v2, (int, float)):
                            soma_detalhe += v2
                            n_detalhe += 1
            if n_detalhe > 1 and val_total != 0:
                diff_pct = abs(soma_detalhe - val_total) / abs(val_total) * 100
                if diff_pct > 0.5:
                    total_ok = False
                    total_details.append(
                        f"{label} {periodo}: soma detalhe={soma_detalhe:.0f} vs total={val_total:.0f} "
                        f"(diff={diff_pct:.1f}%)"
                    )
    checks["subtotais"] = {
        "ok": total_ok,
        "detalhes": "; ".join(total_details) if total_details else "OK",
    }

    # ── Check B: Variações MoM ──
    mom_ok = True
    mom_details: list[str] = []
    periodo_recente = estrutura.get("periodo_mais_recente", "")
    periodo_anterior = estrutura.get("periodo_anterior", "")

    for label, entradas in por_label.items():
        val_atual = None
        val_anterior = None
        var_claimed = None
        chave_atual = None

        for chave, info in entradas:
            p = info.get("periodo", "")
            if p == periodo_recente:
                val_atual = info.get("valor")
                var_claimed = _pct_str_to_float(info.get("variacao_mes"))
                chave_atual = chave
            elif p == periodo_anterior:
                val_anterior = info.get("valor")

        if (val_atual is not None and val_anterior is not None
                and val_anterior != 0 and var_claimed is not None):
            var_calc = (val_atual - val_anterior) / val_anterior
            diff_pp = abs(var_calc - var_claimed) * 100  # em pontos percentuais
            if diff_pp > 0.15:  # tolerância 0.15 pp
                mom_ok = False
                mom_details.append(
                    f"{label}: calc={var_calc*100:.1f}% vs extraído={var_claimed*100:.1f}% "
                    f"(diff={diff_pp:.2f}pp)"
                )
                # Auto-corrigir
                if chave_atual:
                    sinal = "+" if var_calc >= 0 else ""
                    corrigido = f"{sinal}{var_calc*100:.1f}%".replace(".", ",")
                    correcoes[chave_atual] = {"variacao_mes": corrigido}

    checks["variacoes_mom"] = {
        "ok": mom_ok,
        "detalhes": "; ".join(mom_details) if mom_details else "OK",
    }

    # ── Check C: Variações YoY ──
    yoy_ok = True
    yoy_details: list[str] = []

    for label, entradas in por_label.items():
        for chave, info in entradas:
            p = info.get("periodo", "")
            if p != periodo_recente:
                continue
            val_atual = info.get("valor")
            val_yoy = info.get("valor_referencia_yoy")
            var_yoy_claimed = _pct_str_to_float(info.get("variacao_yoy"))

            if (val_atual is not None and val_yoy is not None
                    and val_yoy != 0 and var_yoy_claimed is not None):
                var_calc = (val_atual - val_yoy) / val_yoy
                diff_pp = abs(var_calc - var_yoy_claimed) * 100
                if diff_pp > 0.15:
                    yoy_ok = False
                    yoy_details.append(
                        f"{label}: calc={var_calc*100:.1f}% vs extraído={var_yoy_claimed*100:.1f}% "
                        f"(diff={diff_pp:.2f}pp)"
                    )
                    sinal = "+" if var_calc >= 0 else ""
                    corrigido = f"{sinal}{var_calc*100:.1f}%".replace(".", ",")
                    correcoes[chave] = correcoes.get(chave, {})
                    correcoes[chave]["variacao_yoy"] = corrigido

    checks["variacoes_yoy"] = {
        "ok": yoy_ok,
        "detalhes": "; ".join(yoy_details) if yoy_details else "OK",
    }

    # ── Check D: Sinais ──
    sinais_ok = True
    sinais_details: list[str] = []
    for chave, info in indicadores.items():
        if not isinstance(info, dict):
            continue
        val = info.get("valor")
        var_abs = info.get("variacao_mes_abs")
        var_pct = _pct_str_to_float(info.get("variacao_mes"))
        if val is not None and var_abs is not None and var_pct is not None:
            # Sinal da variação absoluta deve concordar com percentual
            if var_abs != 0 and var_pct != 0:
                if (var_abs > 0) != (var_pct > 0):
                    sinais_ok = False
                    sinais_details.append(
                        f"{chave}: var_abs={var_abs} vs var_pct={info.get('variacao_mes')} — sinais divergem"
                    )

    checks["sinais"] = {
        "ok": sinais_ok,
        "detalhes": "; ".join(sinais_details) if sinais_details else "OK",
    }

    # ── Check E: Completude ──
    periodos_encontrados = {
        info.get("periodo") for info in indicadores.values()
        if isinstance(info, dict) and info.get("periodo")
    }
    periodos_esperados = set()
    for f in ("periodo_mais_recente", "periodo_anterior"):
        p = estrutura.get(f)
        if p:
            periodos_esperados.add(p)
    completude_ok = periodos_esperados.issubset(periodos_encontrados)
    faltantes = periodos_esperados - periodos_encontrados
    checks["completude"] = {
        "ok": completude_ok,
        "detalhes": f"Faltantes: {faltantes}" if faltantes else "OK",
    }

    # ── Aplicar correções ──
    dados_corrigidos = None
    if correcoes:
        dados_corrigidos = {k: dict(v) for k, v in indicadores.items() if isinstance(v, dict)}
        for chave, campos in correcoes.items():
            if chave in dados_corrigidos:
                dados_corrigidos[chave].update(campos)
        alertas.append(f"{len(correcoes)} valor(es) de variação corrigido(s) pela validação")

    # ── Status final ──
    all_ok = all(c["ok"] for c in checks.values())
    if all_ok:
        status = "aprovado"
    elif dados_corrigidos is not None or sinais_ok:
        status = "aprovado_com_alertas"
    else:
        status = "reprovado"

    n_alertas = sum(not c["ok"] for c in checks.values())
    logger.info("ETAPA 3 — Validação: status=%s, alertas=%d", status, n_alertas)

    return {
        "status": status,
        "checks": checks,
        "dados_corrigidos": dados_corrigidos,
        "alertas": alertas,
        "requer_revisao_humana": status == "reprovado",
    }


# ═══════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ═══════════════════════════════════════════════════════════════════════

def analisar_excel(
    llm: LLMClient,
    excel_files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    """Analisa e extrai dados financeiros de arquivos Excel em 3 etapas.

    Substitui ``extrair_dados_excel()`` do extrai_dados_da_planilha.py.
    Retorna formato compatível com o pipeline: {dados: {...}, resumo: str}.

    Args:
        llm: Instância configurada de LLMClient.
        excel_files: Lista de tuplas (filename, file_bytes).

    Returns:
        Dicionário com chave ``dados`` (dict de indicadores), ``resumo`` (str),
        ``estrutura`` (mapa da Etapa 1), ``validacao`` (resultado da Etapa 3).
    """
    # ── Representação enriquecida ──
    conteudo_parts: list[str] = []
    for filename, file_bytes in excel_files:
        try:
            conteudo = representar_excel_enriquecido(file_bytes, filename)
            logger.info("Excel '%s' representado: %d chars", filename, len(conteudo))
            conteudo_parts.append(conteudo)
        except Exception as e:
            logger.error("Erro ao representar '%s': %s", filename, e)
            conteudo_parts.append(f"## Arquivo: {filename}\n_(Erro: {e})_\n")

    conteudo_total = "\n---\n".join(conteudo_parts)

    # ══════════════════════════════════════════
    # ETAPA 1 — Reconhecimento estrutural
    # ══════════════════════════════════════════
    logger.info("🔍 ETAPA 1 — Analisando estrutura do Excel...")
    estrutura = _etapa1_estrutura(llm, conteudo_total)

    if not estrutura:
        logger.warning("Etapa 1 falhou — tentando extração direta (fallback)")
        # Fallback: passa conteúdo direto para extração sem mapa
        estrutura = {
            "abas": [],
            "contexto_negocio": "desconhecido",
            "periodo_mais_recente": None,
            "periodo_anterior": None,
            "periodo_yoy": None,
        }

    # ══════════════════════════════════════════
    # ETAPA 2 — Extração inteligente
    # ══════════════════════════════════════════
    logger.info("📊 ETAPA 2 — Extraindo dados financeiros...")
    dados = _etapa2_extracao(llm, conteudo_total, estrutura)

    if dados.get("erro"):
        return dados

    # ══════════════════════════════════════════
    # ETAPA 3 — Validação financeira
    # ══════════════════════════════════════════
    logger.info("✅ ETAPA 3 — Validando consistência financeira...")
    validacao = _etapa3_validacao(dados, estrutura)

    # Aplicar correções automáticas se houver
    if validacao.get("dados_corrigidos"):
        dados["dados"] = validacao["dados_corrigidos"]
        logger.info("Dados corrigidos pela validação aplicados.")

    # Enriquecer resposta com metadados
    dados["estrutura"] = estrutura
    dados["validacao"] = validacao

    n_periodos = len({
        v.get("periodo") for v in dados.get("dados", {}).values()
        if isinstance(v, dict) and v.get("periodo")
    })
    logger.info(
        "analisa_planilha_financeira: %d indicadores, %d períodos, validação=%s",
        len(dados.get("dados", {})), n_periodos, validacao.get("status"),
    )

    return dados
