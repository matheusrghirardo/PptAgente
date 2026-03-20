"""
componentes_visuais_da_interface.py - B3 Executive UI Components for DeckForge
==============================================================
Redesign institucional para apresentação ao time de controladoria.
Paleta B3, tipografia Barlow/Inter/JetBrains Mono, layout denso e preciso.
"""

from __future__ import annotations

import re

# ---------- B3 Palette ----------
_P = {
    "deep":    "#0a0349",
    "white":   "#FFFFFF",
    "sky":     "#f0f4fa",
    "card_b":  "#dde9f6",
    "coral":   "#f5ba94",
    "green":   "#003321",
    "action":  "#1818b7",
    "muted":   "#94A3B8",
    "body":    "#334155",
}

# ---------- GLOBAL CSS ----------
GLOBAL_CSS = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@200;600;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400&display=swap');

:root {{
  --b3-deep:    {_P["deep"]};
  --b3-white:   {_P["white"]};
  --b3-sky:     {_P["sky"]};
  --b3-card-b:  {_P["card_b"]};
  --b3-coral:   {_P["coral"]};
  --b3-green:   {_P["green"]};
  --b3-action:  {_P["action"]};
  --b3-muted:   {_P["muted"]};
  --b3-body:    {_P["body"]};
  --font-display: 'Barlow', sans-serif;
  --font-body:    'Inter', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;
}}

/* === RESETS === */
.stApp {{ background: var(--b3-white) !important; font-family: var(--font-body) !important; color: var(--b3-body) !important; }}
[data-testid="collapsedControl"],
[data-testid="stSidebar"],
[data-testid="stHeader"],
footer {{ display: none !important; visibility: hidden !important; }}
[data-testid="stDecoration"] {{ background-image: none !important; background: var(--b3-white) !important; }}
.block-container {{
  padding-top: 0 !important; padding-bottom: 1rem !important;
  padding-left: 2rem !important; padding-right: 2rem !important;
  max-width: 100% !important;
}}
*:focus, *:focus-within, *:focus-visible {{
  outline: none !important; box-shadow: none !important;
}}
::selection {{ background: rgba(10,3,73,.18); }}

/* Hide fixed top-left overlay elements (screencast / dev overlay) */
.st-emotion-cache-hzo1qh, .st-emotion-cache-19ee8pt, button.st-emotion-cache-1rg1gxd {{
  display: none !important; visibility: hidden !important;
}}

/* === HEADER === */
.df-header {{
  height: 56px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; background: var(--b3-deep);
  margin-bottom: 0; position: sticky; top: 0; z-index: 100;
}}
.df-header-left {{ display: flex; align-items: center; gap: 14px; }}
.df-header-brand {{ display: flex; flex-direction: column; gap: 1px; }}
.df-header-name {{
  font-family: var(--font-display); font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.18em; color: var(--b3-white);
}}
.df-header-sub {{
  font-family: var(--font-body); font-size: 10px; font-weight: 400;
  color: rgba(255,255,255,0.55);
}}
.df-header-right {{
  display: flex; align-items: center; gap: 18px;
}}
.df-header-tag {{
  font-family: var(--font-body); font-size: 9px; font-weight: 500;
  text-transform: uppercase; padding: 3px 8px;
  border: 1px solid rgba(255,255,255,0.2); border-radius: 3px;
  color: rgba(255,255,255,0.55); letter-spacing: 0.06em;
}}

/* === SECTION LABEL === */
.df-section-label {{
  font-family: var(--font-body); font-size: 9px; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.15em; color: var(--b3-deep);
  margin-bottom: 16px; margin-top: 0;
}}

/* === INPUT CARD === */
.df-input-card {{
  padding: 16px; border: 1px solid var(--b3-card-b);
  border-radius: 6px; background: var(--b3-white); margin-bottom: 12px;
  transition: border-color .2s;
}}
.df-input-card.loaded {{
  border-left: 3px solid var(--b3-deep); background: #f8fafd;
}}
.df-input-card-header {{
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}}
.df-input-card-icon {{ width: 16px; height: 16px; color: var(--b3-action); flex-shrink: 0; }}
.df-input-card-title {{
  font-family: var(--font-display); font-size: 14px; font-weight: 600; color: var(--b3-deep);
}}
.df-input-card-desc {{
  font-family: var(--font-body); font-size: 12px; font-weight: 400; color: var(--b3-body);
}}
.df-file-ok {{
  font-family: var(--font-body); font-size: 13px; font-weight: 500;
  color: var(--b3-green); margin-top: 6px;
}}
.df-file-meta {{
  font-family: var(--font-body); font-size: 11px; font-weight: 400;
  color: var(--b3-body); opacity: 0.7; margin-top: 2px;
}}

