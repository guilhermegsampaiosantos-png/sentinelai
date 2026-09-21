"""
core/settings.py
Configurações gerais da aplicação (hoje: só a Groq API Key).
Salvo em data/settings.json — mesmo padrão de persistência usado por
core/company_context.py e core/asset.py.

Por que isso existe (P2 #15 da revisão de UX): antes, o campo da Groq API
Key morava dentro da aba "Inteligência Artificial", junto com as ações de
IA — uma credencial ficava exposta no meio da tela de trabalho e tinha que
ser redigitada a cada sessão, já que não era persistida em lugar nenhum.
Agora vive numa tela de Configurações própria e é salva em disco.
"""
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

if getattr(sys, "frozen", False):
    _DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "SentinelAI"
else:
    _DATA_DIR = Path(__file__).parent.parent / "data"

SETTINGS_FILE = _DATA_DIR / "settings.json"


@dataclass
class AppSettings:
    groq_api_key: str = ""


def load() -> AppSettings:
    if not SETTINGS_FILE.exists():
        return AppSettings()
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return AppSettings(groq_api_key=data.get("groq_api_key", ""))
    except Exception:
        return AppSettings()


def save(settings: AppSettings) -> bool:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
