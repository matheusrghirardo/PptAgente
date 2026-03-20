"""
gera_previsualizacao_html_do_pptx.py — Gerador de preview HTML fiel do PPTX para visualização no navegador.
Converte shapes, tabelas e gráficos em HTML com posicionamento absoluto.
"""

from io import BytesIO
from html import escape as _esc

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu

# ─────────────────────────────────────────────────
# Constantes de conversão
# ─────────────────────────────────────────────────
_EMU_PER_PX = 9525  # 1 px @96dpi = 9525 EMU

# Slide padrão 10 × 7.5 in → 960 × 720 px @96 DPI
# Mas muitos decks B3 usam 13.33 × 7.5 → widescreen
# Detectamos dinamicamente a partir de prs.slide_width / slide_height.
_PREVIEW_SCALE = 1.0  # será recalculado se slide for maior que 960px


def _emu_to_px(emu, scale: float = 1.0) -> float:
    """Converte EMU para pixels CSS (@96 DPI), opcionalmente escalado."""
    if emu is None:
        return 0.0
    return round(int(emu) / _EMU_PER_PX * scale, 1)


def _rgb_to_hex(rgb) -> str:
    """Converte RGBColor (ou None) para string hex CSS."""
    if rgb is None:
        return None
    try:
        return f"#{rgb}"
    except Exception:
        return None


def _get_fill_color(obj) -> str | None:
    """Extrai cor de preenchimento sólido de shape ou célula."""
    try:
        fill = obj.fill
        if fill.type is not None and str(fill.type) == "SOLID (1)":
            if fill.fore_color and fill.fore_color.type is not None:
                return _rgb_to_hex(fill.fore_color.rgb)
    except Exception:
        pass
    return None


def _get_border(shape) -> tuple[str | None, float]:
    """Retorna (cor_hex, largura_px) da borda do shape."""
    try:
        ln = shape.line
        if ln.fill.type is not None:
            color = _rgb_to_hex(ln.color.rgb)
            width = round(ln.width.pt, 1) if ln.width else 1.0
            return color, width
    except Exception:
        pass
    return None, 0


def _align_css(alignment) -> str:
    """Converte PP_ALIGN para text-align CSS."""
    if alignment is None:
        return "left"
    try:
        if alignment == PP_ALIGN.CENTER:
            return "center"
        if alignment == PP_ALIGN.RIGHT:
            return "right"
        if alignment == PP_ALIGN.JUSTIFY:
            return "justify"
    except Exception:
        pass
    return "left"


# ─────────────────────────────────────────────────
# Extratores de dados dos shapes
# ─────────────────────────────────────────────────

def _extrair_runs_html(paragraph) -> str:
    """Converte runs de um parágrafo para spans HTML com formatação inline."""
    parts = []
    for run in paragraph.runs:
        text = _esc(run.text)
        if not text:
            continue
        styles = []
        font = run.font
        if font.size:
            styles.append(f"font-size:{round(font.size.pt)}pt")
        color = None
        try:
            if font.color and font.color.type is not None:
                color = _rgb_to_hex(font.color.rgb)
        except Exception:
            pass
        if color:
            styles.append(f"color:{color}")
        if font.bold:
            styles.append("font-weight:bold")
        if font.italic:
            styles.append("font-style:italic")
        if font.underline:
            styles.append("text-decoration:underline")
        if font.name:
            styles.append(f"font-family:'{_esc(font.name)}',Arial,sans-serif")
        if styles:
            parts.append(f'<span style="{";".join(styles)}">{text}</span>')
        else:
            parts.append(text)
    return "".join(parts) if parts else _esc(paragraph.text)


def _extrair_paragrafos_html(text_frame) -> str:
    """Gera HTML para todos os parágrafos de um text_frame."""
    blocks = []
    for para in text_frame.paragraphs:
        align = _align_css(para.alignment)
        inner = _extrair_runs_html(para)
        if not inner.strip():
            inner = "&nbsp;"
        blocks.append(f'<div style="text-align:{align}">{inner}</div>')
    return "\n".join(blocks)


def _render_text_shape(shape, scale: float) -> str:
    """Renderiza shape com texto como div posicionado."""
    left = _emu_to_px(shape.left, scale)
    top = _emu_to_px(shape.top, scale)
    w = _emu_to_px(shape.width, scale)
    h = _emu_to_px(shape.height, scale)

    css_parts = [
        f"left:{left}px", f"top:{top}px",
        f"width:{w}px", f"height:{h}px",
        "overflow:hidden", "word-wrap:break-word",
        "display:flex", "flex-direction:column", "justify-content:center",
        "padding:4px 8px",
    ]

    fill = _get_fill_color(shape)
    if fill:
        css_parts.append(f"background:{fill}")

    border_color, border_w = _get_border(shape)
    if border_color:
        css_parts.append(f"border:{border_w}px solid {border_color}")

    inner = _extrair_paragrafos_html(shape.text_frame)
    style = ";".join(css_parts)
    return f'<div class="shape" style="{style}">{inner}</div>\n'


