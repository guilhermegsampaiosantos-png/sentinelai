"""
parsers/gitleaks_parser.py
Processa relatórios JSON gerados pelo Gitleaks.

Gerar com:
    gitleaks detect --source . -r gitleaks_report.json -f json
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from parsers.base_parser import BaseParser
from core.models import ScanReport, Vulnerability, Severity, ScanType, Status


class GitleaksParser(BaseParser):
    """
    Gitleaks não tem severidade nativa — todo vazamento de segredo
    é tratado como CRITICAL por padrão (segredo exposto = comprometimento direto).
    """

    def can_parse(self, file_path: str) -> bool:
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            # Gitleaks retorna array de objetos com 'RuleID' e 'Commit'
            return (
                isinstance(data, list)
                and len(data) > 0
                and "RuleID" in data[0]
                and "Commit" in data[0]
            )
        except Exception:
            return False

    def parse(self, file_path: str) -> ScanReport:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        vulns: list[Vulnerability] = []

        for finding in data:
            rule_id = finding.get("RuleID", "unknown-rule")
            description = finding.get("Description", "")
            secret_masked = self._mask_secret(finding.get("Secret", ""))

            vuln = Vulnerability(
                id=str(uuid.uuid4()),
                title=f"Segredo exposto: {rule_id}",
                severity=Severity.CRITICAL,          # sempre crítico
                scan_type=ScanType.SECRETS,
                tool="gitleaks",
                file_path=finding.get("File"),
                line=finding.get("StartLine"),
                description=(
                    f"{description}\n"
                    f"Commit: {finding.get('Commit', 'N/A')}\n"
                    f"Author: {finding.get('Author', 'N/A')}\n"
                    f"Secret (mascarado): {secret_masked}"
                ),
                remediation=(
                    "1. Revogar a credencial imediatamente.\n"
                    "2. Remover do histórico Git com git-filter-repo.\n"
                    "3. Adicionar ao .gitignore ou usar variáveis de ambiente."
                ),
                rule_id=rule_id,
                status=Status.OPEN,
                found_at=datetime.now(),
            )
            vulns.append(vuln)

        return ScanReport(
            tool="gitleaks",
            scan_type=ScanType.SECRETS,
            target=Path(file_path).stem,
            scanned_at=datetime.now(),
            vulnerabilities=vulns,
            raw_file=file_path,
        )

    @staticmethod
    def _mask_secret(secret: str) -> str:
        """Mostra apenas os 4 primeiros caracteres — nunca exibe o segredo completo."""
        if len(secret) <= 4:
            return "****"
        return secret[:4] + "*" * (len(secret) - 4)
