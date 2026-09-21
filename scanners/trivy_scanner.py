"""
scanners/trivy_scanner.py
Executa o Trivy internamente. Uma única ferramenta cobre 3 estágios da
esteira que hoje o projeto NÃO tinha:

  - Container : CVEs em pacotes do SO / libs dentro de uma imagem Docker
  - IaC       : más configurações em Dockerfile, Terraform, Kubernetes,
                CloudFormation
  - Secrets   : segredos expostos em camadas de imagem ou arquivos

Requer o binário `trivy` instalado e no PATH.
Instalação:
  https://aquasecurity.github.io/trivy/latest/getting-started/installation/
  Windows (winget): winget install AquaSecurity.trivy
  macOS (brew):     brew install trivy
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from scanners.base_scanner import BaseScanner, ScannerResult


class TrivyMode:
    """Modos de execução do Trivy. O scanner escolhe automaticamente com
    base no alvo, mas pode ser forçado via parâmetro `mode` em run()."""
    IMAGE  = "image"   # ex: target="nginx:latest" (imagem docker)
    FS     = "fs"      # ex: target="./meu-projeto" (pasta/repositório local)
    CONFIG = "config"  # ex: target="./infra" (somente arquivos de IaC)


class TrivyScanner(BaseScanner):
    name = "trivy"

    def is_installed(self) -> bool:
        return shutil.which("trivy") is not None

    def install_hint(self) -> str:
        return (
            "Trivy não encontrado no PATH.\n"
            "Instale em: https://aquasecurity.github.io/trivy/latest/getting-started/installation/\n"
            "Windows (winget): winget install AquaSecurity.trivy\n"
            "macOS (brew): brew install trivy"
        )

    def run(self, target: str, mode: str = TrivyMode.FS, timeout: int = 300) -> ScannerResult:
        if not self.is_installed():
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=self.install_hint(),
            )

        # Relatório temporário — o Aggregator lê e persiste o que importa,
        # então não precisamos manter esse arquivo depois.
        report_path = str(Path(tempfile.gettempdir()) / f"trivy_{mode}_report.json")

        cmd = [
            "trivy", mode,
            "--format", "json",
            "--output", report_path,
            "--quiet",
        ]
        # Nos modos fs/image habilitamos os 3 scanners do Trivy explicitamente
        # (em versões recentes o padrão é só 'vuln'). No modo 'config' o
        # Trivy já foca em más configurações por natureza.
        if mode in (TrivyMode.FS, TrivyMode.IMAGE):
            cmd += ["--scanners", "vuln,secret,misconfig"]

        cmd.append(target)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=f"Trivy excedeu o tempo limite de {timeout}s para o alvo '{target}'.",
            )
        except Exception as e:
            return ScannerResult(tool=self.name, report_path="", success=False, error=str(e))

        # Trivy usa código de saída != 0 dependendo de --exit-code configurado.
        # Sem essa flag (nosso caso), 0 = execução ok. Qualquer outro valor
        # aqui é erro real de execução (alvo inválido, binário quebrado etc.).
        if proc.returncode != 0:
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=proc.stderr.strip() or f"Trivy retornou código {proc.returncode}.",
            )

        if not Path(report_path).exists():
            return ScannerResult(
                tool=self.name, report_path="", success=False,
                error=proc.stderr.strip() or "Trivy executou mas não gerou relatório.",
            )

        return ScannerResult(tool=self.name, report_path=report_path, success=True)
