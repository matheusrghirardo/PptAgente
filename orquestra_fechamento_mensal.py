"""
orquestra_fechamento_mensal.py — Orquestrador de fechamento mensal.

Conecta:  extrai_dados_da_planilha → gera_plano_de_edicao_do_pptx → agentes de edição existentes → output.

Usa os agentes existentes do DeckForge sem reescrevê-los — apenas injeta o
plano de edição gerado pelo pptx_mapper no fluxo de navegação/edição já existente.
"""

import re
import time
import logging
from io import BytesIO
from typing import Any, Callable

from pptx import Presentation

from cliente_modelos_de_linguagem import LLMClient
from analisa_planilha_financeira import analisar_excel
from extrai_dados_da_planilha import extrair_dados_excel  # fallback
from gera_plano_de_edicao_do_pptx import gerar_plano_edicao
from monitora_execucao_dos_agentes import ObservabilityAgent
from executa_edicoes_no_pptx import executar_plano_direto
from extrai_padroes_do_pptx import (
    extrair_padroes,
    calcular_contexto,
    formatar_contexto_para_log,
)

logger = logging.getLogger(__name__)
# Garantir que os logs de diagnóstico apareçam no terminal enquanto Streamlit roda
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


class FechamentoResult:
    """Resultado do pipeline de fechamento mensal."""

    def __init__(
        self,
        sucesso: bool,
        pptx_bytes: bytes,
        dados_excel: dict[str, Any],
        plano: list[dict[str, Any]],
        resultado_edicao: dict[str, Any],
        log: list[str],
        contexto_temporal: dict[str, Any] | None = None,
        avisos_manuais: list[dict[str, Any]] | None = None,
    ):
        self.sucesso = sucesso
        self.pptx_bytes = pptx_bytes
        self.dados_excel = dados_excel
        self.plano = plano
        self.resultado_edicao = resultado_edicao
        self.log = log
        self.contexto_temporal = contexto_temporal
        self.avisos_manuais = avisos_manuais or []


# Regex para detectar labels de período do tipo "Fev/25", "Jan/24", etc.
_PERIODO_RE = re.compile(r'\b[A-Za-záéíóúâêôàãõ]{3}/\d{2}\b', re.IGNORECASE)


def _detectar_graficos_com_periodos(pptx_bytes: bytes) -> list[dict[str, Any]]:
    """Varre o PPTX em busca de gráficos cujas categorias contêm labels de período.

    python-pptx lê os nomes de categoria do strCache XML do gráfico, mas NÃO
    oferece API de escrita para categories — modificar o strCache sem atualizar
    o Excel embutido pode ser sobrescrito pelo PowerPoint ao abrir o arquivo.
    Por isso esses elementos são reportados como avisos de ação manual.

    Returns:
        Lista de dicts com slide, shape_nome, categorias e periodos detectados.
    """
    avisos: list[dict[str, Any]] = []
    try:
        prs = Presentation(BytesIO(pptx_bytes))
        for idx_s, slide in enumerate(prs.slides):
            for idx_sh, shape in enumerate(slide.shapes):
                if not shape.has_chart:
                    continue
                chart = shape.chart
                categorias: list[str] = []
                try:
                    for plot in chart.plots:
                        if plot.categories:
                            categorias = [str(c) for c in plot.categories if c is not None]
                            break
                except Exception:
                    pass
                periodos = [c for c in categorias if _PERIODO_RE.search(c)]
                if periodos:
                    avisos.append({
                        "slide": idx_s + 1,
                        "shape_nome": shape.name,
                        "shape_indice": idx_sh,
                        "categorias": categorias,
                        "periodos": periodos,
                    })
    except Exception as exc:
        logger.warning("Erro ao detectar gráficos com períodos: %s", exc)
    return avisos


# ════════════════════════════════════════════════════════════════════════
# Deterministic period-advancement helpers & plan complement
# ════════════════════════════════════════════════════════════════════════

_MESES_ABREV_P = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]
_MESES_COMPLETOS_P = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
_RE_P_ABREV = re.compile(
    r'\b(Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)/(\d{2})\b'
)
_RE_P_FULL = re.compile(
    r'\b(Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|'
    r'Setembro|Outubro|Novembro|Dezembro)\s+(\d{4})\b'
)


def _avancar_abrev(m: re.Match) -> str:
    """Advance an abbreviated month/year token by 1 month."""
    idx = _MESES_ABREV_P.index(m.group(1))
    ni = (idx + 1) % 12
    yy = int(m.group(2))
    return f"{_MESES_ABREV_P[ni]}/{(yy + 1 if idx == 11 else yy):02d}"


