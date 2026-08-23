"""
parsers/base_parser.py
Interface abstrata que todos os parsers devem implementar.
"""
from abc import ABC, abstractmethod
from core.models import ScanReport


class BaseParser(ABC):
    """
    Cada parser recebe o caminho de um arquivo de relatório
    e retorna um ScanReport normalizado.
    """

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        Verifica se este parser consegue processar o arquivo.
        Usado pela detecção automática de formato.
        """
        ...

    @abstractmethod
    def parse(self, file_path: str) -> ScanReport:
        """Lê o arquivo e retorna um ScanReport com vulnerabilidades normalizadas."""
        ...

    def _safe_severity(self, raw: str, mapping: dict) -> str:
        """Normaliza string de severidade usando um mapeamento customizado."""
        return mapping.get(raw.lower().strip(), "medium")
