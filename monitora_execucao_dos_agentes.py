"""
monitora_execucao_dos_agentes.py — ObservabilityAgent + monitor_agent decorator.
Módulo-nível `obs` é inicializado pelo app principal via init_obs().
"""

import json
import time
import logging
import traceback
import functools
from io import StringIO
from datetime import datetime
from pathlib import Path


class ObservabilityAgent:
    """
    Monitora execução de todos os agentes.
    Captura: tempo, erros, warnings, métricas.
    Inclui auditoria de gaps — ações solicitadas sem suporte.
    """
    GAPS_FILE = Path(__file__).parent / "audit_gaps.json"

    def __init__(self):
        self.entries: list = []
        self.counters = {"success": 0, "warning": 0, "error": 0}
        self.gaps: list = self._carregar_gaps()
        self.logger = logging.getLogger("ObservabilityAgent")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        self._log_buffer = StringIO()
        handler = logging.StreamHandler(self._log_buffer)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        self.logger.addHandler(handler)

    # ── Gaps / Auditoria ──
    def _carregar_gaps(self) -> list:
        if self.GAPS_FILE.exists():
            try:
                return json.loads(self.GAPS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _salvar_gaps(self):
        try:
            self.GAPS_FILE.write_text(
                json.dumps(self.gaps, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except OSError:
            pass

    def registrar_gap(self, instrucao_usuario: str, acao_solicitada: str,
                      contexto: str = "", origem: str = ""):
        gap = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "instrucao_usuario": instrucao_usuario[:300],
            "acao_solicitada": acao_solicitada,
            "contexto": contexto[:200],
            "origem": origem,
            "frequencia": 1,
        }
        for g in self.gaps:
            if g["acao_solicitada"] == acao_solicitada:
                g["frequencia"] += 1
                g["timestamp"] = gap["timestamp"]
                g["instrucao_usuario"] = gap["instrucao_usuario"]
                self._salvar_gaps()
                self.log("warning", "Auditoria",
                         f"Gap repetido: '{acao_solicitada}' (freq={g['frequencia']})")
                return
        self.gaps.append(gap)
        self._salvar_gaps()
        self.log("warning", "Auditoria",
                 f"Novo gap registrado: '{acao_solicitada}' — instrução: '{instrucao_usuario[:80]}'")

    def get_gaps_resumo(self) -> list:
        return sorted(self.gaps, key=lambda g: g["frequencia"], reverse=True)

    def limpar_gaps(self):
        self.gaps = []
        self._salvar_gaps()

    def log(self, level: str, agent: str, message: str, detail: str = ""):
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "agent": agent,
            "message": message,
            "detail": detail,
        }
        self.entries.append(entry)
        self.counters[level] = self.counters.get(level, 0) + 1

        log_msg = f"{agent} | {message}" + (f" | {detail}" if detail else "")
        if level == "error":
            self.logger.error(log_msg)
        elif level == "warning":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

    def get_log_text(self) -> str:
        self._log_buffer.seek(0)
        return self._log_buffer.read()

    def get_recent(self, n: int = 10) -> list:
        return self.entries[-n:]

    def get_error_patterns(self) -> list:
        return [e for e in self.entries if e["level"] == "error"]


# ─────────────────────────────────────────────────
# Instância global — inicializada pelo app principal
# ─────────────────────────────────────────────────
obs: ObservabilityAgent = None  # type: ignore


def init_obs(session_state) -> ObservabilityAgent:
    """Inicializa ou recupera a instância global de ObservabilityAgent."""
    global obs
    if "obs_agent" not in session_state:
        session_state.obs_agent = ObservabilityAgent()
    obs = session_state.obs_agent
    return obs


def monitor_agent(agent_name: str):
    """Decorator que monitora execução de um agente.
    Usa a instância global `obs` (resolvida em tempo de chamada)."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                if obs:
                    obs.log("success", agent_name, f"Concluído em {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start
                tb = traceback.format_exc()
                if obs:
                    obs.log("error", agent_name, str(e), tb[-300:])
                raise
        return wrapper
    return decorator
