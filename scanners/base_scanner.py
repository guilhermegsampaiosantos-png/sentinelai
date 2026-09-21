"""
scanners/base_scanner.py
Interface abstrata para scanners executados INTERNAMENTE pela ASPM.

Diferença para parsers/base_parser.py:
  - BaseParser  → LÊ um relatório (JSON/XML) já existente e normaliza.
  - BaseScanner → EXECUTA a ferramenta de verdade (subprocess) contra um
                  alvo (pasta, imagem docker, repositório) e GERA esse
                  relatório.

O objetivo é a ASPM não depender mais de o usuário rodar "semgrep --json"
por fora e importar manualmente — a própria ASPM dispara a ferramenta.

Fluxo:
    scanner = TrivyScanner()
    if scanner.is_installed():
        result = scanner.run(target="./meu-projeto")
        if result.success:
            aggregator.import_file(result.report_path)   # reaproveita o parser já existente
    else:
        print(scanner.install_hint())

Importante: um BaseScanner NUNCA interpreta o resultado — ele só gera um
arquivo de relatório no formato nativo da ferramenta. Quem entende esse
arquivo é sempre um parsers/*_parser.py já existente (ou novo, seguindo o
mesmo padrão). Isso mantém os dois papéis separados: "executar" x "entender".
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ScannerResult:
    """Resultado de uma execução de scanner. Nunca lança exceção — erros
    vêm sempre aqui dentro, para a UI poder mostrar uma mensagem amigável
    em vez de travar com um traceback."""
    tool: str
    report_path: str      # caminho do relatório gerado (vazio se success=False)
    success: bool
    error: str = ""


class BaseScanner(ABC):
    """
    Cada scanner concreto (Trivy, e futuramente Checkov, Bandit, TruffleHog...)
    precisa saber responder a duas perguntas:
      1. is_installed() — a ferramenta está disponível nesta máquina?
      2. run(target)    — execute o scan e devolva o caminho do relatório.
    """

    #: nome curto usado em logs, na UI e para identificar o scanner
    name: str = "base"

    @abstractmethod
    def is_installed(self) -> bool:
        """Verifica se o binário/dependência da ferramenta está acessível."""
        ...

    @abstractmethod
    def run(self, target: str, timeout: int = 300) -> ScannerResult:
        """
        Executa o scan contra `target` (caminho local, imagem docker, URL —
        depende da ferramenta) e retorna o caminho do relatório gerado.
        Deve capturar qualquer erro internamente e devolver via
        ScannerResult.error, nunca lançar exceção para quem chamou.
        """
        ...

    def install_hint(self) -> str:
        """Mensagem exibida na UI quando is_installed() retorna False."""
        return f"Ferramenta '{self.name}' não encontrada no PATH desta máquina."
