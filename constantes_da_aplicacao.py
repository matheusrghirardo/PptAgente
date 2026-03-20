"""
constantes_da_aplicacao.py — Constantes, CSS, conjuntos de ações e palavras-chave.
Extraído de appvf.py para modularização da arquitetura.
"""

# ─────────────────────────────────────────────────
# CSS — Professional AI Tool Interface
# B3-inspired design system
# ─────────────────────────────────────────────────
CSS_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

/* ═══════════════════════════════════════════════════
   DESIGN TOKENS — B3 Financial Agent
   Deep navy + gold accent • Bloomberg-terminal feel
   ═══════════════════════════════════════════════════ */
:root{
  /* B3 core palette */
  --b3-navy:#0a0f1e;
  --b3-navy-mid:#0f1629;
  --b3-navy-light:#151d35;
  --b3-card:#1a2340;
  --b3-input:#111833;
  --b3-gold:#E2A440;
  --b3-gold-hover:#F0B450;
  --b3-gold-subtle:rgba(226,164,64,.10);
  --b3-gold-glow:rgba(226,164,64,.18);
  --b3-blue:#3B82F6;
  --b3-blue-subtle:rgba(59,130,246,.10);

  /* Semantic aliases */
  --bg:#ffffff;
  --bg-alt:#f4f7fb;
  --surface:#eef2f8;
  --surface-raised:#e4ecf6;
  --dark:#1a2340;
  --accent:#E2A440;
  --accent-hover:#F0B450;
  --accent-light:rgba(226,164,64,.14);
  --accent-glow:rgba(226,164,64,.22);
  --border:#d0d9e8;
  --border-light:#bfcde0;
  --text:#1a2340;
  --text-secondary:#4a5d7e;
  --muted:#7a90b0;
  --success:#22c55e;
  --success-bg:rgba(34,197,94,.10);
  --warn:#f59e0b;
  --warn-bg:rgba(245,158,11,.10);
  --error:#ef4444;
  --error-bg:rgba(239,68,68,.10);
  --radius:8px;
  --radius-lg:10px;
  --shadow-sm:0 1px 3px rgba(0,0,0,.08);
  --shadow-md:0 4px 12px rgba(0,0,0,.10);
  --shadow-lg:0 8px 24px rgba(0,0,0,.14);
  --font-sans:'Inter',system-ui,sans-serif;
  --font-mono:'JetBrains Mono',monospace;
  --transition:all .15s ease;
  --accent-blue:#3B82F6;
}

/* ═══════════════════════════════════════════════════
   BASE & RESETS
   ═══════════════════════════════════════════════════ */
.stApp{background:var(--bg)!important;font-family:var(--font-sans)!important;color:var(--text)!important;}
h1,h2,h3,h4{color:var(--text)!important;font-family:var(--font-sans)!important;}
[data-testid="collapsedControl"]{display:none;}
[data-testid="stSidebar"]{display:none;}
[data-testid="stHeader"]{display:none!important;}
[data-testid="stDecoration"]{background-image:none!important;background:var(--bg)!important;}
footer{visibility:hidden;}
/* Kill ALL outlines/focus rings globally */
*:focus,*:focus-within,*:focus-visible{
  outline:none!important;outline-width:0!important;outline-style:none!important;
  outline-color:transparent!important;
  box-shadow:none!important;
}
.block-container{
  padding-top:0.75rem!important;
  padding-bottom:0.75rem!important;
  padding-left:1.5rem!important;
  padding-right:1.5rem!important;
  max-width:100%!important;
}

