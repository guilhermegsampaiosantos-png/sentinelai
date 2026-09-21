"""
scanners/semgrep_scanner.py
Executa o Semgrep internamente (SAST — análise estática de código-fonte).

Requer o binário `semgrep` instalado e no PATH.
Instalação:
  https://semgrep.dev/docs/getting-started/
  pip install semgrep
  macOS (brew): brew install semgrep

Observação importante (validada com scan real contra Teiko-org/backend):
o código de saída do Semgrep não é confiável como sinal de sucesso — ele
retorna != 0 tanto em erros reais quanto em execuções que apenas
encontraram findings (dependendo da versão/config). Por isso, assim como
no TrivyScanner, quem decide se o scan funcionou é a EXISTÊNCIA do
arquivo de relatório, não o returncode.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from scanners.base_scanner import BaseScanner, ScannerResult


class SemgrepScanner(BaseScanner):
    name = "semgrep"

    def is_installed(self) -> bool:
        return shutil.which("semgrep") is not None

    def install_hint(self) -> str:
        return (
            "Semgrep não encontrado no PATH.\n"
            "Instale com: pip install semgrep\n"
            "macOS (brew): brew install semgrep\n"
            "Mais opções: https://semgrep.dev/docs/getting-started/"
        )

    def run(self, target: str, timeout: int = 300) -> ScannerResult:
        if not self.is_installed():
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=self.install_hint(),
            )

        report_path = str(Path(tempfile.gettempdir()) / "semgrep_report.json")

        cmd = [
            "semgrep",
            "--config", "auto",
            "--json",
            "--output", report_path,
            "--quiet",
            target,
        ]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=f"Semgrep excedeu o tempo limite de {timeout}s para o alvo '{target}'.",
            )
        except Exception as e:
            return ScannerResult(tool=self.name, report_path="", success=False, error=str(e))

        # Não confiamos no returncode (ver docstring) — o sinal real de
        # sucesso é o arquivo de relatório ter sido gerado.
        if not Path(report_path).exists():
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=proc.stderr.strip() or "Semgrep executou mas não gerou relatório.",
            )

        return ScannerResult(tool=self.name, report_path=report_path, success=True)