/* === INPUT SEPARATOR === */
.df-input-sep {{ height: 1px; background: var(--b3-card-b); margin: 4px 0; border: none; }}

/* === BUTTON PRIMARY === */
.stButton > button[kind="primary"] {{
  background: var(--b3-deep) !important; color: var(--b3-white) !important;
  font-family: var(--font-display) !important; font-weight: 700 !important;
  font-size: 13px !important; letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  height: 48px !important; border-radius: 6px !important;
  border: none !important; transition: background .2s !important;
  box-shadow: none !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: var(--b3-action) !important;
  box-shadow: none !important;
}}
.stButton > button[disabled] {{
  background: var(--b3-card-b) !important; color: var(--b3-muted) !important;
  box-shadow: none !important; cursor: not-allowed !important;
}}

/* === DOWNLOAD BUTTON === */
.df-download .stDownloadButton > button {{
  background: transparent !important; color: var(--b3-white) !important;
  border: 1px solid rgba(255,255,255,0.3) !important; font-weight: 500 !important;
  font-family: var(--font-body) !important; font-size: 12px !important;
  border-radius: 4px !important; height: 40px !important;
  transition: background .2s !important;
}}
.df-download .stDownloadButton > button:hover {{
  background: rgba(255,255,255,0.1) !important;
}}

/* === PIPELINE VERTICAL === */
.df-pipeline-card {{
  padding: 28px; border: 1px solid var(--b3-card-b);
  border-radius: 8px; background: #f8fafd;
  position: relative; overflow: hidden;
}}
.df-pipeline-card::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--b3-deep), var(--b3-action), var(--b3-coral));
  opacity: 0.7;
}}
.df-pipeline-title {{
  font-family: var(--font-display); font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.18em;
  color: var(--b3-deep); margin-bottom: 24px;
  display: flex; align-items: center; gap: 8px;
}}
.df-pipeline-title::before {{
  content: ''; display: inline-block; width: 8px; height: 8px;
  background: var(--b3-coral); border-radius: 50%;
  animation: title-pulse 2s ease-in-out infinite;
}}
@keyframes title-pulse {{
  0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }}
}}
.df-pipeline-agents {{ display: flex; flex-direction: column; gap: 0; }}

.df-agent-row {{
  display: flex; align-items: flex-start; gap: 16px; min-height: 64px;
  transition: all 0.3s ease;
}}
.df-agent-row.compact {{ min-height: 20px; }}
.df-agent-row.active-row {{
  background: rgba(24,24,183,0.03); border-radius: 8px;
  padding: 8px; margin: -8px; margin-bottom: 0;
}}

