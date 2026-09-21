"""
utils/resources.py
Resolve caminhos de assets (ícones etc.) tanto em execução via código-fonte
(`py main.py`) quanto empacotado como .exe standalone (PyInstaller), onde os
arquivos ficam extraídos em uma pasta temporária referenciada por sys._MEIPASS.
"""
import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """Retorna o caminho absoluto de um recurso (ex: 'assets/icon.ico')."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        base_path = Path(__file__).parent.parent
    return str(Path(base_path) / relative_path)
