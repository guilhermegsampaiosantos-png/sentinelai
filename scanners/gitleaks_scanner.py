"""
scanners/gitleaks_scanner.py
Executa o Gitleaks internamente (detecção de segredos expostos em código
e histórico do Git).

Requer o binário `gitleaks` instalado e no PATH.
Instalação:
  https://github.com/gitleaks/gitleaks#installing
  macOS (brew): brew install gitleaks
  Windows (scoop): scoop install gitleaks

Observações:
  - O Gitleaks retorna código de saída 1 quando ENCONTRA segredos — isso
    não é um erro, é o comportamento esperado. Assim como TrivyScanner e
    SemgrepScanner, quem decide sucesso é a existência do relatório.
  - Se o alvo não for um repositório Git (sem pasta .git), o modo padrão
    `detect --source` falha. Nesse caso caímos automaticamente para
    `--no-git`, que varre os arquivos da pasta sem depender de histórico
    de commits.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from scanners.base_scanner import BaseScanner, ScannerResult


class GitleaksScanner(BaseScanner):
    name = "gitleaks"

    def is_installed(self) -> bool:
        return shutil.which("gitleaks") is not None

    def install_hint(self) -> str:
        return (
            "Gitleaks não encontrado no PATH.\n"
            "Instale em: https://github.com/gitleaks/gitleaks#installing\n"
            "macOS (brew): brew install gitleaks\n"
            "Windows (scoop): scoop install gitleaks"
        )

    def run(self, target: str, timeout: int = 300) -> ScannerResult:
        if not self.is_installed():
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=self.install_hint(),
            )

        report_path = str(Path(tempfile.gettempdir()) / "gitleaks_report.json")
        is_git_repo = (Path(target) / ".git").exists()

        cmd = [
            "gitleaks", "detect",
            "--source", target,
            "--report-format", "json",
            "--report-path", report_path,
            "--no-banner",
        ]
        if not is_git_repo:
            # Pasta comum (não é um repositório Git) — varre só os arquivos
            # do diretório, sem tentar ler histórico de commits.
            cmd.append("--no-git")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=f"Gitleaks excedeu o tempo limite de {timeout}s para o alvo '{target}'.",
            )
        except Exception as e:
            return ScannerResult(tool=self.name, report_path="", success=False, error=str(e))

        # returncode 1 = "encontrou segredos" (esperado, não é erro).
        # O sinal real de sucesso é o relatório ter sido gerado.
        if not Path(report_path).exists():
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=proc.stderr.strip() or "Gitleaks executou mas não gerou relatório.",
            )

        return ScannerResult(tool=self.name, report_path=report_path, success=True)