/* Connector column */
.df-agent-track {{
  display: flex; flex-direction: column; align-items: center; width: 10px; flex-shrink: 0;
  position: relative;
}}
.df-agent-dot {{
  width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid;
  flex-shrink: 0; position: relative; z-index: 2;
  display: flex; align-items: center; justify-content: center;
}}
.df-agent-dot.waiting {{ background: var(--b3-card-b); border-color: #aabdd8; }}
.df-agent-dot.processing {{
  background: var(--b3-coral); border-color: var(--b3-coral);
  animation: status-pulse 1.4s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(245,186,148,0.6), 0 0 16px rgba(245,186,148,0.3);
}}
.df-agent-dot.done {{ background: var(--b3-deep); border-color: var(--b3-deep); }}
.df-agent-dot.done::after {{
  content: ''; display: block; width: 4px; height: 4px;
  border-bottom: 1.5px solid var(--b3-white); border-right: 1.5px solid var(--b3-white);
  transform: rotate(45deg) translate(-0.5px, -0.5px);
}}
.df-agent-line {{
  width: 1px; flex: 1; min-height: 12px;
}}
.df-agent-line.waiting {{ background: var(--b3-card-b); }}
.df-agent-line.done {{ background: var(--b3-deep); }}
.df-agent-line.active {{ background: var(--b3-deep); animation: connector-fill 0.6s ease forwards; }}

/* Text column */
.df-agent-info {{ display: flex; flex-direction: column; gap: 2px; padding-top: 0; }}
.df-agent-name {{
  font-family: var(--font-body); font-size: 13px; font-weight: 600; transition: color .3s, opacity .3s;
}}
.df-agent-name.waiting {{ color: var(--b3-body); opacity: 0.5; }}
.df-agent-name.processing {{ color: var(--b3-deep); opacity: 1; }}
.df-agent-name.done {{ color: var(--b3-deep); opacity: 1; }}
.df-agent-status {{
  font-family: var(--font-body); font-size: 11px; font-weight: 400;
  color: var(--b3-body); opacity: 0.7;
}}

/* SVG column */
.df-agent-svg {{
  width: 48px; height: 48px; flex-shrink: 0; transition: all .4s ease;
}}
.df-agent-svg.waiting {{ opacity: 0.18; filter: grayscale(1); }}
.df-agent-svg.processing {{
  opacity: 1; filter: drop-shadow(0 0 6px rgba(24,24,183,0.35));
}}
.df-agent-svg.done {{ opacity: 1; filter: none; }}

/* Agent activity bubble */
.df-agent-bubble {{
  font-family: var(--font-mono); font-size: 10px; color: var(--b3-action);
  background: rgba(24,24,183,0.06); border: 1px solid rgba(24,24,183,0.12);
  border-radius: 4px; padding: 4px 8px; margin-top: 4px;
  animation: bubble-in 0.3s ease forwards;
  position: relative;
}}
.df-agent-bubble::before {{
  content: ''; position: absolute; top: 50%; left: -5px;
  transform: translateY(-50%); border: 4px solid transparent;
  border-right-color: rgba(24,24,183,0.12);
}}
.df-agent-bubble .cursor-blink {{
  display: inline-block; width: 1px; height: 10px;
  background: var(--b3-action); margin-left: 2px;
  animation: cursor-blink 0.8s step-end infinite;
}}
@keyframes bubble-in {{ from {{ opacity:0; transform: translateX(-4px); }} to {{ opacity:1; transform: translateX(0); }} }}
@keyframes cursor-blink {{ 0%, 50% {{ opacity: 1; }} 51%, 100% {{ opacity: 0; }} }}

/* === RESULTADO CARD === */
.df-result-card {{
  border-left: 3px solid var(--b3-coral);
  background: var(--b3-deep); padding: 24px 20px;
  border-radius: 0 6px 6px 0; margin: 16px 0;
}}
.df-result-big {{
  font-family: var(--font-display); font-size: 72px; font-weight: 200;
  color: var(--b3-white); line-height: 1;
}}
.df-result-label {{
  font-family: var(--font-body); font-size: 11px; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: rgba(255,255,255,0.55); margin-top: 4px;
}}
.df-result-status {{
  font-family: var(--font-body); font-size: 12px; font-weight: 400;
  color: rgba(255,255,255,0.7); margin-top: 8px;
}}
.df-result-sep {{
  height: 1px; background: rgba(255,255,255,0.15); margin: 16px 0; border: none;
}}
.df-result-metrics {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
}}
.df-result-metric-val {{
  font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--b3-white);
}}
.df-result-metric-lbl {{
  font-family: var(--font-body); font-size: 9px; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: rgba(255,255,255,0.55);
}}

/* === AVISO CARD === */
.df-aviso-card {{
  border-radius: 6px; padding: 18px 24px;
  background: rgba(255,205,0,.06); border: 1px solid rgba(255,205,0,.25);
  margin: 12px 0;
}}
.df-aviso-title {{
  font-family: var(--font-display); font-size: 14px; font-weight: 600;
  color: var(--b3-deep); margin-bottom: 8px;
}}
.df-aviso-item {{
  font-family: var(--font-body); font-size: 13px; color: var(--b3-body);
  padding: 4px 0; border-bottom: 1px solid rgba(255,205,0,.12);
}}
.df-aviso-item:last-child {{ border-bottom: none; }}

/* === LOG AREA === */
.df-log-container {{
  background: #080825; border-radius: 8px; padding: 20px 24px;
  max-height: 400px; overflow-y: auto; margin: 12px 0;
  border: 1px solid rgba(24,24,183,0.25);
  position: relative;
  box-shadow: inset 0 0 30px rgba(0,0,0,0.3), 0 0 20px rgba(10,3,73,0.15);
}}
.df-log-container::before {{
  content: '> TERMINAL DE EXECUCAO'; display: block;
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.15em;
  color: rgba(24,24,183,0.5); margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid rgba(24,24,183,0.15);
}}
.df-log-container::-webkit-scrollbar {{ width: 4px; }}
.df-log-container::-webkit-scrollbar-track {{ background: transparent; }}
.df-log-container::-webkit-scrollbar-thumb {{ background: var(--b3-action); border-radius: 2px; }}
.df-log-entry {{
  font-family: var(--font-mono); font-size: 11px; line-height: 2;
  color: rgba(160,200,255,0.85); padding-bottom: 2px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  animation: log-slide 0.3s ease forwards;
}}
.df-log-entry:last-child {{
  border-bottom: none;
  color: rgba(200,230,255,0.95);
}}
.df-log-entry:last-child::after {{
  content: ''; display: inline-block; width: 6px; height: 12px;
  background: rgba(245,186,148,0.8); margin-left: 6px; vertical-align: middle;
  animation: cursor-blink 0.8s step-end infinite;
}}
@keyframes log-slide {{ from {{ opacity:0; transform: translateY(4px); }} to {{ opacity:1; transform: translateY(0); }} }}