def _render_table_shape(shape, scale: float) -> str:
    """Renderiza tabela como <table> posicionada."""
    left = _emu_to_px(shape.left, scale)
    top = _emu_to_px(shape.top, scale)
    w = _emu_to_px(shape.width, scale)
    h = _emu_to_px(shape.height, scale)

    table = shape.table
    rows_html = []
    for ri, row in enumerate(table.rows):
        cells_html = []
        for ci, cell in enumerate(row.cells):
            td_styles = ["padding:4px 6px", "vertical-align:middle"]
            cell_fill = _get_fill_color(cell)
            if cell_fill:
                td_styles.append(f"background:{cell_fill}")
            # Formatação do texto da célula
            inner = ""
            if cell.text_frame:
                inner = _extrair_paragrafos_html(cell.text_frame)
            else:
                inner = _esc(cell.text)
            td_style = ";".join(td_styles)
            cells_html.append(f'<td style="{td_style}">{inner}</td>')
        rows_html.append(f'<tr>{"".join(cells_html)}</tr>')

    style = (f"left:{left}px;top:{top}px;width:{w}px;height:{h}px")
    return (
        f'<div class="table-wrap" style="{style}">\n'
        f'<table>\n{"".join(rows_html)}\n</table>\n'
        f'</div>\n'
    )


def _render_chart_shape(shape, scale: float) -> str:
    """Renderiza placeholder de gráfico (título + tipo)."""
    left = _emu_to_px(shape.left, scale)
    top = _emu_to_px(shape.top, scale)
    w = _emu_to_px(shape.width, scale)
    h = _emu_to_px(shape.height, scale)

    chart = shape.chart
    title = "(sem título)"
    try:
        if chart.has_title:
            title = _esc(chart.chart_title.text_frame.text)
    except Exception:
        pass

    chart_type = str(chart.chart_type) if chart else "?"
    chart_type_clean = chart_type.replace("(", "").replace(")", "").split(".")[-1]

    style = f"left:{left}px;top:{top}px;width:{w}px;height:{h}px"
    return (
        f'<div class="chart-ph" style="{style}">\n'
        f'  <div class="chart-icon">📊</div>\n'
        f'  <div class="chart-title">{title}</div>\n'
        f'  <div class="chart-sub">{chart_type_clean}</div>\n'
        f'</div>\n'
    )


def _render_generic_shape(shape, scale: float) -> str:
    """Renderiza shape genérico (retângulo, etc.) como caixa colorida."""
    left = _emu_to_px(shape.left, scale)
    top = _emu_to_px(shape.top, scale)
    w = _emu_to_px(shape.width, scale)
    h = _emu_to_px(shape.height, scale)

    css = [f"left:{left}px", f"top:{top}px", f"width:{w}px", f"height:{h}px"]

    fill = _get_fill_color(shape)
    if fill:
        css.append(f"background:{fill}")
    else:
        css.append("background:rgba(200,200,200,0.15)")

    border_color, border_w = _get_border(shape)
    if border_color:
        css.append(f"border:{border_w}px solid {border_color}")
    else:
        css.append("border:1px solid rgba(0,0,0,0.08)")

    style = ";".join(css)
    return f'<div class="shape" style="{style}"></div>\n'


def _render_picture_shape(shape, scale: float) -> str:
    """Renderiza placeholder de imagem."""
    left = _emu_to_px(shape.left, scale)
    top = _emu_to_px(shape.top, scale)
    w = _emu_to_px(shape.width, scale)
    h = _emu_to_px(shape.height, scale)

    style = f"left:{left}px;top:{top}px;width:{w}px;height:{h}px"
    return (
        f'<div class="img-ph" style="{style}">\n'
        f'  <div style="font-size:28px">🖼️</div>\n'
        f'  <div style="font-size:11px;color:#94a3b8">Imagem</div>\n'
        f'</div>\n'
    )


# ─────────────────────────────────────────────────
# Renderizador de shape (dispatch)
# ─────────────────────────────────────────────────

def _render_shape(shape, scale: float) -> str:
    """Dispatch: renderiza um shape de acordo com o tipo."""
    try:
        if shape.has_table:
            return _render_table_shape(shape, scale)
        if hasattr(shape, "has_chart") and shape.has_chart:
            return _render_chart_shape(shape, scale)
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            return _render_picture_shape(shape, scale)
        if shape.has_text_frame:
            return _render_text_shape(shape, scale)
        return _render_generic_shape(shape, scale)
    except Exception:
        return ""