def _avancar_completo(m: re.Match) -> str:
    """Advance a full month-name year token by 1 month."""
    idx = _MESES_COMPLETOS_P.index(m.group(1))
    ni = (idx + 1) % 12
    yr = int(m.group(2))
    return f"{_MESES_COMPLETOS_P[ni]} {yr + 1 if idx == 11 else yr}"


def _avancar_periodos_texto(texto: str) -> str:
    """Advance ALL period references in *texto* by exactly 1 month.

    Uses ``re.sub`` with a callback so every match is replaced independently
    in a single pass — no chaining issues between overlapping tokens.
    """
    r = _RE_P_ABREV.sub(_avancar_abrev, texto)
    return _RE_P_FULL.sub(_avancar_completo, r)


def _complementar_plano_periodos(
    pptx_bytes: bytes,
    plano: list[dict[str, Any]],
    contexto_temporal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Add deterministic period-advancement actions for gaps in the LLM plan.

    Scans ALL text in the base PPTX.  For each shape or table cell that
    contains a period reference and is NOT already covered by the LLM plan,
    generates an action to advance the period(s) by 1 month.

    If *contexto_temporal* is provided, text that already contains the target
    period (label_novo) will NOT be advanced — this prevents the double-advance
    bug on publication dates and footers.
    """
    label_novo = (contexto_temporal or {}).get("label_novo", "")
    covered_shapes: set[tuple[int, int]] = set()
    covered_cells: set[tuple[int, int, int, int]] = set()
    global_antigos: set[str] = set()

    for a in plano:
        acao = a.get("acao", "")
        s, sh = a.get("slide_numero"), a.get("shape_indice")
        if acao == "substituir_texto_global":
            global_antigos.add(a.get("valor_antigo", ""))
        elif acao == "alterar_texto":
            covered_shapes.add((s, sh))
        elif acao == "alterar_celula_tabela":
            covered_cells.add((s, sh, a.get("tabela_linha"), a.get("tabela_coluna")))

    novos: list[dict[str, Any]] = []
    prs = Presentation(BytesIO(pptx_bytes))

    for si, slide in enumerate(prs.slides):
        sn = si + 1
        for shi, shape in enumerate(slide.shapes):
            # ── Text shapes ──
            if shape.has_text_frame and (sn, shi) not in covered_shapes:
                for para in shape.text_frame.paragraphs:
                    p = para.text
                    if not p.strip():
                        continue
                    if not (_RE_P_ABREV.search(p) or _RE_P_FULL.search(p)):
                        continue
                    # Skip if text already contains the target period
                    if label_novo and label_novo in p:
                        continue
                    # Skip if every period token is already covered by a global sub
                    # A token t is "covered" only if a global valor_antigo g both
                    # contains t AND appears in the shape text p (so the global
                    # will actually touch this shape).
                    tokens = [m.group(0) for m in _RE_P_ABREV.finditer(p)]
                    tokens += [m.group(0) for m in _RE_P_FULL.finditer(p)]
                    if all(any((t in g) and (g in p) for g in global_antigos) for t in tokens):
                        continue
                    adv = _avancar_periodos_texto(p)
                    if p != adv:
                        novos.append({
                            "tipo": "edicao", "acao": "alterar_texto",
                            "slide_numero": sn, "shape_indice": shi,
                            "valor_antigo": p, "valor_novo": adv,
                            "descricao": f"[AUTO] slide {sn} shape {shi}: period advance",
                        })

            # ── Table cells ──
            if shape.has_table:
                tbl = shape.table
                for ri in range(len(tbl.rows)):
                    for ci in range(len(tbl.columns)):
                        if (sn, shi, ri, ci) in covered_cells:
                            continue
                        ct = tbl.cell(ri, ci).text.strip()
                        if not ct or not (_RE_P_ABREV.search(ct) or _RE_P_FULL.search(ct)):
                            continue
                        # Skip if cell already contains the target period
                        if label_novo and label_novo in ct:
                            continue
                        adv = _avancar_periodos_texto(ct)
                        if ct != adv:
                            novos.append({
                                "tipo": "edicao", "acao": "alterar_celula_tabela",
                                "slide_numero": sn, "shape_indice": shi,
                                "tabela_linha": ri, "tabela_coluna": ci,
                                "valor_antigo": ct, "valor_novo": adv,
                                "descricao": f"[AUTO] slide {sn} table [{ri},{ci}]: period advance",
                            })

    if novos:
        logger.info("Period complement: added %d actions.", len(novos))
    return plano + novos


def _corrigir_tabela_com_excel(
    pptx_bytes: bytes,
    plano: list[dict[str, Any]],
    excel_files: list[tuple[str, bytes]],
    contexto_temporal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic table correction using raw Excel data.

    Reads the Excel directly with openpyxl and verifies/corrects ALL data
    cells in the PPTX table (previous-period values, current-period values,
    MoM R$, MoM %, YoY reference, YoY %).  Any cell that already has the
    correct value or is already covered by the LLM plan is left alone.
    """
    import openpyxl

    label_novo = (contexto_temporal or {}).get("label_novo", "")
    label_anterior = (contexto_temporal or {}).get("label_anterior", "")
    sep_mil = (contexto_temporal or {}).get("separador_milhar", ".")
    sep_dec = (contexto_temporal or {}).get("separador_decimal", ",")
    casas_pct = int((contexto_temporal or {}).get("casas_decimais_pct", 1))

    if not label_novo or not label_anterior or not excel_files:
        return plano

    excel_name, excel_bytes = excel_files[0]
    try:
        wb = openpyxl.load_workbook(BytesIO(excel_bytes), data_only=True)
    except Exception:
        return plano

    # Find the revenue sheet
    ws = None
    for sheet_name in wb.sheetnames:
        candidate = wb[sheet_name]
        for row in candidate.iter_rows(min_row=1, max_row=2, values_only=True):
            row_str = " ".join(str(c or "") for c in row)
            if "Receita" in row_str or "RECEITA" in row_str:
                ws = candidate
                break
        if ws:
            break
    if not ws:
        return plano

    # Parse Excel header
    header_row = None
    header_row_num = 0
    for ri, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), 1):
        if row and row[0] and "Linha" in str(row[0]):
            header_row = list(row)
            header_row_num = ri
            break
    if not header_row:
        return plano

    # Identify Excel columns by header content
    excel_cols: dict[str, int] = {}
    for ci, val in enumerate(header_row):
        s = str(val or "")
        if label_anterior in s and "mil" in s.lower():
            excel_cols["prev_val"] = ci
        elif label_novo in s and "mil" in s.lower():
            excel_cols["curr_val"] = ci
        elif "MoM" in s and "R$" in s:
            excel_cols["mom_r"] = ci
        elif "MoM" in s and "%" in s:
            excel_cols["mom_pct"] = ci
        elif "YoY" in s and "%" in s:
            excel_cols["yoy_pct"] = ci
        else:
            # Check for YoY reference period (e.g. "Mar/24 (R$ mil)")
            parts = label_novo.split("/")
            if len(parts) == 2:
                try:
                    yoy_label = f"{parts[0]}/{int(parts[1]) - 1:02d}"
                except (ValueError, TypeError):
                    yoy_label = ""
                if yoy_label and yoy_label in s and "mil" in s.lower():
                    excel_cols["yoy_val"] = ci

    # Read all data rows from Excel
    # row_label → {prev_val, curr_val, mom_r, mom_pct, yoy_val, yoy_pct}
    excel_data: dict[str, dict[str, Any]] = {}
    for row in ws.iter_rows(min_row=header_row_num + 1, values_only=True):
        if not row or not row[0]:
            continue
        label = str(row[0]).strip()
        entry: dict[str, Any] = {}
        for key, ci in excel_cols.items():
            if ci < len(row) and row[ci] is not None:
                entry[key] = row[ci]
        excel_data[label] = entry

    # Formatting helpers
    def _fmt_int(v) -> str:
        """Format integer with thousand separator."""
        n = int(round(float(v)))
        return f"{n:,}".replace(",", sep_mil)

    def _fmt_signed_int(v) -> str:
        """Format signed integer (MoM R$)."""
        n = int(round(float(v)))
        sign = "+" if n > 0 else ""
        formatted = f"{abs(n):,}".replace(",", sep_mil)
        return f"{sign}{formatted}" if n >= 0 else f"-{formatted}"

    def _fmt_pct(v) -> str:
        """Format decimal as percentage with sign."""
        p = float(v) * 100
        sign = "+" if p > 0 else ""
        formatted = f"{p:.{casas_pct}f}".replace(".", sep_dec)
        return f"{sign}{formatted}%"

    # Map: PPTX table col index → (excel_key, formatter)
    # PPTX table layout: col0=label, col1=prev, col2=curr, col3=momR$, col4=mom%, col5=yoyRef, col6=yoy%
    col_mapping = {
        1: ("prev_val", _fmt_int),
        2: ("curr_val", _fmt_int),
        3: ("mom_r", _fmt_signed_int),
        4: ("mom_pct", _fmt_pct),
        5: ("yoy_val", _fmt_int),
        6: ("yoy_pct", _fmt_pct),
    }

    # Build set of cells already covered by plan actions (both existing and new)
    covered_cells: set[tuple[int, int, int, int]] = set()
    # Also build a map of plan actions by cell for overriding incorrect values
    plan_cell_values: dict[tuple[int, int, int, int], int] = {}
    for idx, a in enumerate(plano):
        if a.get("acao") == "alterar_celula_tabela":
            key = (a.get("slide_numero"), a.get("shape_indice"),
                   a.get("tabela_linha"), a.get("tabela_coluna"))
            covered_cells.add(key)
            plan_cell_values[key] = idx

    # Find table in PPTX
    try:
        prs = Presentation(BytesIO(pptx_bytes))
    except Exception:
        return plano

    novos: list[dict[str, Any]] = []
    override_indices: set[int] = set()  # plan indices to override

    for si, slide in enumerate(prs.slides):
        sn = si + 1
        for shi, shape in enumerate(slide.shapes):
            if not shape.has_table:
                continue
            tbl = shape.table
            n_rows = len(tbl.rows)
            n_cols = len(tbl.columns)
            if n_rows < 3 or n_cols < 7:
                continue

            for ri in range(1, n_rows):
                pptx_label = tbl.cell(ri, 0).text.strip()
                if not pptx_label:
                    continue

                excel_row = excel_data.get(pptx_label)
                if not excel_row:
                    continue

                for pptx_ci, (excel_key, formatter) in col_mapping.items():
                    if pptx_ci >= n_cols:
                        continue
                    raw_val = excel_row.get(excel_key)
                    if raw_val is None:
                        continue

                    try:
                        expected = formatter(raw_val)
                    except (ValueError, TypeError):
                        continue

                    current_val = tbl.cell(ri, pptx_ci).text.strip()
                    cell_key = (sn, shi, ri, pptx_ci)

                    if cell_key in covered_cells:
                        # Check if the LLM plan has the correct value
                        plan_idx = plan_cell_values.get(cell_key)
                        if plan_idx is not None:
                            plan_novo = plano[plan_idx].get("valor_novo", "")
                            if plan_novo != expected:
                                # Override the LLM's incorrect value
                                override_indices.add(plan_idx)
                                novos.append({
                                    "tipo": "edicao",
                                    "acao": "alterar_celula_tabela",
                                    "slide_numero": sn,
                                    "shape_indice": shi,
                                    "tabela_linha": ri,
                                    "tabela_coluna": pptx_ci,
                                    "valor_antigo": current_val,
                                    "valor_novo": expected,
                                    "descricao": f"[AUTO-TABLE-FIX] [{ri},{pptx_ci}]: {plan_novo} → {expected}",
                                })
                    elif current_val != expected:
                        # Cell not covered by plan and value is wrong
                        novos.append({
                            "tipo": "edicao",
                            "acao": "alterar_celula_tabela",
                            "slide_numero": sn,
                            "shape_indice": shi,
                            "tabela_linha": ri,
                            "tabela_coluna": pptx_ci,
                            "valor_antigo": current_val,
                            "valor_novo": expected,
                            "descricao": f"[AUTO-TABLE] [{ri},{pptx_ci}]: {current_val} → {expected}",
                        })

    if novos or override_indices:
        # Remove overridden plan entries
        plano_filtrado = [a for i, a in enumerate(plano) if i not in override_indices]
        logger.info(
            "Table complement: added %d corrections, overrode %d LLM values.",
            len(novos), len(override_indices),
        )
        return plano_filtrado + novos

    return plano


