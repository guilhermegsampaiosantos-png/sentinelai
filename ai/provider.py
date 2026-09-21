"""
ai/provider.py
Abstração de provider LLM com fallback automático.

Prioridade:
  1. Ollama local (http://localhost:11434) — privado, sem internet
  2. Groq API   (https://api.groq.com)    — gratuito, rápido, precisa de chave

Uso:
    provider = LLMProvider()
    response = provider.chat("Explique esta vulnerabilidade...")
"""
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from enum import Enum


class Backend(str, Enum):
    OLLAMA = "ollama"
    GROQ   = "groq"
    NONE   = "none"


@dataclass
class LLMResponse:
    text: str
    backend: Backend
    model: str


class LLMProvider:
    # Modelos preferidos por backend
    OLLAMA_MODEL  = "gemma3:4b"
    # Lista de modelos em ordem de preferência — tenta o próximo se o atual falhar
    GROQ_MODELS = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound-mini",
        "qwen/qwen3.6-27b",
    ]
    GROQ_MODEL    = GROQ_MODELS[0]  # modelo ativo atual

    OLLAMA_URL = "http://localhost:11434/api/chat"
    GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, groq_api_key: str | None = None):
        self._groq_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self._backend  = self._detect_backend()

    # ------------------------------------------------------------------
    def _detect_backend(self) -> Backend:
        """Testa Ollama local primeiro; cai para Groq se disponível."""
        if self._test_ollama():
            return Backend.OLLAMA
        if self._groq_key:
            return Backend.GROQ
        return Backend.NONE

    def _test_ollama(self) -> bool:
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    @property
    def available(self) -> bool:
        return self._backend != Backend.NONE

    @property
    def backend_name(self) -> str:
        return self._backend.value

    def set_groq_key(self, key: str):
        self._groq_key = key
        if self._backend == Backend.NONE and key:
            self._backend = Backend.GROQ

    # ------------------------------------------------------------------
    def chat(self, prompt: str, system: str = "", timeout: int = 60) -> LLMResponse:
        """
        Envia uma mensagem para o LLM ativo e retorna a resposta.
        Lança RuntimeError se nenhum backend estiver disponível.
        """
        if self._backend == Backend.OLLAMA:
            return self._ollama_chat(prompt, system, timeout)
        if self._backend == Backend.GROQ:
            return self._groq_chat(prompt, system, timeout)
        raise RuntimeError(
            "Nenhum backend de IA disponível.\n"
            "• Instale o Ollama: https://ollama.com  →  ollama pull gemma3:4b\n"
            "• Ou configure GROQ_API_KEY (gratuito em https://console.groq.com)"
        )

    # ------------------------------------------------------------------
    def _ollama_chat(self, prompt: str, system: str, timeout: int) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = json.dumps({
            "model": self.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            self.OLLAMA_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))

        text = data["message"]["content"].strip()
        return LLMResponse(text=text, backend=Backend.OLLAMA, model=self.OLLAMA_MODEL)

    def _groq_chat(self, prompt: str, system: str, timeout: int) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for model in self.GROQ_MODELS:
            body = json.dumps({
                "model": model,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.3,
            }).encode()

            req = urllib.request.Request(
                self.GROQ_URL,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._groq_key}",
                    # Sem um User-Agent "normal", a Groq (atrás de WAF/Cloudflare)
                    # devolve 403 para o User-Agent padrão do urllib
                    # ("Python-urllib/x.y"), mesmo com a chave correta.
                    "User-Agent": "aspm-app/1.0 (+https://github.com)",
                    "Accept": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read()
                    data = json.loads(raw.decode("utf-8"))
                self.GROQ_MODEL = model  # atualiza modelo ativo
                text = data["choices"][0]["message"]["content"].strip()
                return LLMResponse(text=text, backend=Backend.GROQ, model=model)
            except urllib.error.HTTPError as e:
                if e.code in (401,):
                    raise RuntimeError("Chave Groq inválida ou expirada. Gere uma nova em console.groq.com.")
                if e.code == 429:
                    raise RuntimeError("Limite de requisições Groq atingido. Aguarde 1 minuto e tente novamente.")
                # 403 ou outro erro: tenta próximo modelo
                last_error = e
                continue

        raise RuntimeError(
            f"Nenhum modelo Groq disponível (último erro: {last_error.code if last_error else 'desconhecido'}).\n"
            "Verifique sua chave em console.groq.com."
        )