/* === SEPARATOR === */
.df-sep {{ height: 1px; background: var(--b3-card-b); margin: 20px 0; border: none; }}

/* === ANIMATIONS === */
@keyframes status-pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); box-shadow: 0 0 8px rgba(245,186,148,0.6); }}
  50% {{ opacity: 0.7; transform: scale(0.85); box-shadow: 0 0 16px rgba(245,186,148,0.4); }}
}}
@keyframes connector-fill {{
  from {{ height: 0%; }}
  to {{ height: 100%; }}
}}

/* === AGENT SVG ANIMATIONS === */
@keyframes agent-pulse {{
  0%, 100% {{ transform: scale(1); }}
  50% {{ transform: scale(0.97); }}
}}
@keyframes agent-blink {{
  0%, 40%, 44%, 100% {{ opacity: 1; }}
  42% {{ opacity: 0; }}
}}
@keyframes agent-lupa-rotate {{
  0%, 100% {{ transform: rotate(0deg); }}
  50% {{ transform: rotate(12deg); }}
}}
@keyframes agent-setas-move {{
  0%, 100% {{ transform: translateX(0); }}
  50% {{ transform: translateX(3px); }}
}}
@keyframes agent-caneta-write {{
  0%, 100% {{ transform: translateY(0) rotate(0deg); }}
  25% {{ transform: translateY(1px) rotate(-3deg); }}
  75% {{ transform: translateY(-1px) rotate(3deg); }}
}}
@keyframes agent-sheet-bounce {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-2px); }}
}}
@keyframes agent-check-in {{
  0% {{ opacity: 0; transform: scale(0.3); }}
  100% {{ opacity: 1; transform: scale(1); }}
}}
.df-agent-svg.processing .agent-body {{ animation: agent-pulse 2s ease-in-out infinite; }}
.df-agent-svg.processing .agent-eyes {{ animation: agent-blink 1.5s ease-in-out infinite; }}
.df-agent-svg.processing .agent-action-lupa {{ animation: agent-lupa-rotate 1s ease-in-out infinite; transform-origin: 36px 20px; }}
.df-agent-svg.processing .agent-action-setas {{ animation: agent-setas-move 1s ease-in-out infinite; }}
.df-agent-svg.processing .agent-action-caneta {{ animation: agent-caneta-write 1s ease-in-out infinite; transform-origin: 38px 30px; }}
.df-agent-svg.processing .agent-action-sheet {{ animation: agent-sheet-bounce 1s ease-in-out infinite; }}
.df-agent-svg .agent-check {{ display: none; }}
.df-agent-svg.done .agent-check {{
  display: block; animation: agent-check-in 0.4s ease forwards;
}}

/* === STREAMLIT WIDGET OVERRIDES === */
.stSelectbox label, .stTextInput label, .stNumberInput label,
.stFileUploader label, .stCheckbox label {{
  font-family: var(--font-body) !important; font-size: 11px !important;
  text-transform: uppercase !important; letter-spacing: 0.08em !important;
  color: var(--b3-muted) !important; font-weight: 500 !important;
}}
.stSelectbox [data-baseweb="select"] {{
  border-color: var(--b3-card-b) !important; border-radius: 6px !important;
}}
.stTextInput input {{
  border-color: var(--b3-card-b) !important; border-radius: 6px !important;
  font-family: var(--font-body) !important;
}}
div[data-testid="stExpander"] {{
  border: 1px solid var(--b3-card-b) !important; border-radius: 6px !important;
  background: var(--b3-white) !important;
}}
div[data-testid="stExpander"] summary {{
  font-family: var(--font-body) !important; font-size: 11px !important;
  text-transform: uppercase !important; letter-spacing: 0.06em !important;
  color: var(--b3-deep) !important; font-weight: 500 !important;
}}

/* === FILE UPLOADER TAMING === */
[data-testid="stFileUploader"] {{
  margin-top: 8px;
}}
[data-testid="stFileUploader"] section {{
  border: 1px dashed var(--b3-card-b) !important; border-radius: 6px !important;
  padding: 10px !important; background: var(--b3-sky) !important;
}}
[data-testid="stFileUploader"] section:hover {{
  border-color: var(--b3-action) !important;
}}
</style>"""


# ---------- LOGO SVG (white on dark header) ----------
_LOGO_SVG = """<svg width="36" height="36" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
  <text x="2" y="30" font-family="Barlow,sans-serif" font-size="32" font-weight="700" fill="#FFFFFF">[</text>
  <text x="11" y="28" font-family="Barlow,sans-serif" font-size="18" font-weight="700" fill="#FFFFFF">PD</text>
  <text x="28" y="30" font-family="Barlow,sans-serif" font-size="32" font-weight="700" fill="#FFFFFF">]</text>
  <text x="33" y="14" font-family="Barlow,sans-serif" font-size="10" font-weight="600" fill="rgba(255,255,255,0.7)">3</text>