_PCT_ISOLATED_RE = re.compile(r'^[+\-]\d+[,\.]\d+%$')
_RE_VAR_LABEL = re.compile(r'var\.?\s*vs\s+(\w{3})/(\d{2})', re.IGNORECASE)


def _corrigir_kpis_capa_slide(
    pptx_bytes: bytes,
    plano: list[dict[str, Any]],
    dados_excel: dict[str, Any],
    contexto_temporal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic override for isolated percentage KPI shapes on slide 1.

    Isolated '+X,X%' shapes adjacent to 'Var. vs [period]' labels are
    MoM/YoY totals.  This function replaces any incorrect LLM-generated
    actions for those shapes with values read directly from the TOTAL entry
    in the data dict, completely bypassing LLM non-determinism.
    """
    label_novo = (contexto_temporal or {}).get("label_novo", "")
    label_anterior = (contexto_temporal or {}).get("label_anterior", "")

    # Derive the prior-year period label (e.g. "Mar/25" → "Mar/24")
    _parts = label_novo.split("/") if "/" in label_novo else []
    try:
        label_yoy = f"{_parts[0]}/{int(_parts[1]) - 1:02d}" if len(_parts) == 2 else ""
    except (ValueError, TypeError):
        label_yoy = ""

    # ── Locate TOTAL entry in dados_excel for the current period ──
    dados = dados_excel.get("dados", {})
    total_entry: dict | None = None
    max_val = -float("inf")

    for entry in dados.values():
        if entry.get("periodo") != label_novo:
            continue
        lbl_upper = (entry.get("label") or "").upper()
        try:
            v = float(entry.get("valor", 0) or 0)
        except (TypeError, ValueError):
            v = 0
        if "TOTAL" in lbl_upper:
            # Prefer TOTAL entry with highest valor
            if total_entry is None or v > float(total_entry.get("valor", 0) or 0):
                total_entry = entry
        elif total_entry is None and v > max_val:
            # Fallback: max-valor entry if no TOTAL found
            max_val = v
            total_entry = entry

    if not total_entry:
        return plano  # Nothing to correct

    total_label = total_entry.get("label", "")
    try:
        total_val_curr = float(total_entry.get("valor", 0) or 0)
    except (TypeError, ValueError):
        return plano

    # ── Compute MoM from raw values (more reliable than variacao_mes field) ──
    total_mom: str | None = total_entry.get("variacao_mes")
    if not total_mom and label_anterior:
        for entry in dados.values():
            if entry.get("label") == total_label and entry.get("periodo") == label_anterior:
                try:
                    prev_val = float(entry.get("valor", 0) or 0)
                    if prev_val:
                        mom_pct = (total_val_curr - prev_val) / prev_val * 100
                        sign = "+" if mom_pct >= 0 else ""
                        total_mom = f"{sign}{mom_pct:.1f}%".replace(".", ",")
                except (TypeError, ValueError, ZeroDivisionError):
                    pass
                break

    # ── Compute YoY from raw values (more reliable than variacao_yoy field) ──
    total_yoy: str | None = total_entry.get("variacao_yoy")
    if not total_yoy and label_yoy:
        for entry in dados.values():
            if entry.get("label") == total_label and entry.get("periodo") == label_yoy:
                try:
                    yoy_val = float(entry.get("valor", 0) or 0)
                    if yoy_val:
                        yoy_pct = (total_val_curr - yoy_val) / yoy_val * 100
                        sign = "+" if yoy_pct >= 0 else ""
                        total_yoy = f"{sign}{yoy_pct:.1f}%".replace(".", ",")
                except (TypeError, ValueError, ZeroDivisionError):
                    pass
                break

    logger.debug(
        "[KPI-capa] total_label=%r curr=%.0f mom=%s yoy=%s label_yoy=%s",
        total_label, total_val_curr, total_mom, total_yoy, label_yoy,
    )

    if not total_mom and not total_yoy:
        return plano  # Nothing to correct

    # ── Scan slide 1 for isolated percentage shapes ──
    try:
        prs = Presentation(BytesIO(pptx_bytes))
    except Exception:
        return plano

    slide1 = prs.slides[0]
    shapes = list(slide1.shapes)
    novo_year = label_novo.split("/")[-1] if "/" in label_novo else ""

    plano_out = list(plano)

    for idx_sh, shape in enumerate(shapes):
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text.strip()
        if not _PCT_ISOLATED_RE.match(text):
            continue

        # Search backward (up to 5 shapes) for the nearest "Var. vs [period]" label
        var_match = None
        for j in range(idx_sh - 1, max(idx_sh - 6, -1), -1):
            sh_j = shapes[j]
            if not sh_j.has_text_frame:
                continue
            t = sh_j.text_frame.text.strip()
            m = _RE_VAR_LABEL.search(t)
            if m:
                var_match = m
                break

        if not var_match:
            continue  # No "Var. vs" label found nearby — skip

        label_year = var_match.group(2)  # e.g. "25" or "24"
        is_yoy = (label_year != novo_year)
        valor_correto = total_yoy if is_yoy else total_mom

        if not valor_correto or valor_correto == text:
            continue

        # Remove any existing LLM action for this shape on slide 1
        plano_out = [
            a for a in plano_out
            if not (a.get("slide_numero") == 1
                    and a.get("shape_indice") == idx_sh
                    and a.get("acao") == "alterar_texto")
        ]
        tipo_kpi = "YoY" if is_yoy else "MoM"
        plano_out.append({
            "tipo": "edicao",
            "acao": "alterar_texto",
            "slide_numero": 1,
            "shape_indice": idx_sh,
            "valor_antigo": text,
            "valor_novo": valor_correto,
            "descricao": f"[KPI-{tipo_kpi}] slide 1 shape {idx_sh}: {text} → {valor_correto}",
        })
        logger.info("[KPI] slide 1 shape %d (%s): %s → %s", idx_sh, tipo_kpi, text, valor_correto)

    return plano_out


def _corrigir_formatacao_valores(
    plano: list[dict[str, Any]],
    contexto: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fix thousand separators and percentual precision in plan values."""
    from decimal import Decimal, ROUND_HALF_UP

    sep_mil = contexto.get("separador_milhar", ".")
    sep_dec = contexto.get("separador_decimal", ",")
    casas_pct = int(contexto.get("casas_decimais_pct", 1))
    quantize_target = Decimal(f"0.{'0' * (casas_pct - 1)}1") if casas_pct else Decimal("1")

    pct_re = re.compile(r'([+-]?)(\d+)[,.](\d+)%')

    def _fix_pct(m: re.Match) -> str:
        sign, int_p, dec_p = m.group(1), m.group(2), m.group(3)
        if len(dec_p) == casas_pct:
            return m.group(0)
        val = Decimal(f"{int_p}.{dec_p}")
        rounded = val.quantize(quantize_target, rounding=ROUND_HALF_UP)
        fmt = str(rounded).replace(".", sep_dec)
        return f"{sign}{fmt}%"

    for a in plano:
        if a.get("acao") not in ("alterar_celula_tabela", "alterar_texto"):
            continue
        novo = a.get("valor_novo", "")
        if not novo:
            continue

        # 1. Fix bare integers without thousand separators
        stripped = novo.lstrip("+-")
        if stripped.isdigit() and len(stripped) >= 4:
            n = int(stripped)
            formatted = f"{n:,}".replace(",", sep_mil)
            prefix = novo[0] if novo and novo[0] in "+-" else ""
            a["valor_novo"] = prefix + formatted
            continue

        # 2. Fix percentual precision (e.g., +4,23% → +4,2% if casas_pct=1)
        novo_fixed = pct_re.sub(_fix_pct, novo)
        if novo_fixed != novo:
            a["valor_novo"] = novo_fixed
    return plano


def executar_fechamento(
    llm: LLMClient,
    obs: ObservabilityAgent,
    pptx_bytes: bytes,
    excel_files: list[tuple[str, bytes]],
    on_log: Callable[[str], None] | None = None,
    chat_col: Any = None,
    chat_stream: Any = None,
    panel_placeholder: Any = None,
    override_mes: int | None = None,
    override_ano: int | None = None,
) -> FechamentoResult:
    """Executa o pipeline completo de fechamento mensal.

    Args:
        llm: Instância do LLMClient configurada com provider/modelo.
        obs: Instância do ObservabilityAgent para monitoramento.
        pptx_bytes: Bytes do arquivo PPTX base (mês anterior).
        excel_files: Lista de tuplas (filename, file_bytes) dos Excels.
        on_log: Callback opcional para emitir mensagens de progresso.
        chat_col: Container Streamlit para logs visuais (opcional).
        chat_stream: Container Streamlit para streaming (opcional).
        panel_placeholder: Placeholder Streamlit para painel (opcional).
        override_mes: Forçar mês base (1-12). None = detecção automática.
        override_ano: Forçar ano base. None = detecção automática.

    Returns:
        FechamentoResult com o PPTX atualizado e metadados.
    """
    log_entries: list[str] = []

    def _log(msg: str) -> None:
        log_entries.append(msg)
        logger.info(msg)
        if on_log:
            on_log(msg)

    inicio = time.time()
    contexto_temporal: dict[str, Any] | None = None
    avisos_manuais: list[dict[str, Any]] = []

    # ════════════════════════════════════════════
    # ETAPA 0 — Extração de padrões do PPTX base
    # ════════════════════════════════════════════
    _log("🔍 Etapa 0/3 — Extraindo padrões de formatação do PPTX base via LLM...")
    obs.log("info", "PIPELINE", "Iniciando extração de padrões")

    padroes = extrair_padroes(llm, pptx_bytes)

    if not padroes:
        _log("❌ Não foi possível extrair padrões do PPTX. Verifique se o arquivo contém texto legível.")
        obs.log("error", "PIPELINE", "Extração de padrões falhou")
        return FechamentoResult(
            sucesso=False, pptx_bytes=pptx_bytes,
            dados_excel={}, plano=[], resultado_edicao={}, log=log_entries,
            avisos_manuais=[],
        )

    contexto_temporal = calcular_contexto(padroes, override_mes, override_ano)
    ctx_msg = formatar_contexto_para_log(contexto_temporal)
    _log(f"🗓️ {ctx_msg}")
    obs.log(
        "success", "PIPELINE",
        f"Padrões extraídos: {contexto_temporal['label_anterior']} → {contexto_temporal['label_novo']}",
    )

    # Detecção de gráficos com labels de período (não editáveis programaticamente)
    avisos_manuais = _detectar_graficos_com_periodos(pptx_bytes)
    for av in avisos_manuais:
        periodos_str = ", ".join(f'"{p}"' for p in av["periodos"])
        _log(
            f"⚠️ Gráfico no slide {av['slide']} (\"{av['shape_nome']}\") contém labels de período "
            f"({periodos_str}) que não podem ser atualizados programaticamente — "
            f"**atualização manual necessária**."
        )
        obs.log("warning", "PIPELINE",
                f"Gráfico slide {av['slide']} precisa de atualização manual de categorias")

    # ════════════════════════════════════════════
    # ETAPA 1 — Extração de dados do Excel
    # ════════════════════════════════════════════
    _log(f"📊 Etapa 1/3 — Extraindo dados de {len(excel_files)} arquivo(s) Excel (3 sub-etapas)...")
    obs.log("info", "PIPELINE", f"Iniciando análise de {len(excel_files)} Excel(s) via analisa_planilha_financeira")

    try:
        dados_excel = analisar_excel(llm, excel_files)
        if dados_excel.get("erro"):
            raise RuntimeError(dados_excel.get("resumo", "Erro desconhecido"))
        validacao = dados_excel.get("validacao", {})
        status_val = validacao.get("status", "?")
        _log(f"   Validação financeira: {status_val}")
        for alerta in validacao.get("alertas", []):
            _log(f"   ⚠️ {alerta}")
        obs.log("success", "PIPELINE", f"analisa_planilha_financeira: validação={status_val}")
    except Exception as e:
        _log(f"⚠️ analisa_planilha_financeira falhou ({e}) — usando extrai_dados_da_planilha como fallback...")
        obs.log("warning", "PIPELINE", f"analisa_planilha_financeira falhou: {e}")
        dados_excel = extrair_dados_excel(llm, excel_files)

    if dados_excel.get("erro"):
        _log(f"❌ Erro na extração do Excel: {dados_excel.get('resumo', '?')}")
        obs.log("error", "PIPELINE", f"Erro excel_reader: {dados_excel.get('resumo')}")
        return FechamentoResult(
            sucesso=False, pptx_bytes=pptx_bytes,
            dados_excel=dados_excel, plano=[], resultado_edicao={}, log=log_entries,
            contexto_temporal=contexto_temporal, avisos_manuais=avisos_manuais,
        )

    n_indicadores = len(dados_excel.get("dados", {}))
    _log(f"✅ {n_indicadores} indicador(es) financeiro(s) extraído(s).")
    _log(f"   Resumo: {dados_excel.get('resumo', 'N/A')}")
    obs.log("success", "PIPELINE", f"excel_reader: {n_indicadores} indicadores")

    # ════════════════════════════════════════════
    # ETAPA 2 — Mapeamento Excel → PPTX
    # ════════════════════════════════════════════
    _log("🗺️ Etapa 2/3 — Mapeando dados para os slides do PPTX...")
    obs.log("info", "PIPELINE", "Iniciando pptx_mapper")

    plano = gerar_plano_edicao(llm, dados_excel, pptx_bytes, contexto=contexto_temporal)

    if not plano:
        _log("⚠️ Nenhuma edição mapeada. Verifique se os dados correspondem ao layout do PPTX.")
        obs.log("warning", "PIPELINE", "pptx_mapper retornou plano vazio")
        return FechamentoResult(
            sucesso=False, pptx_bytes=pptx_bytes,
            dados_excel=dados_excel, plano=[], resultado_edicao={}, log=log_entries,
            contexto_temporal=contexto_temporal, avisos_manuais=avisos_manuais,
        )

    _log(f"✅ Plano de edição (LLM) com {len(plano)} ação(ões).")
    obs.log("success", "PIPELINE", f"pptx_mapper: {len(plano)} ações")

    # ════════════════════════════════════════════
    # ETAPA 2.5 — Complemento determinístico
    # ════════════════════════════════════════════
    # ── Filtrar ações com valor_novo vazio ──
    n_pre_filter = len(plano)
    plano = [a for a in plano if a.get("valor_novo", "").strip() != ""]
    n_empty_removed = n_pre_filter - len(plano)
    if n_empty_removed > 0:
        _log(f"⚠️ {n_empty_removed} ação(ões) ignorada(s) por valor_novo vazio.")
        obs.log("warning", "PIPELINE", f"{n_empty_removed} ações com valor_novo vazio removidas")

    _log("🔧 Complementando plano com avanço determinístico de períodos...")
    n_antes = len(plano)
    plano = _corrigir_kpis_capa_slide(pptx_bytes, plano, dados_excel, contexto_temporal)
    plano = _complementar_plano_periodos(pptx_bytes, plano, contexto_temporal)
    plano = _corrigir_tabela_com_excel(pptx_bytes, plano, excel_files, contexto_temporal)
    plano = _corrigir_formatacao_valores(plano, contexto_temporal)
    n_add = len(plano) - n_antes
    _log(f"✅ Plano final: {len(plano)} ações ({n_add} adicionadas pelo complemento).")
    obs.log("info", "PIPELINE", f"Complement: +{n_add} actions, total={len(plano)}")

    # ════════════════════════════════════════════
    # ETAPA 3 — Execução direta do plano
    # ════════════════════════════════════════════
    _log("⚙️ Etapa 3/3 — Executando edições diretamente no PPTX...")
    obs.log("info", "PIPELINE", "Iniciando execução direta do plano")

    try:
        resultado = executar_plano_direto(
            pptx_bytes=pptx_bytes,
            plano=plano,
            on_log=_log,
        )
    except Exception as e:
        _log(f"❌ Erro na execução: {e}")
        obs.log("error", "PIPELINE", f"Executor exception: {e}")
        return FechamentoResult(
            sucesso=False, pptx_bytes=pptx_bytes,
            dados_excel=dados_excel, plano=plano, resultado_edicao={}, log=log_entries,
            contexto_temporal=contexto_temporal, avisos_manuais=avisos_manuais,
        )

    pptx_final = resultado.get("pptx_bytes", pptx_bytes)
    n_ok = resultado.get("total_sucesso", 0)
    n_err = resultado.get("total_erro", 0)

    elapsed = time.time() - inicio
    _log(f"🏁 Fechamento concluído em {elapsed:.1f}s — {n_ok} OK, {n_err} erros.")
    obs.log("success", "PIPELINE",
            f"Fechamento: {n_ok} OK, {n_err} erros, {elapsed:.1f}s")

    return FechamentoResult(
        sucesso=(n_err == 0),
        pptx_bytes=pptx_final,
        dados_excel=dados_excel,
        plano=plano,
        resultado_edicao=resultado,
        log=log_entries,
        contexto_temporal=contexto_temporal,
        avisos_manuais=avisos_manuais,
    )


def _montar_instrucao_sintetica(
    plano: list[dict[str, Any]],
    dados_excel: dict[str, Any],
    contexto_temporal: dict[str, Any] | None = None,
) -> str:
    """Monta uma instrução em linguagem natural para o Orquestrador.

    Descreve as substituições necessárias de forma que o agente_interprete
    do DeckForge gere um plano equivalente ao nosso.
    """
    cabecalho = ""
    if contexto_temporal:
        cabecalho = (
            f"CONTEXTO: Este relatório é de {contexto_temporal['mes_novo_nome']}/{contexto_temporal['ano_novo']} "
            f"({contexto_temporal['label_novo']}). O mês anterior era {contexto_temporal['label_anterior']}. "
            f"Substitua TODAS as referências de data de '{contexto_temporal['label_anterior']}' "
            f"por '{contexto_temporal['label_novo']}', e variações como "
            f"'{contexto_temporal['mes_base_nome']} {contexto_temporal['ano_base']}' "
            f"por '{contexto_temporal['mes_novo_nome']} {contexto_temporal['ano_novo']}'.\n"
            f"PADRÕES: percentuais como {contexto_temporal.get('formato_percentual_positivo', '+X,X%')}, "
            f"valores como {contexto_temporal.get('formato_valor_tabela', '19.230')}, "
            f"separador decimal '{contexto_temporal.get('separador_decimal', ',')}', "
            f"milhar '{contexto_temporal.get('separador_milhar', '.')}'.\n\n"
        )

    linhas: list[str] = [
        cabecalho +
        "Atualize os dados deste PPTX com os valores do fechamento mensal mais recente. "
        "Execute EXATAMENTE as seguintes substituições:\n"
    ]

    for i, cmd in enumerate(plano, 1):
        acao = cmd.get("acao", "?")
        desc = cmd.get("descricao", "")
        antigo = cmd.get("valor_antigo", "")
        novo = cmd.get("valor_novo", "")
        slide = cmd.get("slide_numero")

        if acao == "substituir_texto_global":
            linhas.append(f'{i}. Substituir globalmente "{antigo}" por "{novo}". ({desc})')
        elif acao == "alterar_celula_tabela":
            row = cmd.get("tabela_linha", "?")
            col = cmd.get("tabela_coluna", "?")
            linhas.append(
                f'{i}. No slide {slide}, tabela linha {row} coluna {col}: '
                f'alterar "{antigo}" para "{novo}". ({desc})'
            )
        elif acao == "alterar_texto":
            linhas.append(
                f'{i}. No slide {slide}: alterar "{antigo}" para "{novo}". ({desc})'
            )
        else:
            linhas.append(f'{i}. {acao}: {desc} (slide {slide})')

    linhas.append(
        "\nIMPORTANTE: Execute TODAS as substituições listadas acima. "
        "Não faça perguntas. Não adicione nem remova elementos."
    )

    return "\n".join(linhas)
