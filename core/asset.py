"""
core/asset.py
Modelo e persistência de Ativos — aplicações/serviços individuais da empresa.

É o "Contexto por Ativo": diferente do CompanyContext (um contexto único e
global), cada Asset representa um sistema específico (ex.: "Portal
Financeiro", "API de Pagamentos") com seus próprios atributos de exposição
e criticidade. Vulnerabilidades importadas podem ser vinculadas a um Asset
(ver Vulnerability.asset_id em core/models.py) para que a priorização leve
em conta o risco real daquele sistema específico, não só o da empresa como
um todo.

Salvo em data/assets.json — carregado automaticamente na inicialização.
"""
import json
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

if getattr(sys, "frozen", False):
    # Empacotado (.exe): salva em %APPDATA%\SentinelAI — mesma lógica do
    # company_context.py, ver comentário lá para o motivo.
    _DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "SentinelAI"
else:
    _DATA_DIR = Path(__file__).parent.parent / "data"

ASSETS_FILE = _DATA_DIR / "assets.json"

ENVIRONMENTS = ["development", "staging", "production"]


@dataclass
class Asset:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    environment: str = "production"
    internet_facing: bool = False
    contains_sensitive_data: bool = False
    critical_asset: bool = False
    customer_facing: bool = False

    @property
    def label(self) -> str:
        return self.name or "(sem nome)"


def load_all() -> list[Asset]:
    """Carrega todos os ativos do arquivo JSON. Retorna lista vazia se não existir."""
    try:
        if ASSETS_FILE.exists():
            with open(ASSETS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return [Asset(**item) for item in data]
    except Exception as e:
        print(f"[asset] Erro ao carregar: {e}")
    return []


def save_all(assets: list[Asset]) -> bool:
    """Salva a lista completa de ativos em JSON. Retorna True se sucesso."""
    try:
        ASSETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ASSETS_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in assets], f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[asset] Erro ao salvar: {e}")
        return False


def as_dict(assets: list[Asset]) -> dict[str, Asset]:
    """Converte a lista em dict {asset.id: Asset} — formato usado pelo prioritizer
    e pelo FindingsView para resolver o asset_id de uma vulnerabilidade."""
    return {a.id: a for a in assets}