</svg>"""


# ---------- INLINE ICONS (16px) ----------
_ICON_PPTX = f'<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="1" width="12" height="14" rx="1.5" stroke="{_P["action"]}" stroke-width="1.2"/><rect x="4" y="5" width="8" height="4" rx="0.5" stroke="{_P["action"]}" stroke-width="0.8"/><line x1="4" y1="11" x2="10" y2="11" stroke="{_P["action"]}" stroke-width="0.8"/></svg>'

_ICON_XLSX = f'<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="1" width="12" height="14" rx="1.5" stroke="{_P["action"]}" stroke-width="1.2"/><line x1="2" y1="5" x2="14" y2="5" stroke="{_P["action"]}" stroke-width="0.8"/><line x1="2" y1="8" x2="14" y2="8" stroke="{_P["action"]}" stroke-width="0.8"/><line x1="2" y1="11" x2="14" y2="11" stroke="{_P["action"]}" stroke-width="0.8"/><line x1="6" y1="5" x2="6" y2="15" stroke="{_P["action"]}" stroke-width="0.8"/><line x1="10" y1="5" x2="10" y2="15" stroke="{_P["action"]}" stroke-width="0.8"/></svg>'


# ---------- AGENT SVGs (48x48, color via currentColor, check overlay #0a0349) ----------
def _svg_agent_excel() -> str:
    return """<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <g class="agent-body">
    <line x1="24" y1="2" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="24" cy="2" r="2" fill="currentColor" opacity="0.5"/>
    <rect x="14" y="8" width="20" height="14" rx="4" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <g class="agent-eyes">
      <rect x="18" y="13" width="3" height="4" rx="1" fill="currentColor"/>
      <rect x="27" y="13" width="3" height="4" rx="1" fill="currentColor"/>
    </g>
    <rect x="16" y="24" width="16" height="10" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <line x1="16" y1="28" x2="8" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="32" y1="28" x2="40" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <g class="agent-action-sheet">
      <rect x="7" y="22" width="10" height="8" rx="1" fill="none" stroke="currentColor" stroke-width="1"/>
      <line x1="9" y1="24.5" x2="15" y2="24.5" stroke="currentColor" stroke-width="0.6"/>
      <line x1="9" y1="26.5" x2="15" y2="26.5" stroke="currentColor" stroke-width="0.6"/>
      <line x1="9" y1="28.5" x2="13" y2="28.5" stroke="currentColor" stroke-width="0.6"/>
    </g>
    <line x1="20" y1="34" x2="20" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="28" y1="34" x2="28" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="18" y1="40" x2="22" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="26" y1="40" x2="30" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </g>
  <g class="agent-check">
    <circle cx="39" cy="7" r="6" fill="#0a0349"/>
    <polyline points="36,7 38.5,9.5 42,5" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>"""


def _svg_agent_pattern() -> str:
    return """<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <g class="agent-body">
    <line x1="24" y1="2" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="24" cy="2" r="2" fill="currentColor" opacity="0.5"/>
    <rect x="14" y="8" width="20" height="14" rx="4" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <g class="agent-eyes">
      <rect x="18" y="13" width="3" height="4" rx="1" fill="currentColor"/>
      <rect x="27" y="13" width="3" height="4" rx="1" fill="currentColor"/>
    </g>
    <rect x="16" y="24" width="16" height="10" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <line x1="16" y1="28" x2="10" y2="34" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="32" y1="26" x2="36" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <g class="agent-action-lupa">
      <circle cx="38" cy="14" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/>
      <line x1="35" y1="18" x2="33" y2="20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <path d="M36,11 Q37,10 39,11" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.5"/>
    </g>
    <line x1="20" y1="34" x2="20" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="28" y1="34" x2="28" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="18" y1="40" x2="22" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="26" y1="40" x2="30" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </g>
  <g class="agent-check">
    <circle cx="39" cy="7" r="6" fill="#0a0349"/>
    <polyline points="36,7 38.5,9.5 42,5" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>"""


def _svg_agent_mapper() -> str:
    return """<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <g class="agent-body">
    <line x1="24" y1="2" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="24" cy="2" r="2" fill="currentColor" opacity="0.5"/>
    <rect x="14" y="8" width="20" height="14" rx="4" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <g class="agent-eyes">
      <rect x="18" y="13" width="3" height="4" rx="1" fill="currentColor"/>
      <rect x="27" y="13" width="3" height="4" rx="1" fill="currentColor"/>
    </g>
    <rect x="16" y="24" width="16" height="10" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <g class="agent-action-setas">
      <line x1="16" y1="27" x2="6" y2="27" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <polyline points="9,24.5 6,27 9,29.5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="32" y1="27" x2="42" y2="27" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <polyline points="39,24.5 42,27 39,29.5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    <line x1="20" y1="34" x2="20" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="28" y1="34" x2="28" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="18" y1="40" x2="22" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="26" y1="40" x2="30" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </g>
  <g class="agent-check">
    <circle cx="39" cy="7" r="6" fill="#0a0349"/>
    <polyline points="36,7 38.5,9.5 42,5" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>"""


def _svg_agent_executor() -> str:
    return """<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <g class="agent-body">
    <line x1="24" y1="2" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="24" cy="2" r="2" fill="currentColor" opacity="0.5"/>
    <rect x="14" y="8" width="20" height="14" rx="4" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <g class="agent-eyes">
      <rect x="18" y="13" width="3" height="4" rx="1" fill="currentColor"/>
      <rect x="27" y="13" width="3" height="4" rx="1" fill="currentColor"/>
    </g>
    <rect x="16" y="24" width="16" height="10" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <line x1="16" y1="28" x2="10" y2="34" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="32" y1="26" x2="38" y2="28" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <g class="agent-action-caneta">
      <line x1="38" y1="28" x2="44" y2="36" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <polygon points="44,36 42.5,37.5 45.5,37.5" fill="currentColor"/>
      <circle cx="42" cy="39" r="0.8" fill="currentColor" opacity="0.4"/>
      <circle cx="40" cy="40" r="0.6" fill="currentColor" opacity="0.3"/>
    </g>
    <line x1="20" y1="34" x2="20" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="28" y1="34" x2="28" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="18" y1="40" x2="22" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="26" y1="40" x2="30" y2="40" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </g>
  <g class="agent-check">
    <circle cx="39" cy="7" r="6" fill="#0a0349"/>
    <polyline points="36,7 38.5,9.5 42,5" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>"""


_AGENT_SVGS = {
    "excel":    _svg_agent_excel,
    "pattern":  _svg_agent_pattern,
    "mapper":   _svg_agent_mapper,
    "executor": _svg_agent_executor,
}

_AGENT_LABELS = {
    "excel":    "Extrator",
    "pattern":  "Analista",
    "mapper":   "Mapeador",
    "executor": "Executor",
}

_AGENT_DESCS = {
    "excel":    "Extração de dados financeiros",
    "pattern":  "Análise de padrões do PPTX",
    "mapper":   "Mapeamento dados → slides",
    "executor": "Execução das edições",
}

_AGENT_BUBBLES = {
    "excel":    "Lendo planilhas e extraindo indicadores",
    "pattern":  "Varrendo slides e identificando padrões",
    "mapper":   "Cruzando dados com placeholders do deck",
    "executor": "Escrevendo edições no PPTX",
}


# ---------- LOG SANITIZER ----------
def sanitizar_log(texto: str) -> str:
    """Remove markdown artifacts (bold, backticks) from log text."""
    texto = re.sub(r'\*\*|\*', '', texto)
    texto = re.sub(r'`([^`]*)`', r'\1', texto)
    return texto.strip()


# ---------- PUBLIC RENDER FUNCTIONS ----------

def render_header(ambiente: str = "DEV") -> str:
    """Header fixo #0a0349 com logo branco."""
    return (
        f'<div class="df-header">'
        f'  <div class="df-header-left">'
    f'    {_LOGO_SVG}'
    f'    <div class="df-header-brand">'
    f'      <div class="df-header-name">PowerDeck</div>'
        f'      <div class="df-header-sub">Financial Close Edition</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="df-header-right">'
        f'    <span class="df-header-tag">{ambiente}</span>'
        f'  </div>'
        f'</div>'
    )


