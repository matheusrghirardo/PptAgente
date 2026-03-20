"""
cliente_modelos_de_linguagem.py — Cliente LLM multi-provider (Perplexity / Anthropic).

Seleciona o backend via ``provider``:
  - "perplexity" → OpenAI SDK apontando para api.perplexity.ai
  - "anthropic"  → Anthropic SDK nativo (Claude)
"""

import time

from openai import OpenAI


def _get_anthropic_client(api_key: str):
    """Importa e instancia o cliente Anthropic sob demanda."""
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


class LLMClient:
    def __init__(self, api_key: str, model: str = "sonar",
                 provider: str = "perplexity"):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key

        if self.provider == "anthropic":
            self._anthropic = _get_anthropic_client(api_key)
            self.client = None  # OpenAI client not used
        else:
            self.client = OpenAI(api_key=api_key,
                                 base_url="https://api.perplexity.ai")
            self._anthropic = None

    # ── helpers ──────────────────────────────────

    @staticmethod
    def _sanitizar_historico(history: list) -> list:
        """Garante alternância user/assistant exigida pela Perplexity API."""
        if not history:
            return []
        limpo = []
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content or role not in ("user", "assistant"):
                continue
            if limpo and limpo[-1]["role"] == role:
                limpo[-1]["content"] += "\n" + content
            else:
                limpo.append({"role": role, "content": content})
        return limpo

    def _build_messages(self, system_prompt: str, user_message: str,
                        history: list = None) -> list:
        """Monta a lista de mensagens para a API."""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            limpo = self._sanitizar_historico(history)
            if limpo and limpo[-1]["role"] == "user":
                limpo.pop()
            if limpo and limpo[0]["role"] == "assistant":
                limpo.pop(0)
            messages.extend(limpo)
        messages.append({"role": "user", "content": user_message})
        return messages

    # ── Anthropic backend ────────────────────────

    def _chat_anthropic(self, system_prompt: str, user_message: str,
                        history: list = None, model: str = None) -> str:
        """Envia mensagem via Anthropic SDK (Claude)."""
        msgs = []
        if history:
            limpo = self._sanitizar_historico(history)
            if limpo and limpo[-1]["role"] == "user":
                limpo.pop()
            if limpo and limpo[0]["role"] == "assistant":
                limpo.pop(0)
            msgs.extend(limpo)
        msgs.append({"role": "user", "content": user_message})

        max_tentativas = 3
        _model = model or self.model
        for tentativa in range(max_tentativas):
            try:
                resp = self._anthropic.messages.create(
                    model=_model,
                    max_tokens=32768,
                    temperature=0.1,
                    system=system_prompt,
                    messages=msgs,
                )
                return resp.content[0].text.strip()
            except Exception as e:
                erro_str = str(e).lower()
                conexao = any(k in erro_str for k in (
                    "connection", "timeout", "refused", "reset", "eof", "ssl", "overloaded"))
                if conexao and tentativa < max_tentativas - 1:
                    time.sleep(2 * (tentativa + 1))
                    continue
                return f"ERRO_LLM: {str(e)}"
        return "ERRO_LLM: Max retries exceeded"

    def _chat_anthropic_with_finish(self, system_prompt: str, user_message: str,
                                    history: list = None, model: str = None) -> tuple:
        """Anthropic chat retornando (content, finish_reason)."""
        msgs = []
        if history:
            limpo = self._sanitizar_historico(history)
            if limpo and limpo[-1]["role"] == "user":
                limpo.pop()
            if limpo and limpo[0]["role"] == "assistant":
                limpo.pop(0)
            msgs.extend(limpo)
        msgs.append({"role": "user", "content": user_message})

        _model = model or self.model
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                resp = self._anthropic.messages.create(
                    model=_model,
                    max_tokens=32768,
                    temperature=0.1,
                    system=system_prompt,
                    messages=msgs,
                )
                content = resp.content[0].text.strip()
                finish = "stop" if resp.stop_reason == "end_turn" else resp.stop_reason or "stop"
                return content, finish
            except Exception as e:
                erro_str = str(e).lower()
                conexao = any(k in erro_str for k in (
                    "connection", "timeout", "refused", "reset", "eof", "ssl", "overloaded"))
                if conexao and tentativa < max_tentativas - 1:
                    time.sleep(2 * (tentativa + 1))
                    continue
                return f"ERRO_LLM: {str(e)}", "error"
        return "ERRO_LLM: Max retries exceeded", "error"

    # ── public API (provider-agnostic) ───────────

    def chat(self, system_prompt: str, user_message: str,
             history: list = None, model: str = None) -> str:
        """Envia mensagem com histórico completo ao LLM."""
        if self.provider == "anthropic":
            return self._chat_anthropic(system_prompt, user_message, history, model=model)

        _model = model or self.model
        messages = self._build_messages(system_prompt, user_message, history)
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                resp = self.client.chat.completions.create(
                    model=_model, messages=messages,
                    temperature=0.1, max_tokens=32768,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                erro_str = str(e).lower()
                conexao = any(k in erro_str for k in ("connection", "timeout", "refused", "reset", "eof", "ssl"))
                if conexao and tentativa < max_tentativas - 1:
                    time.sleep(2 * (tentativa + 1))
                    continue
                return f"ERRO_LLM: {str(e)}"
        return "ERRO_LLM: Max retries exceeded"

    def chat_with_finish(self, system_prompt: str, user_message: str,
                         history: list = None, model: str = None) -> tuple:
        """Como chat(), mas também retorna finish_reason para detectar truncamento.

        Returns:
            (content: str, finish_reason: str)  — finish_reason é 'stop', 'length' ou 'error'
        """
        if self.provider == "anthropic":
            return self._chat_anthropic_with_finish(system_prompt, user_message, history, model=model)

        _model = model or self.model
        messages = self._build_messages(system_prompt, user_message, history)
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                resp = self.client.chat.completions.create(
                    model=_model, messages=messages,
                    temperature=0.1, max_tokens=32768,
                )
                content = resp.choices[0].message.content.strip()
                finish_reason = resp.choices[0].finish_reason or "stop"
                return content, finish_reason
            except Exception as e:
                erro_str = str(e).lower()
                conexao = any(k in erro_str for k in ("connection", "timeout", "refused", "reset", "eof", "ssl"))
                if conexao and tentativa < max_tentativas - 1:
                    time.sleep(2 * (tentativa + 1))
                    continue
                return f"ERRO_LLM: {str(e)}", "error"
        return "ERRO_LLM: Max retries exceeded", "error"
