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

## Inteligência Artificial
A aba "Inteligência Artificial" usa um provider de LLM com fallback automático
(Ollama local, quando disponível, ou Groq como alternativa) para três funções:
- **Explicação** de vulnerabilidades em linguagem simples, sem jargão técnico
- **Priorização** inteligente — combina heurísticas determinísticas com o LLM
  para sugerir o que corrigir primeiro, com justificativa
- **Detecção de anomalias** — padrões recorrentes e comportamentos fora do
  esperado entre os relatórios importados

## Estrutura do Projeto
```
aspm/
├── main.py                    # Entrypoint PyQt6
├── requirements.txt
├── core/
│   ├── models.py               # Dataclasses: Vulnerability, ScanReport etc.
│   ├── aggregator.py           # Detecta o parser certo e agrega os relatórios
│   └── scorer.py               # Calcula o score de postura (0-100)
├── parsers/
│   ├── base_parser.py          # Interface abstrata
│   ├── semgrep_parser.py       # Semgrep JSON → Vulnerability
│   ├── zap_parser.py           # ZAP JSON/XML → Vulnerability
│   ├── snyk_parser.py          # Snyk JSON → Vulnerability
│   └── gitleaks_parser.py      # Gitleaks JSON → Vulnerability
├── ai/
│   ├── provider.py             # Abstração de LLM (Ollama local ou Groq)
│   ├── explainer.py            # Explica vulnerabilidades em linguagem simples
│   ├── prioritizer.py          # Priorização inteligente (heurística + LLM)
│   └── anomaly_detector.py     # Detecção de padrões e anomalias
├── ui/
│   ├── main_window.py          # QMainWindow principal
│   ├── theme.py                 # Paleta de cores central da UI
│   ├── icons.py                 # Ícones vetoriais desenhados via QPainter
│   ├── charts.py                 # Gráficos desenhados via QPainter (sem libs externas)
│   ├── easter_eggs.py            # 🥚 easter eggs escondidos
│   └── views/
│       ├── dashboard_view.py
│       ├── findings_view.py
│       └── ai_view.py           # Tab de Inteligência Artificial
├── data/
│   └── samples/                # JSONs de exemplo para cada ferramenta
└── utils/
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
