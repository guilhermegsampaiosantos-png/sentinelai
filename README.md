# ASPM — Application Security Posture Management
> Protótipo técnico | Python + PyQt6

## Visão Geral
Dashboard desktop que agrega relatórios de ferramentas de segurança (Semgrep, OWASP ZAP, Snyk, Gitleaks),
normaliza as vulnerabilidades em um modelo único e calcula um score de postura de segurança.

## Ferramentas Integradas
| Ferramenta | Tipo    | Formato de entrada |
|------------|---------|--------------------|
| Semgrep    | SAST    | JSON               |
| OWASP ZAP  | DAST    | JSON / XML         |
| Snyk       | SCA     | JSON               |
| Gitleaks   | Secrets | JSON               |

## Estrutura do Projeto
```
aspm/
├── main.py                  # Entrypoint PyQt6
├── requirements.txt
├── core/
│   ├── models.py            # Dataclasses: Vulnerability, Application, Report
│   ├── aggregator.py        # Agrega resultados de todos os parsers
│   └── scorer.py            # Calcula posture score (0-100)
├── parsers/
│   ├── base_parser.py       # Interface abstrata
│   ├── semgrep_parser.py    # Semgrep JSON → Vulnerability
│   ├── zap_parser.py        # ZAP JSON/XML → Vulnerability
│   ├── snyk_parser.py       # Snyk JSON → Vulnerability
│   └── gitleaks_parser.py   # Gitleaks JSON → Vulnerability
├── ui/
│   ├── main_window.py       # QMainWindow principal
│   ├── widgets/
│   │   ├── score_widget.py  # Score gauge circular
│   │   ├── stats_bar.py     # Cards de métricas (críticas/altas/médias)
│   │   └── vuln_table.py    # QTableWidget de vulnerabilidades
│   └── views/
│       ├── dashboard_view.py
│       └── findings_view.py
├── data/
│   ├── db/                  # SQLite (findings.db)
│   └── samples/             # JSONs de exemplo para cada ferramenta
└── utils/
    ├── severity.py          # Normalização de severidade
    └── export.py            # Exportar CSV / PDF
```

## Como Executar
```bash
pip install -r requirements.txt
python main.py
```

## Como Usar
1. Gere os relatórios com cada ferramenta (ou use os samples em data/samples/)
2. No dashboard, clique em "Importar Relatório" e selecione o arquivo
3. O sistema detecta o formato automaticamente e normaliza os dados
4. O score de postura é recalculado em tempo real
