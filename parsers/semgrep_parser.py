"""
parsers/semgrep_parser.py
Processa relatórios JSON gerados pelo Semgrep.

Gerar com:
    semgrep scan --json -o semgrep_report.json <diretório>
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from parsers.base_parser import BaseParser
from core.models import ScanReport, Vulnerability, Severity, ScanType, Status

SEVERITY_MAP = {
    "error":   Severity.HIGH,
    "warning": Severity.MEDIUM,
    "info":    Severity.LOW,
    # Semgrep extras via metadata
    "critical": Severity.CRITICAL,
    "high":     Severity.HIGH,
    "medium":   Severity.MEDIUM,
    "low":      Severity.LOW,
}


class SemgrepParser(BaseParser):

    def can_parse(self, file_path: str) -> bool:
        """Detecta se é um relatório Semgrep verificando a chave 'results'."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return "results" in data and "version" in data
        except Exception:
            return False

    def parse(self, file_path: str) -> ScanReport:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        vulns: list[Vulnerability] = []

        for result in data.get("results", []):
            meta = result.get("extra", {})
            severity_raw = meta.get("severity", "warning").lower()
            # Semgrep pode sobrescrever severidade via metadata
            meta_sev = meta.get("metadata", {}).get("confidence", None)
            severity = SEVERITY_MAP.get(severity_raw, Severity.MEDIUM)

            vuln = Vulnerability(
                id=str(uuid.uuid4()),
                title=result.get("check_id", "Sem título"),
                severity=severity,
                scan_type=ScanType.SAST,
                tool="semgrep",
                file_path=result.get("path"),
                line=result.get("start", {}).get("line"),
                description=meta.get("message", ""),
                remediation=meta.get("metadata", {}).get("fix", ""),
                rule_id=result.get("check_id"),
                status=Status.OPEN,
                found_at=datetime.now(),
            )
            vulns.append(vuln)

        return ScanReport(
            tool="semgrep",
            scan_type=ScanType.SAST,
            target=Path(file_path).stem,
            scanned_at=datetime.now(),
            vulnerabilities=vulns,
            raw_file=file_path,
        )