def render_section_label(text: str) -> str:
    """Inter 500 9px uppercase label."""
    return f'<div class="df-section-label">{text}</div>'


def render_input_card(
    icon_svg: str,
    title: str,
    description: str,
    loaded: bool = False,
    file_info: str = "",
    file_meta: str = "",
) -> str:
    """Card wrapper for upload inputs."""
    cls = "df-input-card loaded" if loaded else "df-input-card"
    file_html = ""
    if loaded and file_info:
        file_html = f'<div class="df-file-ok">{file_info}</div>'
        if file_meta:
            file_html += f'<div class="df-file-meta">{file_meta}</div>'
    return (
        f'<div class="{cls}">'
        f'  <div class="df-input-card-header">'
        f'    <span class="df-input-card-icon">{icon_svg}</span>'
        f'    <span class="df-input-card-title">{title}</span>'
        f'  </div>'
        f'  <div class="df-input-card-desc">{description}</div>'
        f'  {file_html}'
        f'</div>'
    )


def render_input_card_pptx(loaded: bool = False, filename: str = "", meta: str = "") -> str:
    fi = f"✓  {filename}" if loaded else ""
    return render_input_card(_ICON_PPTX, "Apresentação base", "Fechamento do mês anterior · .pptx", loaded, fi, meta)