# ─────────────────────────────────────────────────
# CSS do preview
# ─────────────────────────────────────────────────

_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',Calibri,Arial,sans-serif;background:#171717;padding:32px 16px}
.hdr{text-align:center;color:#E8E8E8;margin-bottom:32px}
.hdr h1{font-size:28px;margin-bottom:6px}
.hdr p{color:#9E9E9E;font-size:14px}
.slides{max-width:__MAX_W__px;margin:0 auto}
.slide-wrap{margin-bottom:36px;position:relative}
.slide-num{color:#9E9E9E;font-size:13px;font-weight:600;margin-bottom:6px}
.slide{width:__SW__px;height:__SH__px;background:#fff;position:relative;
  border:1px solid #333;border-radius:3px;overflow:hidden}
.shape{position:absolute}
.table-wrap{position:absolute;overflow:auto}
.table-wrap table{border-collapse:collapse;width:100%;height:100%;font-size:11pt}
.table-wrap td{border:1px solid #333;padding:4px 6px;text-align:left;vertical-align:middle}
.chart-ph{position:absolute;background:#2b2b2b;border:2px dashed #333;
  display:flex;align-items:center;justify-content:center;flex-direction:column;color:#9E9E9E;
  border-radius:4px}
.chart-icon{font-size:40px;margin-bottom:6px}
.chart-title{font-weight:700;font-size:14px}
.chart-sub{font-size:11px;color:#666;margin-top:2px}
.img-ph{position:absolute;background:#2b2b2b;border:2px dashed #333;
  display:flex;align-items:center;justify-content:center;flex-direction:column;
  border-radius:4px}
.ft{text-align:center;color:#666;margin-top:48px;font-size:13px}
"""


# ─────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────

def gerar_preview_html(pptx_bytes: bytes, max_render_width: int = 960) -> str:
    """
    Gera string HTML completa com preview visual fiel do PPTX.

    Args:
        pptx_bytes: bytes do arquivo .pptx
        max_render_width: largura máxima em px para render (padrão 960)

    Returns:
        String HTML completa (pode ser salva em arquivo ou injetada via st.components).
    """
    prs = Presentation(BytesIO(pptx_bytes))

    # Dimensões reais do slide
    sw_emu = int(prs.slide_width)
    sh_emu = int(prs.slide_height)
    sw_px = sw_emu / _EMU_PER_PX
    sh_px = sh_emu / _EMU_PER_PX

    # Escalar para caber no max_render_width
    if sw_px > max_render_width:
        scale = max_render_width / sw_px
    else:
        scale = 1.0

    render_w = round(sw_px * scale)
    render_h = round(sh_px * scale)

    css = _CSS.replace("__MAX_W__", str(render_w + 40))
    css = css.replace("__SW__", str(render_w))
    css = css.replace("__SH__", str(render_h))

    slides_html = []
    for idx, slide in enumerate(prs.slides):
        shapes_html = []
        for shape in slide.shapes:
            shapes_html.append(_render_shape(shape, scale))

        slide_bg = ""
        try:
            bg = slide.background
            bg_fill = _get_fill_color(bg)
            if bg_fill:
                slide_bg = f"background:{bg_fill};"
        except Exception:
            pass

        slides_html.append(
            f'<div class="slide-wrap">\n'
            f'  <div class="slide-num">Slide {idx + 1}</div>\n'
            f'  <div class="slide" style="{slide_bg}">\n'
            f'    {"".join(shapes_html)}'
            f'  </div>\n'
            f'</div>\n'
        )

    total = len(prs.slides)
    body = "".join(slides_html)

    html = (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>DeckForge Preview</title>\n'
        f'<style>{css}</style>\n'
        '</head>\n<body>\n'
        '<div class="hdr">\n'
        '  <h1><svg width="24" height="20" viewBox="0 0 24 20" style="vertical-align:middle;margin-right:6px"><rect x="2" y="4" width="20" height="14" rx="4" fill="#E2A44033" stroke="#E2A440" stroke-width="1.5"/><rect x="7" y="8" width="3" height="4" rx="1" fill="#E2A440"/><rect x="14" y="8" width="3" height="4" rx="1" fill="#E2A440"/><line x1="12" y1="0" x2="12" y2="4" stroke="#E2A440" stroke-width="1.5"/><circle cx="12" cy="0" r="2" fill="#E2A440"/></svg>DeckForge Preview</h1>\n'
        f'  <p>{total} slide{"s" if total != 1 else ""}</p>\n'
        '</div>\n'
        f'<div class="slides">\n{body}</div>\n'
        '<div class="ft">Preview aproximado — baixe o PPTX para resultado final.</div>\n'
        '</body>\n</html>'
    )
    return html


def gerar_preview_html_inline(pptx_bytes: bytes, max_width: int = 900) -> str:
    """
    Gera HTML *inline* (sem <html>/<body>) pronto para st.components.v1.html().
    Adequado para embutir dentro do Streamlit.

    Args:
        pptx_bytes: bytes do .pptx
        max_width: largura máxima do render

    Returns:
        String HTML que pode ser usada em st.components.v1.html(html, height=...)
    """
    prs = Presentation(BytesIO(pptx_bytes))

    sw_emu = int(prs.slide_width)
    sh_emu = int(prs.slide_height)
    sw_px = sw_emu / _EMU_PER_PX
    sh_px = sh_emu / _EMU_PER_PX

    if sw_px > max_width:
        scale = max_width / sw_px
    else:
        scale = 1.0

    render_w = round(sw_px * scale)
    render_h = round(sh_px * scale)

    total_slides = len(prs.slides)
    # Altura necessária: slides + gaps + header + footer
    total_height = total_slides * (render_h + 52) + 80

    css_inline = f"""
    <style>
    .df-preview *{{margin:0;padding:0;box-sizing:border-box}}
    .df-preview{{font-family:'Inter',Calibri,Arial,sans-serif;background:#171717;
      padding:16px;border-radius:8px}}
    .df-hdr{{text-align:center;color:#E8E8E8;margin-bottom:20px}}
    .df-hdr h2{{font-size:18px;margin-bottom:4px}}
    .df-hdr p{{color:#9E9E9E;font-size:12px}}
    .df-slide-wrap{{margin-bottom:28px;position:relative}}
    .df-slide-num{{color:#9E9E9E;font-size:11px;font-weight:600;margin-bottom:4px}}
    .df-slide{{width:{render_w}px;height:{render_h}px;background:#fff;position:relative;
      border:1px solid #333;border-radius:3px;overflow:hidden;
      margin:0 auto}}
    .df-slide .shape{{position:absolute}}
    .df-slide .table-wrap{{position:absolute;overflow:auto}}
    .df-slide .table-wrap table{{border-collapse:collapse;width:100%;height:100%;font-size:10pt}}
    .df-slide .table-wrap td{{border:1px solid #333;padding:3px 5px;text-align:left;
      vertical-align:middle}}
    .df-slide .chart-ph{{position:absolute;background:#2b2b2b;border:2px dashed #333;
      display:flex;align-items:center;justify-content:center;flex-direction:column;
      color:#9E9E9E;border-radius:4px}}
    .df-slide .chart-icon{{font-size:32px;margin-bottom:4px}}
    .df-slide .chart-title{{font-weight:700;font-size:12px}}
    .df-slide .chart-sub{{font-size:10px;color:#666;margin-top:2px}}
    .df-slide .img-ph{{position:absolute;background:#2b2b2b;border:2px dashed #333;
      display:flex;align-items:center;justify-content:center;flex-direction:column;
      border-radius:4px}}
    .df-ft{{text-align:center;color:#666;font-size:11px;margin-top:16px}}
    </style>
    """

    slides_html = []
    for idx, slide in enumerate(prs.slides):
        shapes_html = []
        for shape in slide.shapes:
            shapes_html.append(_render_shape(shape, scale))

        slide_bg = ""
        try:
            bg_fill = _get_fill_color(slide.background)
            if bg_fill:
                slide_bg = f"background:{bg_fill};"
        except Exception:
            pass

        slides_html.append(
            f'<div class="df-slide-wrap">\n'
            f'  <div class="df-slide-num">Slide {idx + 1}</div>\n'
            f'  <div class="df-slide" style="{slide_bg}">\n'
            f'    {"".join(shapes_html)}'
            f'  </div>\n'
            f'</div>\n'
        )

    body = "".join(slides_html)

    return (
        f'{css_inline}\n'
        f'<div class="df-preview">\n'
        f'  <div class="df-hdr">\n'
        f'    <h2><svg width="20" height="16" viewBox="0 0 24 20" style="vertical-align:middle;margin-right:4px"><rect x="2" y="4" width="20" height="14" rx="4" fill="#E2A44033" stroke="#E2A440" stroke-width="1.5"/><rect x="7" y="8" width="3" height="4" rx="1" fill="#E2A440"/><rect x="14" y="8" width="3" height="4" rx="1" fill="#E2A440"/><line x1="12" y1="0" x2="12" y2="4" stroke="#E2A440" stroke-width="1.5"/><circle cx="12" cy="0" r="2" fill="#E2A440"/></svg>DeckForge Preview</h2>\n'
        f'    <p>{total_slides} slide{"s" if total_slides != 1 else ""}</p>\n'
        f'  </div>\n'
        f'  {body}'
        f'  <div class="df-ft">Preview aproximado</div>\n'
        f'</div>'
    ), total_height
