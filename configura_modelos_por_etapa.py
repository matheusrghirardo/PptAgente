"""
configura_modelos_por_etapa.py — Configuração centralizada de modelos LLM por etapa.

Troque apenas o AMBIENTE_ATIVO para migrar entre dev e produção.
Nunca altere os perfis diretamente — crie um novo perfil se necessário.
"""

from __future__ import annotations

# ── AMBIENTE ATIVO ─────────────────────────────────────────────
# Troque aqui para migrar entre ambientes:
# "dev"         → Perplexity Sonar (PC pessoal)
# "corporativo" → Anthropic + Google + OpenAI + DeepSeek
AMBIENTE_ATIVO = "dev"

# ── PERFIS DE MODELO POR AMBIENTE ─────────────────────────────
PERFIS: dict[str, dict[str, str]] = {

    "dev": {
        # Perplexity — disponível no desenvolvimento local
        "pattern_extractor":   "sonar",
        "excel_structural":    "sonar",
        "excel_extractor":     "sonar-reasoning-pro",
        "excel_validator":     "sonar",
        "pptx_mapper":         "sonar-pro",
        "observability":       "sonar",
        "conclusao":           "sonar-pro",
    },

    "corporativo": {
        # Anthropic + Google + OpenAI + DeepSeek
        # Tarefas leves → Gemini Flash (rápido, barato, contexto grande)
        # Tarefas críticas → Claude Sonnet (melhor para JSON + pt-BR financeiro)
        # Debug/logs → DeepSeek (custo mínimo)
        # Fallback Excel irregular → GPT-4o
        "pattern_extractor":   "gemini-1.5-flash",
        "excel_structural":    "gemini-1.5-flash",
        "excel_extractor":     "claude-sonnet-4-6",
        "excel_validator":     "gemini-1.5-flash",
        "pptx_mapper":         "claude-sonnet-4-6",
        "observability":       "deepseek-chat",
        "conclusao":           "claude-sonnet-4-6",
    },

    "fallback": {
        # Usar se o modelo principal falhar repetidamente
        # Ex: Excel muito irregular onde Sonnet não dá conta
        "pattern_extractor":   "gpt-4o-mini",
        "excel_structural":    "gpt-4o-mini",
        "excel_extractor":     "gpt-4o",
        "excel_validator":     "gpt-4o-mini",
        "pptx_mapper":         "gpt-4o",
        "observability":       "gpt-4o-mini",
        "conclusao":           "gpt-4o",
    },
}

# ── INTERFACE PÚBLICA ──────────────────────────────────────────
def modelo(etapa: str, ambiente: str | None = None) -> str:
    """Retorna o modelo configurado para uma etapa do pipeline.

    Args:
        etapa: Nome da etapa. Ex: 'pptx_mapper', 'excel_extractor'
        ambiente: Sobrescreve AMBIENTE_ATIVO se fornecido.

    Returns:
        Nome do modelo como string.

    Raises:
        KeyError: Se etapa ou ambiente não existirem nos perfis.
    """
    env = ambiente or AMBIENTE_ATIVO
    if env not in PERFIS:
        raise KeyError(f"Ambiente '{env}' não encontrado em PERFIS. "
                       f"Disponíveis: {list(PERFIS.keys())}")
    if etapa not in PERFIS[env]:
        raise KeyError(f"Etapa '{etapa}' não encontrada no perfil '{env}'. "
                       f"Disponíveis: {list(PERFIS[env].keys())}")
    return PERFIS[env][etapa]


def listar_configuracao_ativa() -> dict[str, str]:
    """Retorna o perfil completo do ambiente ativo."""
    return dict(PERFIS[AMBIENTE_ATIVO])