def render_input_card_excel(loaded: bool = False, files_info: str = "") -> str:
    return render_input_card(_ICON_XLSX, "Dados financeiros", "Indicadores do mês atual · .xlsx", loaded, files_info)


def render_file_ok(text: str) -> str:
    """Inline file confirmation (legacy compat)."""
    return f'<div class="df-file-ok">{text}</div>'


def _agent_color(state: str) -> str:
    return {
        "waiting": "rgba(10,3,73,0.25)",
        "processing": _P["action"],
        "done": _P["green"],
    }.get(state, "rgba(10,3,73,0.25)")


def render_agente_vertical(name: str, state: str, elapsed: str = "", is_last: bool = False, compact: bool = False) -> str:
    """Single agent row in vertical pipeline layout."""
    svg_fn = _AGENT_SVGS.get(name)
    if not svg_fn:
        return ""
    color = _agent_color(state)
    svg_html = svg_fn()
    label = _AGENT_LABELS.get(name, name)
    desc = _AGENT_DESCS.get(name, "")
    bubble_text = _AGENT_BUBBLES.get(name, "")

    if state == "waiting":
        status = "Em espera"
    elif state == "processing":
        status = f"Executando · {elapsed}" if elapsed else "Executando..."
    else:
        status = f"OK · {elapsed}" if elapsed else "Concluído ✓"

    dot = f'<div class="df-agent-dot {state}"></div>'

    line_cls = "done" if state == "done" else ("active" if state == "processing" else "waiting")
    line = f'<div class="df-agent-line {line_cls}"></div>' if not is_last else ""

    row_cls = "df-agent-row compact" if compact else "df-agent-row"
    if state == "processing" and not compact:
        row_cls += " active-row"

    if compact:
        return (
            f'<div class="{row_cls}">'
            f'  <div class="df-agent-track">{dot}{line}</div>'
            f'  <div class="df-agent-info">'
            f'    <div class="df-agent-name done" style="font-size:11px;">{label} — {status}</div>'
            f'  </div>'
            f'</div>'
        )

    # Activity bubble for processing agents
    bubble_html = ""
    if state == "processing" and bubble_text:
        bubble_html = (
            f'<div class="df-agent-bubble">'
            f'{bubble_text}<span class="cursor-blink"></span>'
            f'</div>'
        )

    return (
        f'<div class="{row_cls}">'
        f'  <div class="df-agent-track">{dot}{line}</div>'
        f'  <div class="df-agent-svg {state}" style="color:{color}">{svg_html}</div>'
        f'  <div class="df-agent-info">'
        f'    <div class="df-agent-name {state}">{label}</div>'
        f'    <div class="df-agent-status">{desc} · {status}</div>'
        f'    {bubble_html}'
        f'  </div>'
        f'</div>'
    )


def render_pipeline(states: dict, elapsed: dict = None, compact: bool = False) -> str:
    """Full vertical pipeline with 4 agents."""
    order = ["pattern", "excel", "mapper", "executor"]
    elapsed = elapsed or {}
    parts = []
    n_done = sum(1 for k in order if states.get(k) == "done")
    n_proc = sum(1 for k in order if states.get(k) == "processing")
    for i, key in enumerate(order):
        st = states.get(key, "waiting")
        el = elapsed.get(key, "")
        is_last = (i == len(order) - 1)
        parts.append(render_agente_vertical(key, st, el, is_last, compact))
    inner = "\n".join(parts)

    # Status summary
    if n_proc > 0:
        summary = f'<span style="color:var(--b3-coral);font-weight:600;">{n_done}/4 concluídos</span>'
    elif n_done == 4:
        summary = '<span style="color:var(--b3-green);font-weight:600;">Pipeline concluído ✓</span>'
    else:
        summary = '<span style="opacity:0.4;">Aguardando início</span>'

    title = (
        f'<div class="df-pipeline-title">'
        f'AGENTES DE FECHAMENTO'
        f'<span style="margin-left:auto;font-family:var(--font-body);font-size:10px;'
        f'font-weight:400;letter-spacing:0.02em;text-transform:none;">{summary}</span>'
        f'</div>'
    )
    return f'<div class="df-pipeline-card">{title}<div class="df-pipeline-agents">{inner}</div></div>'


