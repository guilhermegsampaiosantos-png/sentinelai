"""
parsers/zap_parser.py
Processa relatórios JSON ou XML gerados pelo OWASP ZAP.

Gerar com:
    zap-cli report -o zap_report.json -f json
    zap-cli report -o zap_report.xml  -f xml
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

import defusedxml.ElementTree as ET

from parsers.base_parser import BaseParser
from core.models import ScanReport, Vulnerability, Severity, ScanType, Status

# ZAP usa riskcode numérico: 3=High, 2=Medium, 1=Low, 0=Info
RISK_CODE_MAP = {
    "3": Severity.HIGH,
    "2": Severity.MEDIUM,
    "1": Severity.LOW,
    "0": Severity.INFO,
}

RISK_STR_MAP = {
    "high":          Severity.HIGH,
    "medium":        Severity.MEDIUM,
    "low":           Severity.LOW,
    "informational": Severity.INFO,
    "critical":      Severity.CRITICAL,
}


class ZapParser(BaseParser):

    def can_parse(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        if ext == ".xml":
            try:
                tree = ET.parse(file_path)
                return tree.getroot().tag in ("OWASPZAPReport", "report")
            except Exception:
                return False
        if ext == ".json":
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                return "site" in data or "alerts" in data
            except Exception:
                return False
        return False

    def parse(self, file_path: str) -> ScanReport:
        ext = Path(file_path).suffix.lower()
        if ext == ".xml":
            return self._parse_xml(file_path)
        return self._parse_json(file_path)

    # ------------------------------------------------------------------
    def _parse_json(self, file_path: str) -> ScanReport:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        vulns: list[Vulnerability] = []
        sites = data.get("site", [data])  # suporta array ou objeto único

        for site in (sites if isinstance(sites, list) else [sites]):
            target_url = site.get("@name", site.get("url", "unknown"))
            for alert in site.get("alerts", []):
                severity = RISK_CODE_MAP.get(
                    str(alert.get("riskcode", "1")),
                    RISK_STR_MAP.get(alert.get("risk", "").lower(), Severity.MEDIUM)
                )
                for instance in alert.get("instances", [{}]):
                    vuln = Vulnerability(
                        id=str(uuid.uuid4()),
                        title=alert.get("name", "ZAP Alert"),
                        severity=severity,
                        scan_type=ScanType.DAST,
                        tool="zap",
                        url=instance.get("uri", target_url),
                        description=alert.get("desc", ""),
                        remediation=alert.get("solution", ""),
                        cve_id=alert.get("cweid"),  # ZAP usa CWE
                        rule_id=str(alert.get("pluginid", "")),
                        status=Status.OPEN,
                        found_at=datetime.now(),
                    )
                    vulns.append(vuln)

        return ScanReport(
            tool="zap",
            scan_type=ScanType.DAST,
            target=file_path,
            scanned_at=datetime.now(),
            vulnerabilities=vulns,
            raw_file=file_path,
        )

    def _parse_xml(self, file_path: str) -> ScanReport:
        tree = ET.parse(file_path)
        root = tree.getroot()
        vulns: list[Vulnerability] = []

        for site in root.findall(".//site"):
            target_url = site.get("name", "unknown")
            for alert in site.findall(".//alertitem"):
                risk_code = alert.findtext("riskcode", "1")
                severity = RISK_CODE_MAP.get(risk_code, Severity.MEDIUM)
                uri = alert.findtext("uri", target_url)

                vuln = Vulnerability(
                    id=str(uuid.uuid4()),
                    title=alert.findtext("alert", "ZAP Alert"),
                    severity=severity,
                    scan_type=ScanType.DAST,
                    tool="zap",
                    url=uri,
                    description=alert.findtext("desc", ""),
                    remediation=alert.findtext("solution", ""),
                    rule_id=alert.findtext("pluginid", ""),
                    status=Status.OPEN,
                    found_at=datetime.now(),
                )
                vulns.append(vuln)

        return ScanReport(
            tool="zap",
            scan_type=ScanType.DAST,
            target=file_path,
            scanned_at=datetime.now(),
            vulnerabilities=vulns,
            raw_file=file_path,
        )
