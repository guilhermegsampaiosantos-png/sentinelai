"""
core/aggregator.py
Detecta automaticamente o parser correto e agrega todos os relatórios importados.
"""
from pathlib import Path
from core.models import ScanReport, Vulnerability
from parsers.semgrep_parser import SemgrepParser
from parsers.zap_parser import ZapParser
from parsers.snyk_parser import SnykParser
from parsers.gitleaks_parser import GitleaksParser

# Ordem de tentativa na detecção automática
PARSERS = [
    GitleaksParser(),  # primeiro — estrutura muito específica
    SnykParser(),
    SemgrepParser(),
    ZapParser(),
]


class Aggregator:
    """
    Mantém a lista de relatórios importados e expõe
    a lista consolidada de vulnerabilidades.
    """

    def __init__(self):
        self._reports: list[ScanReport] = []

    def import_file(self, file_path: str) -> ScanReport:
        """
        Tenta detectar o parser correto e importa o arquivo.
        Lança ValueError se nenhum parser reconhecer o formato.
        """
        path = str(Path(file_path).resolve())

        for parser in PARSERS:
            if parser.can_parse(path):
                report = parser.parse(path)
                self._reports.append(report)
                return report

        raise ValueError(
            f"Formato não reconhecido: {file_path}\n"
            "Verifique se o arquivo é um relatório válido de "
            "Semgrep, ZAP, Snyk ou Gitleaks."
        )

    @property
    def reports(self) -> list[ScanReport]:
        return list(self._reports)

    @property
    def all_vulnerabilities(self) -> list[Vulnerability]:
        """Retorna todas as vulnerabilidades de todos os relatórios importados."""
        vulns = []
        for r in self._reports:
            vulns.extend(r.vulnerabilities)
        return vulns

    def filter(
        self,
        severity: str | None = None,
        tool: str | None = None,
        status: str | None = None,
    ) -> list[Vulnerability]:
        """Filtra vulnerabilidades por severidade, ferramenta ou status."""
        result = self.all_vulnerabilities
        if severity:
            result = [v for v in result if v.severity.value == severity]
        if tool:
            result = [v for v in result if v.tool == tool]
        if status:
            result = [v for v in result if v.status.value == status]
        return result

    def clear(self):
        self._reports.clear()