::selection{background:rgba(226,164,64,.35);color:#fff;}

/* ═══════════════════════════════════════════════════
   TOP BAR — B3 Financial Terminal Header
   ═══════════════════════════════════════════════════ */
.top-bar{
  background:linear-gradient(135deg,#0d1424 0%,#162042 50%,#0d1424 100%);
  padding:14px 24px;border-radius:var(--radius-lg);margin-bottom:20px;
  display:flex;align-items:center;justify-content:space-between;
  border:1px solid var(--border-light);position:relative;overflow:visible;
  box-shadow:var(--shadow-md);
}
.top-bar::before{
  content:'';position:absolute;top:-50%;right:-5%;width:280px;height:280px;
  background:radial-gradient(circle,rgba(226,164,64,.06) 0%,transparent 70%);
  pointer-events:none;
}
.top-bar-left{display:flex;align-items:center;gap:14px;z-index:1;}
.top-bar-logo{font-size:28px;filter:drop-shadow(0 2px 8px rgba(226,164,64,.25));}
.top-bar-title{
  font-size:20px;font-weight:700;color:#fff;letter-spacing:-.02em;
}
.top-bar-sub{font-size:11px;color:var(--text-secondary);font-weight:500;margin-top:1px;}

/* ═══ CSS Robot Agents ═══ */
.top-bar-agents{display:flex;align-items:center;gap:10px;z-index:5;margin-left:auto;}

/* Base bot container */
.bot{
  display:flex;flex-direction:column;align-items:center;
  cursor:default;position:relative;
  animation:bot-idle 3s ease-in-out infinite;
  transition:all .3s ease;
}

/* Antenna */
.bot-antenna{
  width:2px;height:8px;background:rgba(255,255,255,.25);
  position:relative;margin-bottom:1px;
  animation:antenna-sway 2.5s ease-in-out infinite;
  transform-origin:bottom center;
}
.bot-antenna-tip{
  width:5px;height:5px;border-radius:50%;
  background:rgba(255,255,255,.35);
  position:absolute;top:-3px;left:-1.5px;
  transition:all .3s ease;
}

/* Head */
.bot-head{
  width:28px;height:22px;border-radius:6px 6px 4px 4px;
  background:rgba(255,255,255,.12);border:1.5px solid rgba(255,255,255,.18);
  position:relative;display:flex;align-items:center;justify-content:center;
  gap:6px;transition:all .3s ease;
}

/* Eyes */
.bot-eye{
  width:5px;height:6px;border-radius:2px;
  background:#fff;opacity:.7;
  animation:bot-blink 4s ease-in-out infinite;
  transition:all .3s ease;
}
.bot-eye-l{animation-delay:0s;}
.bot-eye-r{animation-delay:.1s;}

/* Mouth */
.bot-mouth{
  position:absolute;bottom:3px;left:50%;transform:translateX(-50%);
  width:8px;height:2px;border-radius:0 0 3px 3px;
  background:rgba(255,255,255,.25);
  transition:all .3s ease;
}

/* Body */
.bot-body{
  width:22px;height:10px;border-radius:2px 2px 5px 5px;
  background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);
  margin-top:1px;position:relative;transition:all .3s ease;
}
.bot-body::before,.bot-body::after{
  content:'';position:absolute;top:2px;
  width:3px;height:6px;border-radius:2px;
  background:rgba(255,255,255,.10);
}
.bot-body::before{left:-4px;}
.bot-body::after{right:-4px;}

/* Name label */
.bot-name{
  font-size:7px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:rgba(255,255,255,.30);font-family:var(--font-sans);
  margin-top:3px;transition:all .3s ease;
}

/* ─── Idle animations ─── */
@keyframes bot-idle{
  0%,100%{transform:translateY(0);}
  50%{transform:translateY(-2px);}
}
@keyframes bot-blink{
  0%,42%,46%,100%{transform:scaleY(1);}
  44%{transform:scaleY(.1);}
}
@keyframes antenna-sway{
  0%,100%{transform:rotate(0deg);}
  25%{transform:rotate(6deg);}
  75%{transform:rotate(-6deg);}
}

/* ─── Per-robot color themes ─── */
/* Conductor — gold */
.bot-orch .bot-head{border-color:rgba(226,164,64,.35);background:rgba(226,164,64,.12);}
.bot-orch .bot-eye{background:#E2A440;}
.bot-orch .bot-antenna-tip{background:#E2A440;}
.bot-orch .bot-mouth{background:rgba(226,164,64,.35);}
.bot-orch .bot-body{border-color:rgba(226,164,64,.25);background:rgba(226,164,64,.08);}

/* Analyst — blue */
.bot-interp .bot-head{border-color:rgba(59,130,246,.35);background:rgba(59,130,246,.12);}
.bot-interp .bot-eye{background:#60a5fa;}
.bot-interp .bot-antenna-tip{background:#60a5fa;}
.bot-interp .bot-mouth{background:rgba(59,130,246,.35);}
.bot-interp .bot-body{border-color:rgba(59,130,246,.25);background:rgba(59,130,246,.08);}

/* Locator — purple */
.bot-nav .bot-head{border-color:rgba(139,92,246,.35);background:rgba(139,92,246,.12);}
.bot-nav .bot-eye{background:#a78bfa;}
.bot-nav .bot-antenna-tip{background:#a78bfa;}
.bot-nav .bot-mouth{background:rgba(139,92,246,.35);}
.bot-nav .bot-body{border-color:rgba(139,92,246,.25);background:rgba(139,92,246,.08);}

/* Forge — green */
.bot-edit .bot-head{border-color:rgba(34,197,94,.35);background:rgba(34,197,94,.12);}
.bot-edit .bot-eye{background:#4ade80;}
.bot-edit .bot-antenna-tip{background:#4ade80;}
.bot-edit .bot-mouth{background:rgba(34,197,94,.35);}
.bot-edit .bot-body{border-color:rgba(34,197,94,.25);background:rgba(34,197,94,.08);}

/* Auditor — pink */
.bot-audit .bot-head{border-color:rgba(236,72,153,.35);background:rgba(236,72,153,.12);}
.bot-audit .bot-eye{background:#f472b6;}
.bot-audit .bot-antenna-tip{background:#f472b6;}
.bot-audit .bot-mouth{background:rgba(236,72,153,.35);}
.bot-audit .bot-body{border-color:rgba(236,72,153,.25);background:rgba(236,72,153,.08);}

/* ─── Hover — light up ─── */
.bot:hover .bot-eye{opacity:1;filter:brightness(1.3);}
.bot:hover .bot-antenna-tip{box-shadow:0 0 6px currentColor;}
.bot:hover .bot-name{color:rgba(255,255,255,.6);}
.bot:hover .bot-head{border-color:rgba(255,255,255,.3);}

/* ─── Active state — working ─── */
.bot.bot-active{
  animation:bot-idle 1.5s ease-in-out infinite;
}
.bot.bot-active .bot-antenna-tip{
  animation:tip-pulse 0.8s ease-in-out infinite;
}
.bot.bot-active .bot-eye{
  opacity:1;animation:eye-scan 1.2s ease-in-out infinite;
}
.bot.bot-active .bot-mouth{
  animation:mouth-talk .4s steps(2) infinite;
}
.bot.bot-active .bot-head{
  box-shadow:0 0 10px rgba(226,164,64,.25);
}
.bot.bot-active .bot-name{
  color:var(--accent);
}
@keyframes tip-pulse{
  0%,100%{opacity:1;transform:scale(1);}
  50%{opacity:.5;transform:scale(1.4);}
}
@keyframes eye-scan{
  0%,100%{transform:scaleY(1) translateX(0);}
  25%{transform:scaleY(1) translateX(-1px);}
  75%{transform:scaleY(1) translateX(1px);}
}
@keyframes mouth-talk{
  0%,100%{height:2px;}
  50%{height:4px;border-radius:0 0 4px 4px;}
}

/* ─── Inline mini-bot for panels/timeline/pills ─── */
.bot-inline{
  display:inline-flex;align-items:center;justify-content:center;
  vertical-align:middle;position:relative;
}
.bot-inline .bi-head{
  display:inline-flex;align-items:center;justify-content:center;gap:3px;
  border-radius:4px 4px 3px 3px;position:relative;
  border-width:1.5px;border-style:solid;
}
.bot-inline .bi-eye{
  border-radius:1.5px;
  animation:bot-blink 4s ease-in-out infinite;
}
/* Size: sm (default for pills/timeline) */
.bot-inline-sm .bi-head{
  width:18px;height:14px;gap:3px;border-radius:4px 4px 3px 3px;
}
.bot-inline-sm .bi-eye{width:3px;height:4px;}
/* Size: md (for workflow nodes) */
.bot-inline-md .bi-head{
  width:24px;height:18px;gap:4px;border-radius:5px 5px 3px 3px;
}
.bot-inline-md .bi-eye{width:4px;height:5px;}
/* Size: lg (for headers) */
.bot-inline-lg .bi-head{
  width:32px;height:24px;gap:5px;border-radius:6px 6px 4px 4px;
}
.bot-inline-lg .bi-eye{width:5px;height:6px;}

/* Inline bot colors (reusing agent themes) */
.bot-inline.bot-orch .bi-head{border-color:rgba(226,164,64,.5);background:rgba(226,164,64,.15);}
.bot-inline.bot-orch .bi-eye{background:#E2A440;}
.bot-inline.bot-interp .bi-head{border-color:rgba(59,130,246,.5);background:rgba(59,130,246,.15);}
.bot-inline.bot-interp .bi-eye{background:#60a5fa;}
.bot-inline.bot-nav .bi-head{border-color:rgba(139,92,246,.5);background:rgba(139,92,246,.15);}
.bot-inline.bot-nav .bi-eye{background:#a78bfa;}
.bot-inline.bot-edit .bi-head{border-color:rgba(34,197,94,.5);background:rgba(34,197,94,.15);}
.bot-inline.bot-edit .bi-eye{background:#4ade80;}
.bot-inline.bot-audit .bi-head{border-color:rgba(236,72,153,.5);background:rgba(236,72,153,.15);}
.bot-inline.bot-audit .bi-eye{background:#f472b6;}

/* ═══════════════════════════════════════════════════
   PIPELINE STEPPER — Workflow Indicator
   ═══════════════════════════════════════════════════ */
.pipeline{
  display:flex;align-items:center;justify-content:space-evenly;gap:0;
  padding:14px 28px;
  background:linear-gradient(135deg,#f8faff 0%,#eef2f8 100%);
  border:1px solid var(--border);
  border-top:3px solid var(--b3-card);
  border-radius:var(--radius-lg);
  margin-bottom:18px;
  box-shadow:var(--shadow-md);
  position:relative;
  overflow:hidden;
  transition:transform .4s cubic-bezier(.34,1.56,.64,1),
             box-shadow .4s ease,
             border-color .4s ease,
             padding .4s ease;
  transform-origin:center center;
}
/* Running state — enlarges the pipeline for emphasis */
.pipeline.pipeline-running{
  transform:scale(1.035);
  padding:18px 32px;
  box-shadow:0 6px 24px rgba(226,164,64,.18), var(--shadow-md);
  border-color:var(--accent);
  border-top-width:3px;
}
.pipeline::after{
  content:'';
  position:absolute;top:50%;left:10%;right:10%;
  height:1px;background:var(--border);z-index:0;
  transform:translateY(6px);
}
.pipe-step{
  display:flex;flex-direction:column;align-items:center;gap:5px;
  padding:4px 16px;border-radius:8px;
  font-size:10px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
  color:var(--accent-blue);transition:var(--transition);
  position:relative;z-index:1;
  flex:1;min-width:0;
}
.pipe-icon-wrap{
  width:36px;height:36px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  background:var(--b3-blue-subtle);border:2px solid var(--accent-blue);
  font-size:16px;transition:var(--transition);
  box-shadow:0 0 0 0 transparent;
}
.pipe-step.done .pipe-icon-wrap{
  background:rgba(226,164,64,.10);border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-glow);
}
.pipe-step.done{ color:var(--accent); }
.pipe-step.active .pipe-icon-wrap{
  background:rgba(226,164,64,.10);
  border-color:transparent;
  box-shadow:none;
  animation:pipe-spin 1.1s linear infinite;
}
.pipe-step.active .pipe-icon-wrap::before{
  content:'';
  position:absolute;inset:-2px;
  border-radius:50%;
  border:2px solid transparent;
  border-top-color:var(--accent);
  border-right-color:rgba(226,164,64,.35);
  animation:pipe-spin 1.1s linear infinite;
}
.pipe-icon-wrap{position:relative;}
.pipe-step.active{ color:var(--accent); }
@keyframes pipe-spin{
  0%{transform:rotate(0deg);}
  100%{transform:rotate(360deg);}
}
.pipe-arrow{color:var(--accent-blue);opacity:.35;font-size:20px;margin:0 2px;user-select:none;
  position:relative;z-index:1;flex-shrink:0;line-height:1;padding-bottom:20px;}

[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stFileUploader"] label{
  font-size:11px!important;font-weight:700!important;color:var(--muted)!important;
  letter-spacing:.04em!important;text-transform:uppercase!important;
  font-family:var(--font-sans)!important;
}
[data-testid="stTextInput"] input{
  background:#ffffff!important;border:1px solid var(--border)!important;
  border-radius:6px!important;padding:8px 12px!important;font-size:13px!important;
  color:var(--text)!important;box-shadow:none!important;font-family:var(--font-sans)!important;
  transition:var(--transition)!important;
}
[data-testid="stTextInput"] input::placeholder{color:var(--muted)!important;font-size:12px!important;}
[data-testid="stTextInput"] input:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 2px var(--accent-glow)!important;
}
[data-testid="stSelectbox"] [data-baseweb="select"]>div{
  background:#ffffff!important;border:1px solid var(--border)!important;
  border-radius:6px!important;min-height:42px!important;box-shadow:none!important;
  color:var(--text)!important;
}
/* valor selecionado */
[data-testid="stSelectbox"] [data-baseweb="select"] div[value] {
  color:var(--text)!important;
  -webkit-text-fill-color:var(--text)!important;
  font-size:13px!important;
}
/* placeholder (nenhum item selecionado) — múltiplos seletores possíveis do BaseWeb */
[data-testid="stSelectbox"] [data-baseweb="select"] [data-baseweb="placeholder"],
[data-testid="stSelectbox"] [data-baseweb="select"] [class*="placeholder" i],
[data-testid="stSelectbox"] [data-baseweb="select"] div[value=""],
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div:first-child:not([value]) {
  color:#7a90b0!important;
  -webkit-text-fill-color:#7a90b0!important;
  font-size:12px!important;
  opacity:1!important;
  font-family:var(--font-sans)!important;
  font-weight:400!important;
}
[data-testid="stTextInput"],
[data-testid="stSelectbox"],
[data-testid="stFileUploader"]{
  margin-bottom:0!important;
}

/* ═══════════════════════════════════════════════════
   FILE UPLOAD CARD
   ═══════════════════════════════════════════════════ */
.upload-card{
  background:var(--bg-alt);border:2px dashed var(--border-light);border-radius:var(--radius);
  padding:20px;text-align:center;margin-bottom:16px;transition:var(--transition);
}
.upload-card:hover{border-color:var(--accent);background:var(--accent-light);}
.upload-card-title{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:.06em;margin-bottom:6px;}

[data-testid="stFileUploader"] section{
  background:#f0f4f8!important;border:2px dashed var(--border-light)!important;
  border-radius:8px!important;padding:14px!important;transition:var(--transition)!important;
  min-height:88px!important;display:flex!important;align-items:center!important;justify-content:space-between!important;gap:12px!important;
}
[data-testid="stFileUploader"] section:hover{
  border-color:var(--accent)!important;background:var(--accent-light)!important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"]{
  display:flex!important;align-items:center!important;gap:12px!important;text-align:left!important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] > div{
  display:flex!important;flex-direction:column!important;gap:2px!important;
}
[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"]{
  white-space:nowrap!important;min-width:fit-content!important;
  background:#ffffff!important;
  border:1px solid var(--border)!important;
  border-radius:6px!important;
  color:var(--text)!important;
  font-size:13px!important;
  font-weight:400!important;
  font-family:var(--font-sans)!important;
  padding:7px 14px!important;
  box-shadow:none!important;
  transition:var(--transition)!important;
}
[data-testid="stFileUploader"] button[data-testid="stBaseButton-secondary"]:hover{
  border-color:var(--accent)!important;
  color:var(--accent)!important;
  background:#ffffff!important;
  box-shadow:none!important;
}
/* Tradução: "Drag and drop file here" → português */
[data-testid="stFileUploaderDropzoneInstructions"] div span{
  font-size:0!important;
}
[data-testid="stFileUploaderDropzoneInstructions"] div span::after{
  content:'Arraste e solte o arquivo aqui';
  font-size:12px!important;
  color:var(--muted)!important;
  -webkit-text-fill-color:var(--muted)!important;
  font-family:var(--font-sans)!important;
  font-weight:400!important;
}
/* Tradução: "Limit 200MB per file • PPTX" → português */
[data-testid="stFileUploaderDropzoneInstructions"] small{
  font-size:0!important;
}
[data-testid="stFileUploaderDropzoneInstructions"] small::after{
  content:'Limite 200MB por arquivo • PPTX';
  font-size:11px!important;
  color:var(--muted)!important;
  font-family:var(--font-sans)!important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"]{
  color:var(--muted)!important;
}
/* Hide uploaded file indicator — custom file-status card replaces it */
[data-testid="stFileUploaderFile"]{display:none!important;}
[data-testid="stFileUploaderFileName"]{
  font-size:12px!important;font-weight:500!important;
  color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;
  font-family:var(--font-sans)!important;
}
[data-testid="stFileUploaderFileData"] small{
  font-size:11px!important;font-weight:400!important;
  color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important;
  font-family:var(--font-sans)!important;
}

/* File status card — Executive dashboard */
.file-status{
  background:linear-gradient(135deg,#0d1424 0%,#162042 60%,#1a2a52 100%);
  border:1px solid rgba(255,255,255,.08);border-radius:var(--radius-lg);
  padding:16px 22px;margin-bottom:16px;display:flex;align-items:center;gap:16px;
  box-shadow:0 4px 16px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.04);
  position:relative;overflow:hidden;
}
.file-status::before{
  content:'';position:absolute;top:-40%;right:-3%;width:200px;height:200px;
  background:radial-gradient(circle,rgba(226,164,64,.07) 0%,transparent 70%);
  pointer-events:none;
}
.fs-left{display:flex;align-items:center;gap:14px;flex-shrink:0;z-index:1;}
.fs-badge{
  background:linear-gradient(135deg,#E2A440,#d4922e);color:#1a1200;
  font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
  padding:6px 10px;border-radius:6px;font-family:var(--font-mono);
  box-shadow:0 2px 8px rgba(226,164,64,.30);
  line-height:1;
}
.fs-info{display:flex;flex-direction:column;gap:2px;}
.fs-filename{
  font-size:13px;font-weight:600;color:#fff;letter-spacing:-.01em;
  font-family:var(--font-sans);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;max-width:320px;
}
.fs-details{
  font-size:11px;color:rgba(255,255,255,.45);font-family:var(--font-sans);
  font-weight:400;
}
.fs-stats{
  display:flex;flex-wrap:wrap;gap:6px;flex:1;justify-content:center;z-index:1;
}
.fs-pill{
  background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.10);
  border-radius:20px;padding:4px 10px;font-size:11px;font-weight:500;
  color:rgba(255,255,255,.75);font-family:var(--font-sans);
  white-space:nowrap;transition:var(--transition);display:inline-flex;
  align-items:center;gap:4px;
}
.fs-pill:hover{
  background:rgba(226,164,64,.12);border-color:rgba(226,164,64,.25);
  color:rgba(255,255,255,.9);
}
.fs-ready{
  display:flex;align-items:center;gap:6px;flex-shrink:0;z-index:1;
  font-size:11px;font-weight:600;color:var(--success);
  font-family:var(--font-sans);letter-spacing:.02em;
}
.fs-ready-dot{
  width:7px;height:7px;border-radius:50%;background:var(--success);
  box-shadow:0 0 6px rgba(34,197,94,.50);
  animation:fs-pulse 2s ease-in-out infinite;
}
@keyframes fs-pulse{
  0%,100%{opacity:1;box-shadow:0 0 6px rgba(34,197,94,.50);}
  50%{opacity:.6;box-shadow:0 0 10px rgba(34,197,94,.70);}
}

/* ═══════════════════════════════════════════════════
   BUTTONS — B3 Primary Gold
   ═══════════════════════════════════════════════════ */
.stButton>button,.stDownloadButton>button{
  background:linear-gradient(135deg,#E2A440,#d4922e)!important;color:#1a1200!important;
  border:none!important;
  border-radius:6px!important;font-weight:600!important;font-size:13px!important;
  padding:8px 16px!important;transition:var(--transition)!important;
  box-shadow:0 2px 8px rgba(226,164,64,.25)!important;font-family:var(--font-sans)!important;
}
.stButton>button:hover,.stDownloadButton>button:hover{
  background:linear-gradient(135deg,#F0B450,#E2A440)!important;transform:translateY(-1px)!important;
  box-shadow:0 4px 14px rgba(226,164,64,.35)!important;
}

/* Clear chat btn — ghost button, modern UX */
.chat-toolbar{
  display:flex;justify-content:center;
  margin:2px 0 12px;
}
.chat-toolbar .st-key-btn_limpar_chat button{
  all:unset!important;
  display:inline-flex!important;
  align-items:center!important;
  justify-content:center!important;
  gap:5px!important;
  cursor:pointer!important;
  background:transparent!important;
  color:var(--muted)!important;
  -webkit-text-fill-color:var(--muted)!important;
  border:none!important;
  border-radius:6px!important;
  font-size:11px!important;
  font-weight:500!important;
  letter-spacing:.02em!important;
  padding:5px 10px!important;
  height:auto!important;
  box-sizing:border-box!important;
  font-family:var(--font-sans)!important;
  white-space:nowrap!important;
  transition:all .15s ease!important;
}
.chat-toolbar .st-key-btn_limpar_chat button::before{
  content:'\2715'!important;
  font-size:10px!important;
  line-height:1!important;
}
.chat-toolbar .st-key-btn_limpar_chat button:hover{
  color:var(--error)!important;
  -webkit-text-fill-color:var(--error)!important;
  background:var(--error-bg)!important;
}
.chat-toolbar .st-key-btn_limpar_chat button:active{
  transform:scale(.96)!important;
}

/* ═══════════════════════════════════════════════════
   SECTION HEADERS — Clear hierarchy
   ═══════════════════════════════════════════════════ */
.section-hdr{
  display:flex;align-items:center;justify-content:center;gap:8px;
  font-size:14px;font-weight:700;color:var(--text);
  padding-bottom:10px;margin-bottom:10px;
  border-bottom:1px solid var(--border);
  font-family:var(--font-sans);
}
.section-hdr .icon{font-size:17px;}
.section-hdr .counter{
  font-size:10px;font-weight:700;background:var(--accent);color:#1a1200;
  padding:2px 7px;border-radius:10px;margin-left:auto;
}

/* ═══════════════════════════════════════════════════
   CHAT MESSAGES — Financial terminal conversation
   ═══════════════════════════════════════════════════ */
.stChatMessage{border-left:none!important;}

/* User messages */
[data-testid="stChatMessage"][data-testid-type="user"],
.stChatMessage:has([data-testid="chatAvatarIcon-user"]){
  background:linear-gradient(135deg,rgba(226,164,64,.08),rgba(226,164,64,.04))!important;
  color:var(--text)!important;border-radius:var(--radius)!important;
  border:1px solid rgba(226,164,64,.20)!important;margin-left:12%!important;padding:14px 18px!important;
  box-shadow:var(--shadow-sm)!important;
}
[data-testid="stChatMessage"][data-testid-type="user"] *,
.stChatMessage:has([data-testid="chatAvatarIcon-user"]) *{color:var(--text)!important;}

/* Assistant messages */
[data-testid="stChatMessage"][data-testid-type="assistant"],
.stChatMessage:has([data-testid="chatAvatarIcon-assistant"]){
  background:var(--surface)!important;color:var(--text)!important;
  border-radius:var(--radius)!important;
  border:1px solid var(--border)!important;margin-right:6%!important;
  padding:14px 18px!important;
  box-shadow:var(--shadow-sm)!important;
}
[data-testid="stChatMessage"][data-testid-type="assistant"] *,
.stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) *{color:var(--text)!important;}

/* Remove default Streamlit border from all block wrappers */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div > div,
.stVerticalBlock,
.stHorizontalBlock,
.stColumn > div,
[class*="e1f1d6gn"]{
  border:none!important;box-shadow:none!important;
  border-radius:0!important;background:transparent!important;
  outline:none!important;outline-width:0!important;
  border-top:none!important;border-bottom:none!important;
  border-left:none!important;border-right:none!important;
  border-image:none!important;
}
/* Chat container — restore border specifically */
[data-testid="stVerticalBlockBorderWrapper"]:has(.stChatMessage){
  background:#ffffff!important;border:1px solid var(--border)!important;
  border-radius:var(--radius)!important;
}

/* ═══════════════════════════════════════════════════
   CHAT INPUT — Financial terminal
   ═══════════════════════════════════════════════════ */
[data-testid="stChatInput"]{margin-top:10px!important;}
[data-testid="stChatInput"] textarea{
  background:#ffffff!important;border:1px solid var(--border)!important;
  border-radius:6px!important;min-height:50px!important;font-size:13px!important;
  padding:14px 12px!important;color:var(--text)!important;
  -webkit-text-fill-color:var(--text)!important;caret-color:var(--text)!important;
  font-family:var(--font-sans)!important;transition:var(--transition)!important;
}
[data-testid="stChatInput"] textarea:disabled{
  color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;opacity:1!important;
}
[data-testid="stChatInput"] textarea:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 2px var(--accent-glow)!important;
}
[data-testid="stChatInput"] textarea::placeholder{
  color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important;
  font-size:12px!important;font-weight:400!important;
  font-family:var(--font-sans)!important;
}
[data-testid="stChatInput"] textarea:disabled::placeholder{
  color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important;opacity:1!important;
}
[data-testid="stChatInput"] button{
  background:linear-gradient(135deg,#E2A440,#d4922e)!important;
  color:#1a1200!important;border-radius:6px!important;
  border:none!important;min-height:50px!important;padding:8px 16px!important;
  transition:var(--transition)!important;
}
[data-testid="stChatInput"] button:hover{
  background:linear-gradient(135deg,#F0B450,#E2A440)!important;
  box-shadow:0 2px 10px rgba(226,164,64,.3)!important;
}

/* ═══════════════════════════════════════════════════
   EXECUTION PANEL — B3 Trading Desk
   ═══════════════════════════════════════════════════ */
.exec-panel{
  background:var(--bg-alt);
  color:var(--text);padding:20px;border-radius:var(--radius-lg);
  min-height:200px;font-size:13px;line-height:1.7;
  border:1px solid var(--border);box-shadow:var(--shadow-md);
  font-family:var(--font-sans);
}

/* Counters row */
.obs-counters{
  display:flex;justify-content:space-around;padding:10px 0;margin-bottom:10px;
  background:rgba(255,255,255,.03);border-radius:8px;border:1px solid var(--border);
}
.obs-counter-item{
  display:flex;flex-direction:column;align-items:center;gap:2px;
}
.obs-counter-value{font-size:20px;font-weight:800;font-family:var(--font-mono);}
.obs-counter-label{font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);}
.obs-success .obs-counter-value{color:var(--success);}
.obs-warn .obs-counter-value{color:var(--warn);}
.obs-error .obs-counter-value{color:var(--error);}

/* Timer */
.timer{
  font-size:22px;font-weight:800;color:var(--accent);text-align:center;
  padding:8px 0;font-family:var(--font-mono);
  letter-spacing:.02em;text-shadow:0 0 12px rgba(226,164,64,.2);
}

/* Progress summary */
.progress-summary{
  text-align:center;margin:6px 0 10px;font-size:14px;color:var(--text-secondary);
}
.progress-summary strong{color:var(--text);font-size:16px;}

/* Progress bar */
.progress-track{
  background:rgba(255,255,255,.04);border-radius:6px;height:8px;
  margin:8px 0 14px;overflow:hidden;border:1px solid var(--border);
}
.progress-fill{
  height:100%;border-radius:5px;transition:width .6s cubic-bezier(.4,0,.2,1);
  background:linear-gradient(90deg,#d4922e,#E2A440,#F0B450);
}

/* Agent status block */
.agent-status-block{
  margin:10px 0;padding:12px 14px;background:rgba(255,255,255,.02);
  border-radius:8px;border:1px solid var(--border);
}
.agent-status-block .agent-status-title{
  font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
  color:var(--muted);margin-bottom:8px;
}
.agent-pill{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 10px;border-radius:6px;font-size:12px;font-weight:600;
  margin:2px 3px;
}

/* Agent-specific pill colors — B3 Financial */
.pill-orch{background:rgba(226,164,64,.12);color:#E2A440;border:1px solid rgba(226,164,64,.25);}
.pill-interp{background:rgba(59,130,246,.10);color:#3B82F6;border:1px solid rgba(59,130,246,.20);}
.pill-nav{background:rgba(245,158,11,.10);color:#f59e0b;border:1px solid rgba(245,158,11,.20);}
.pill-edit{background:rgba(34,197,94,.10);color:#22c55e;border:1px solid rgba(34,197,94,.20);}
.pill-valid{background:rgba(139,157,195,.10);color:#8b9dc3;border:1px solid rgba(139,157,195,.20);}

/* Chat-area agent log blocks — terminal cards */
.agent-log{
  padding:8px 12px;border-radius:8px;margin-bottom:6px;font-size:12px;line-height:1.5;
  border-left:3px solid;font-family:var(--font-sans);
  background:var(--surface);color:var(--text);
}
.agent-orch{border-left-color:var(--accent);}.agent-orch strong{color:var(--accent);}
.agent-interp{border-left-color:var(--accent-blue);}.agent-interp strong{color:var(--accent-blue);}
.agent-nav{border-left-color:var(--warn);}.agent-nav strong{color:var(--warn);}
.agent-edit{border-left-color:var(--success);}.agent-edit strong{color:var(--success);}
.agent-obs{border-left-color:var(--text-secondary);}.agent-obs strong{color:var(--text-secondary);}
.agent-err{border-left-color:var(--error);}.agent-err strong{color:var(--error);}
.agent-ok{border-left-color:var(--success);}.agent-ok strong{color:var(--success);}

/* Progress items */
.pi{
  padding:7px 12px;margin:3px 0;border-radius:8px;font-size:12px;
  border-left:3px solid;font-family:var(--font-sans);
}
.pi-done{background:rgba(34,197,94,.08);border-left-color:var(--success);color:var(--text);}
.pi-active{background:rgba(226,164,64,.10);border-left-color:var(--accent);font-weight:600;
  color:var(--text);animation:pulse 2s ease-in-out infinite;}
.pi-pending{background:rgba(255,255,255,.02);border-left-color:var(--border-light);opacity:.45;}
.pi-error{background:rgba(239,68,68,.08);border-left-color:var(--error);color:var(--text);}

@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.7;}}

/* ═══════════════════════════════════════════════════
   ALERTS — Inline feedback
   ═══════════════════════════════════════════════════ */
[data-testid="stAlert"]{
  background:var(--accent-light)!important;border:1px solid var(--accent)!important;
  border-radius:8px!important;font-size:12px!important;color:var(--accent)!important;
  font-family:var(--font-sans)!important;font-weight:400!important;
}
[data-testid="stAlert"] *,
[data-testid="stAlert"] p{
  color:var(--accent)!important;
  -webkit-text-fill-color:var(--accent)!important;
  font-size:12px!important;font-weight:400!important;
  font-family:var(--font-sans)!important;
}

/* ═══════════════════════════════════════════════════
   SEPARATORS & DIVIDERS
   ═══════════════════════════════════════════════════ */
[data-testid="stHorizontalRule"]{border-color:var(--border)!important;}

/* ═══════════════════════════════════════════════════
   EXPANDER — Gaps audit
   ═══════════════════════════════════════════════════ */
[data-testid="stExpander"]{
  background:var(--surface)!important;border:1px solid var(--border)!important;
  border-radius:var(--radius)!important;
}
[data-testid="stExpander"] summary{font-size:13px!important;font-weight:600!important;
  font-family:var(--font-sans)!important;color:var(--text)!important;}

/* ═══════════════════════════════════════════════════
   METRICS — Financial KPIs
   ═══════════════════════════════════════════════════ */
[data-testid="stMetric"]{
  background:var(--surface)!important;border:1px solid var(--border)!important;
  border-radius:8px!important;padding:12px 16px!important;box-shadow:var(--shadow-sm)!important;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"]{
  font-size:11px!important;font-weight:600!important;color:var(--muted)!important;
  text-transform:uppercase!important;letter-spacing:.04em!important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"]{
  font-size:22px!important;font-weight:800!important;color:var(--accent)!important;
}

/* ═══════════════════════════════════════════════════
   SCROLLBAR — thin navy
   ═══════════════════════════════════════════════════ */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--border-light);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#3a4d7a;}

/* ═══════════════════════════════════════════════════
   TABS — B3 style
   ═══════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"]{
  gap:4px;border-bottom:1px solid var(--border);
}
.stTabs [data-baseweb="tab"]{
  font-size:12px!important;font-weight:600!important;font-family:var(--font-sans)!important;
  padding:8px 16px!important;border-radius:6px 6px 0 0!important;
  color:var(--muted)!important;transition:var(--transition)!important;
}
.stTabs [data-baseweb="tab"]:hover{background:rgba(226,164,64,.06)!important;color:var(--text)!important;}
.stTabs [aria-selected="true"]{
  color:var(--accent)!important;border-bottom:2px solid var(--accent)!important;
}
[data-testid="stTabPanel"] p,
[data-testid="stTabPanel"] li,
[data-testid="stTabPanel"] span{
  font-size:9.6px!important;
  line-height:1.5!important;
}

/* ═══════════════════════════════════════════════════
   WORKFLOW NODES — B3 Trading Pipeline
   ═══════════════════════════════════════════════════ */
.wf-nodes{
  display:flex;align-items:center;justify-content:center;gap:0;
  padding:10px 4px 14px;margin-bottom:12px;
  border-bottom:1px solid var(--border);
}
.wf-node{
  display:flex;flex-direction:column;align-items:center;gap:3px;
  padding:8px 10px;border-radius:8px;min-width:68px;
  background:rgba(255,255,255,.02);border:1px solid var(--border);
  transition:all .15s ease;
}
.wf-node.wf-active{
  background:rgba(226,164,64,.10);border-color:rgba(226,164,64,.35);
  box-shadow:0 0 14px rgba(226,164,64,.12);animation:pulse 2s ease-in-out infinite;
}
.wf-node.wf-done{background:rgba(34,197,94,.06);border-color:rgba(34,197,94,.25);}
.wf-node.wf-error{background:rgba(239,68,68,.06);border-color:rgba(239,68,68,.25);}
.wf-node-icon{font-size:20px;}
.wf-node-label{font-size:9px;font-weight:600;color:var(--text-secondary);text-align:center;}
.wf-node-status{font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);}
.wf-node.wf-active .wf-node-status{color:var(--accent);}
.wf-node.wf-done .wf-node-status{color:var(--success);}
.wf-node.wf-error .wf-node-status{color:var(--error);}
.wf-connector{width:20px;height:2px;background:var(--border);flex-shrink:0;}
.wf-connector.wf-conn-done{background:linear-gradient(90deg,var(--success),rgba(34,197,94,.25));}
.wf-connector.wf-conn-active{background:linear-gradient(90deg,var(--accent),rgba(226,164,64,.25));}

/* ═══════════════════════════════════════════════════
   TIMELINE — Execution event log
   ═══════════════════════════════════════════════════ */
.tl-entry{
  display:flex;gap:10px;padding:8px 12px;margin:4px 0;
  border-radius:8px;background:var(--surface);
  border-left:3px solid var(--border);font-size:12px;
  transition:var(--transition);
}
.tl-entry:hover{background:var(--surface-raised);}
.tl-time{
  font-family:var(--font-mono);font-size:10px;color:var(--muted);
  white-space:nowrap;min-width:52px;padding-top:2px;
}
.tl-agent{font-weight:700;font-size:11px;margin-bottom:2px;}
.tl-msg{color:var(--text-secondary);line-height:1.4;font-size:11px;}
.tl-orch{border-left-color:var(--accent);}.tl-orch .tl-agent{color:var(--accent);}
.tl-interp{border-left-color:var(--accent-blue);}.tl-interp .tl-agent{color:var(--accent-blue);}
.tl-nav{border-left-color:var(--warn);}.tl-nav .tl-agent{color:var(--warn);}
.tl-edit{border-left-color:var(--success);}.tl-edit .tl-agent{color:var(--success);}
.tl-valid{border-left-color:var(--text-secondary);}.tl-valid .tl-agent{color:var(--text-secondary);}
.tl-ok{border-left-color:var(--success);}.tl-ok .tl-agent{color:var(--success);}
.tl-err{border-left-color:var(--error);}.tl-err .tl-agent{color:var(--error);}

/* ═══════════════════════════════════════════════════
   SUMMARY — Execution results
   ═══════════════════════════════════════════════════ */
.summary-dl{
  background:linear-gradient(135deg,var(--surface),var(--bg-alt));
  border:1px solid var(--border);
  padding:16px;border-radius:var(--radius);text-align:center;
  margin:8px 0;box-shadow:var(--shadow-sm);
}
.summary-dl-title{
  font-size:12px;font-weight:700;color:var(--accent);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;
}
.change-before{color:var(--error);text-decoration:line-through;background:var(--error-bg);padding:1px 4px;border-radius:3px;}
.change-after{color:var(--success);background:var(--success-bg);padding:1px 4px;border-radius:3px;}

/* ═══════════════════════════════════════════════════
   RESPONSIVE TWEAKS
   ═══════════════════════════════════════════════════ */
@media(max-width:1200px){
  .pipeline{flex-wrap:wrap;gap:6px;padding:12px 16px;}
  .pipe-step{padding:4px 10px;}
  .top-bar{flex-direction:column;gap:8px;text-align:center;}
  .top-bar-right{justify-content:center;}
  .wf-nodes{flex-wrap:wrap;gap:4px;}
}
</style>
"""

# ─────────────────────────────────────────────────
# Constantes de fluxo
# ─────────────────────────────────────────────────
STEP_DELAY = 0.8
MAX_TENTATIVAS = 3

# ─────────────────────────────────────────────────
# LLM Provider — "perplexity" | "anthropic"
# ─────────────────────────────────────────────────
MODEL_PROVIDER = "perplexity"   # alternar para "anthropic" no ambiente corporativo

# ─────────────────────────────────────────────────
# Preview do PPTX gerado na interface
# ─────────────────────────────────────────────────
SHOW_PREVIEW = False

# Modelos padrão por provider
MODELOS_POR_PROVIDER = {
    "perplexity": ["sonar", "sonar-pro", "sonar-reasoning-pro"],
    "anthropic":  ["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
}

# ─────────────────────────────────────────────────
# Classificação de ações
# ─────────────────────────────────────────────────
ACOES_LEITURA = {"listar_estrutura", "ler_notas", "ler_dados_grafico", "ler_metadata"}
ACOES_EDICAO = {
    "alterar_texto", "alterar_celula_tabela", "adicionar_texto",
    "remover_shape", "alterar_formatacao", "substituir_texto_global",
    "mover_shape", "redimensionar_shape", "alterar_zorder",
    "duplicar_slide", "adicionar_shape", "alterar_alinhamento",
    "alterar_espacamento", "alterar_preenchimento", "alterar_borda",
    "rotacionar_shape",
    "excluir_slide", "reordenar_slides",
    "inserir_imagem", "criar_tabela", "alterar_fundo_slide",
    "alterar_notas",
    "criar_grafico", "adicionar_hyperlink", "criar_lista",
    "alterar_metadata",
    "agrupar_shapes", "desagrupar_shapes",
}

ACOES_BYPASS_NAV = {
    "listar_estrutura", "substituir_texto_global", "duplicar_slide",
    "adicionar_shape", "excluir_slide", "reordenar_slides",
    "inserir_imagem", "criar_tabela", "alterar_fundo_slide",
    "alterar_notas", "ler_notas",
    "criar_grafico", "criar_lista", "alterar_metadata",
    "ler_dados_grafico", "ler_metadata",
    "agrupar_shapes", "desagrupar_shapes",
}

ACOES_TODAS = ACOES_EDICAO | ACOES_LEITURA

# ─────────────────────────────────────────────────
# Palavras-chave para detecção de intenção
# ─────────────────────────────────────────────────
PALAVRAS_EXPORTAR = {"exportar", "baixar", "salvar", "download", "export", "save"}

_RADICAIS_EXPORTAR = ("export", "baixa", "baixe", "baixo", "salv", "download", "save")
_FRASES_EXPORTAR = (
    "me dá o arquivo", "me da o arquivo", "gera o pptx", "gerar o pptx",
    "quero o arquivo", "gera o arquivo", "gerar o arquivo",
    "manda o arquivo", "envia o arquivo", "me envi",
    "exporte para mim", "exporta para mim", "exporta pra mim",
    "exporte pra mim", "pode exportar", "pode baixar",
    "faz o download", "faça o download",
)

_RADICAIS_LEITURA = ("lista", "liste", "mostr", "descrev", "cont", "estrutura", "quant")
_FRASES_LEITURA = (
    "o que tem", "quais shapes", "quais slides", "me mostr", "me list",
    "me descrev", "o que há", "como está", "como esta",
    "mostr as notas", "mostre as notas", "ler notas", "leia as notas",
    "quais notas", "quais são as notas",
    "dados do grafico", "dados do gráfico", "ler grafico", "ler gráfico",
    "propriedades do arquivo", "metadados", "metadata", "quem criou",
    "autor do arquivo", "titulo do arquivo", "título do arquivo",
)

_RADICAIS_EDICAO = (
    "alter", "mude", "mud", "troque", "troc", "substitu",
    "traduz", "coloque", "coloq", "ponha", "adicion",
    "remov", "delet", "exclu", "apag", "duplic", "reorden",
    "mov", "redimension", "rotacion", "gir",
    "format", "negrit", "italic", "centr", "alinh",
    "deixe", "deix", "manten", "manter", "fique", "fiqu",
    "cri", "inser", "defin", "configur", "faz", "faç",
)
_FRASES_EDICAO = (
    "apenas o slide", "apenas os slide", "só o slide", "só os slide",
    "somente o slide", "somente os slide", "exclua o rest",
    "delete o rest", "apague o rest", "remova o rest",
    "mude o", "altere o", "troque o", "coloque o",
    "faça o slide", "depois exclua", "depois delete",
    "depois apague", "depois remova", "e depois",
)

# ─────────────────────────────────────────────────
# DeckForge — Agent Identity
# ─────────────────────────────────────────────────
_AGENT_BOT_CLASS = {
    "CONDUCTOR": "bot-orch",
    "ANALYST": "bot-interp",
    "LOCATOR": "bot-nav",
    "FORGE": "bot-edit",
    "AUDITOR": "bot-audit",
    "Extrator PPTX": "bot-nav",
}

def bot_html(agent_name: str, size: str = "sm") -> str:
    """Return inline HTML for a mini CSS robot representing an agent."""
    cls = _AGENT_BOT_CLASS.get(agent_name, "bot-orch")
    return (
        f'<span class="bot-inline bot-inline-{size} {cls}">'
        f'<span class="bi-head">'
        f'<span class="bi-eye"></span><span class="bi-eye"></span>'
        f'</span></span>'
    )

# Legacy compat — maps used in panels / timeline
AGENT_AVATARS = {k: bot_html(k) for k in _AGENT_BOT_CLASS}

CSS_CLASS_TO_AVATAR = {
    "agent-orch": bot_html("CONDUCTOR"),
    "agent-interp": bot_html("ANALYST"),
    "agent-nav": bot_html("LOCATOR"),
    "agent-edit": bot_html("FORGE"),
    "agent-obs": bot_html("AUDITOR"),
    "agent-err": "❌",
    "agent-ok": "✅",
}


# ─────────────────────────────────────────────────
# Classificação de intenção (v8)
# ─────────────────────────────────────────────────
def _tem_sinal_exportar(texto: str, palavras: list) -> bool:
    for fr in _FRASES_EXPORTAR:
        if fr in texto:
            return True
    for palavra in palavras:
        if palavra.startswith(_RADICAIS_EXPORTAR):
            return True
    for palavra in PALAVRAS_EXPORTAR:
        if palavra in palavras:
            return True
    return False


def _tem_sinal_edicao(texto: str, palavras: list) -> bool:
    for fr in _FRASES_EDICAO:
        if fr in texto:
            return True
    for palavra in palavras:
        if palavra.startswith(_RADICAIS_EDICAO):
            return True
    return False


def _tem_sinal_leitura(texto: str, palavras: list) -> bool:
    for fr in _FRASES_LEITURA:
        if fr in texto:
            return True
    for palavra in palavras:
        if palavra.startswith(_RADICAIS_LEITURA):
            return True
    return False


def classificar_intencao(instrucao: str) -> str:
    """Classifica a intenção do usuário.
    Retorna: 'LEITURA' | 'EDICAO' | 'EXPORTAR' | 'EDICAO_E_EXPORTAR'"""
    if instrucao is None:
        return "LEITURA"
    texto = instrucao.strip().lower()
    palavras = texto.split()

    tem_export = _tem_sinal_exportar(texto, palavras)
    tem_edicao = _tem_sinal_edicao(texto, palavras)
    tem_leitura = _tem_sinal_leitura(texto, palavras)

    if tem_export and tem_edicao:
        return "EDICAO_E_EXPORTAR"
    if tem_export and not tem_edicao and not tem_leitura:
        return "EXPORTAR"
    if tem_leitura and not tem_edicao:
        return "LEITURA"
    return "EDICAO"