def render_resultado(
    sucesso: bool,
    total_ok: int,
    total_err: int,
    elapsed: str,
    n_slides: int = 0,
    n_llm: int = 0,
    n_auto: int = 0,
    filename: str = "",
) -> str:
    """Result card: dark background, coral left border, white typography."""
    icon = "✓" if sucesso else "✗"
    status = f"{icon}  Concluído em {elapsed} · {total_err} erros"

    metrics_html = ""
    if n_slides or n_llm or n_auto:
        metrics_html = (
            f'<hr class="df-result-sep"/>'
            f'<div class="df-result-metrics">'
            f'  <div><div class="df-result-metric-val">{n_slides}</div><div class="df-result-metric-lbl">Slides</div></div>'
            f'  <div><div class="df-result-metric-val">{n_llm}</div><div class="df-result-metric-lbl">LLM</div></div>'
            f'  <div><div class="df-result-metric-val">{n_auto}</div><div class="df-result-metric-lbl">Auto</div></div>'
            f'</div>'
        )

    return (
        f'<div class="df-result-card">'
        f'  <div class="df-result-big">{total_ok}</div>'
        f'  <div class="df-result-label">edições aplicadas</div>'
        f'  <div class="df-result-status">{status}</div>'
        f'  {metrics_html}'
        f'</div>'
    )


def render_avisos_manuais(avisos: list) -> str:
    """Manual-action warnings (chart period labels — avisos manuais)."""
    if not avisos:
        return ""
    items = ""
    for av in avisos:
        periodos = ", ".join(av.get("periodos", []))
        items += (
            f'<div class="df-aviso-item">'
            f'  <strong>Slide {av["slide"]}</strong> — '
            f'  Gráfico <em>"{av.get("shape_nome", "?")}"</em>: '
            f'  labels <strong>{periodos}</strong> → atualize via '
            f'  <strong>Editar Dados</strong> no PowerPoint.'
            f'</div>'
        )
    return (
        f'<div class="df-aviso-card">'
        f'  <div class="df-aviso-title">⚠️ Atualização manual necessária</div>'
        f'  {items}'
        f'</div>'
    )


def render_log(entries: list) -> str:
    """Log area: dark terminal, monospace, with line numbers and timestamps."""
    items = "\n".join(
        f'<div class="df-log-entry">'
        f'<span style="color:rgba(24,24,183,0.5);margin-right:8px;">{str(i+1).zfill(3)}</span>'
        f'<span style="color:rgba(245,186,148,0.6);margin-right:8px;">▸</span>'
        f'{sanitizar_log(e)}</div>'
        for i, e in enumerate(entries)
    )
    return f'<div class="df-log-container">{items}</div>'


def render_separator() -> str:
    return '<hr class="df-sep"/>'


# Legacy compat aliases
def render_etapa(numero: str, titulo: str, subtitulo: str) -> str:
    """Step header - kept for backward compatibility."""
    return (
        f'<div style="display:flex;align-items:flex-start;gap:20px;margin-bottom:6px;padding:0 4px;">'
        f'  <div style="font-family:var(--font-display);font-size:48px;font-weight:200;'
        f'color:{_P["card_b"]};line-height:1;min-width:64px;user-select:none;">{numero}</div>'
        f'  <div style="display:flex;flex-direction:column;gap:2px;padding-top:6px;">'
        f'    <div style="font-family:var(--font-display);font-size:18px;font-weight:600;'
        f'color:{_P["deep"]};line-height:1.2;">{titulo}</div>'
        f'    <div style="font-family:var(--font-body);font-size:13px;font-weight:400;'
        f'color:{_P["body"]};opacity:0.6;">{subtitulo}</div>'
        f'  </div>'
        f'</div>'
    )


# Legacy render functions (kept for backward compat with interface_web_do_fechamento.py)
def render_agente(name: str, state: str) -> str:
    """Return SVG+wrapper for a single agent icon (horizontal layout)."""
    svg_fn = _AGENT_SVGS.get(name)
    if not svg_fn:
        return ""
    color = _agent_color(state)
    svg_html = svg_fn()
    label = _AGENT_LABELS.get(name, name)
    return (
        f'<div class="df-agent-node" style="display:flex;flex-direction:column;align-items:center;gap:6px;min-width:90px;">'
        f'  <div class="df-agent-svg {state}" style="color:{color};width:36px;height:36px;">{svg_html}</div>'
        f'  <div class="df-agent-name {state}" style="font-family:var(--font-body);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.10em;">{label}</div>'
        f'</div>'
    )


def render_connector(filled: bool) -> str:
    """Return HTML for a horizontal connector line between agents."""
    bg = _P["deep"] if filled else _P["card_b"]
    return f'<div style="width:56px;height:2px;background:{bg};border-radius:1px;align-self:center;margin:0 2px;flex-shrink:0;margin-bottom:20px;transition:background 0.4s;"></div>'