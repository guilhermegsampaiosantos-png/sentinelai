# SentinelAI — ASPM (Application Security Posture Management)
> Protótipo técnico | Python + PyQt6

## Visão Geral
Dashboard desktop que agrega relatórios de múltiplas ferramentas de segurança,
normaliza tudo em um modelo único de vulnerabilidade e calcula um score de
postura de segurança — com uma camada de IA que explica, prioriza e detecta
padrões, sempre considerando o contexto real da empresa e dos ativos
cadastrados.

## Ferramentas Integradas
| Ferramenta | Tipo(s)                          | Formato de entrada | Execução interna |
|------------|-----------------------------------|---------------------|---------------------|
| Trivy      | Container + IaC + Secrets           | JSON                | Sim (`scanners/trivy_scanner.py`) |
| Semgrep    | SAST                               | JSON                | Sim (`scanners/semgrep_scanner.py`) |
| Gitleaks   | Secrets                             | JSON                | Sim (`scanners/gitleaks_scanner.py`) |
| OWASP ZAP  | DAST                               | JSON / XML          | Não (importação manual) |
| Snyk       | SCA                                 | JSON                | Não (importação manual) |

O Trivy cobre três estágios num único relatório: CVEs de pacotes de SO/imagem
(Container), más configurações de Dockerfile/Kubernetes/Terraform (IaC) e
segredos expostos em camadas de imagem ou arquivos (Secrets). Trivy, Semgrep
e Gitleaks podem ser disparados diretamente pelo app contra uma pasta de
projeto ("Escanear Pasta", requer os binários correspondentes no PATH) —
ZAP e Snyk continuam só via importação manual do relatório, por
dependerem de infraestrutura externa (app rodando / build autenticado).

## Navegação (sidebar)
- **Dashboard** — score de postura, distribuição de achados por ferramenta e
  por tipo de scan. Sem nenhum relatório importado ainda, mostra um checklist
  de primeiros passos em vez de um painel zerado — a ASPM nunca afirma
  cobertura que não tem.
- **Findings** — lista completa das vulnerabilidades normalizadas, com busca,
  ordenação por coluna, filtros (severidade, ferramenta, status, ativo) e
  vínculo de findings a ativos cadastrados.
- **Inteligência Artificial**, dividida em três sub-abas:
  - *Explicar Vuln* — explica uma vulnerabilidade em linguagem simples, sem jargão.
  - *Priorização IA* — ranking de prioridade combinando heurística determinística
    e reordenação por LLM (ver seção abaixo).
  - *Padrões & Anomalias* — padrões recorrentes, módulos mais afetados
    (hotspots) e correlações suspeitas entre relatórios importados.
- **Attack Path** — cruza os findings importados com o contexto dos ativos
  para montar cadeias de risco (exposição → vulnerabilidade → impacto).
  Determinístico, não depende de IA.
- **Ativos** — CRUD de aplicações/serviços da empresa (ambiente, exposição à
  internet, criticidade, dados sensíveis) — dá contexto por sistema à
  priorização e ao Attack Path.
- **Contexto da Empresa** — formulário com setor, porte, prioridades de
  negócio (disponibilidade/confidencialidade/integridade), dados sensíveis,
  exposição à internet, infraestrutura e regulamentações. Usado tanto no
  score determinístico quanto injetado no prompt da IA.

## Priorização Inteligente (score transparente)
O score de cada vulnerabilidade é a soma de parcelas nomeadas — não uma caixa
preta:

```
Severidade base (crítica): +40
CVSS (9.8):                +24.5
Segredo exposto:           +15
Confidencialidade prioritária (contexto): +8
Setor Financeiro (contexto):              +5
──────────────────────────────────────────
Pre-score:                                92.5  (teto: 100)
```

Esse pre-score determinístico é combinado (70/30) com a reordenação opcional
do LLM, que também justifica sua posição no ranking. Sem contexto de empresa
preenchido ou sem IA disponível, o app cai automaticamente em critérios
técnicos padrão — nunca trava a funcionalidade.

## Inteligência Artificial
A aba de IA usa um provider com fallback automático:
1. **Ollama local** (`http://localhost:11434`) — privado, sem internet.
2. **Groq API** (`https://api.groq.com`) — gratuito, precisa de chave.

A Groq API Key é configurada em **Configurações** (botão na barra da aba de
IA) e persiste em `data/settings.json` — arquivo local, fora do controle de
versão (ver `.gitignore`).

## Estrutura do Projeto
```
sentinelai_merged/
├── main.py                      # Entrypoint PyQt6
├── requirements.txt
├── core/
│   ├── models.py                 # Dataclasses: Vulnerability, ScanReport, PostureScore...
│   ├── aggregator.py             # Detecta o parser certo e agrega os relatórios
│   ├── scorer.py                 # Calcula o score de postura (0-100)
│   ├── coverage.py               # Quais tipos de scan foram efetivamente executados
│   ├── company_context.py        # Modelo + persistência do Contexto da Empresa
│   ├── asset.py                  # Modelo + persistência dos Ativos
│   ├── attack_path.py            # Motor determinístico de cadeias de risco
│   └── settings.py               # Configurações do app (Groq API Key)
├── parsers/
│   ├── base_parser.py            # Interface abstrata
│   ├── semgrep_parser.py         # Semgrep JSON → Vulnerability
│   ├── zap_parser.py             # ZAP JSON/XML → Vulnerability
│   ├── snyk_parser.py            # Snyk JSON → Vulnerability
│   ├── gitleaks_parser.py        # Gitleaks JSON → Vulnerability
│   └── trivy_parser.py           # Trivy JSON → Vulnerability (Container/IaC/Secrets)
├── scanners/
│   ├── base_scanner.py           # Interface abstrata
│   ├── trivy_scanner.py          # Executa o Trivy internamente
│   ├── semgrep_scanner.py        # Executa o Semgrep internamente
│   └── gitleaks_scanner.py       # Executa o Gitleaks internamente
├── ai/
│   ├── provider.py                # Abstração de LLM (Ollama local ou Groq)
│   ├── explainer.py               # Explica vulnerabilidades / resumo executivo
│   ├── prioritizer.py             # Priorização (heurística com breakdown + LLM)
│   └── anomaly_detector.py        # Padrões, hotspots e correlações
├── ui/
│   ├── main_window.py             # QMainWindow principal (sidebar + views)
│   ├── theme.py                   # Paleta de cores central da UI
│   ├── icons.py                   # Ícones vetoriais via QPainter
│   ├── charts.py                  # Gráficos via QPainter (sem libs externas)
│   ├── easter_eggs.py             # easter eggs escondidos
│   ├── dialogs/
│   │   └── settings_dialog.py     # Diálogo de Configurações (Groq API Key)
│   ├── widgets/
│   │   ├── ai_results.py          # Cards estruturados de Priorização, Anomalias e Attack Path
│   │   └── view_header.py         # Cabeçalho padrão compartilhado entre views
│   └── views/
│       ├── dashboard_view.py
│       ├── findings_view.py
│       ├── ai_view.py
│       ├── attack_path_view.py
│       ├── assets_view.py
│       └── context_view.py        # Formulário do Contexto da Empresa
├── packaging/                    # Geração de instalador Windows (.exe)
│   ├── build_exe.bat
│   ├── installer.iss
│   └── INSTALACAO.md
├── assets/                       # Ícone do app (.ico / .png)
├── data/
│   └── samples/                  # JSONs de exemplo para cada ferramenta
└── utils/
```

## Requisitos
- **Python 3.9+**
- **Obrigatório**: as dependências de `requirements.txt` (inclui o PyQt6)
- **Opcional** — só necessário se for usar *"Escanear Pasta"* (scanners
  internos), cada um requer o binário correspondente instalado e disponível
  no `PATH`:
  - [Trivy](https://trivy.dev) (`trivy`)
  - [Semgrep](https://semgrep.dev) (`pip install semgrep` já coloca no PATH)
  - [Gitleaks](https://github.com/gitleaks/gitleaks) (`gitleaks`)
- **Opcional** — só necessário para a aba **Inteligência Artificial**:
  [Ollama](https://ollama.com) rodando local, **ou** uma
  [Groq API key](https://console.groq.com/keys) (gratuita).

Sem nenhum dos itens opcionais instalados/configurados, o app roda normal —
"Escanear Pasta" fica indisponível (use "Importar Relatório" no lugar) e a
priorização cai automaticamente no cálculo determinístico, sem IA.

## Como Executar
```bash
pip install -r requirements.txt
python main.py
```
Para habilitar a IA, configure a Groq API key em **Configurações** (dentro
da aba Inteligência Artificial) — ou apenas deixe o Ollama rodando local
(`ollama pull gemma3:4b`), que é detectado automaticamente.

## Como Usar
**Primeira execução:** com nenhum dado importado ainda, o Dashboard mostra um
checklist de primeiros passos em vez de um painel zerado — siga a ordem
abaixo:

1. **(Opcional, recomendado) Preencha o Contexto da Empresa** — setor, porte,
   prioridades de negócio (disponibilidade/confidencialidade/integridade),
   dados sensíveis e infraestrutura. Melhora o score e entra no prompt da IA.
2. **(Opcional) Cadastre os Ativos** — aplicações/serviços da empresa, com
   ambiente, exposição à internet e criticidade. Habilita a aba **Attack
   Path** e refina a priorização por sistema.
3. **Traga os findings**, de duas formas (pode combinar as duas):
   - **"Escanear Pasta"** — roda Trivy/Semgrep/Gitleaks direto contra um
     projeto local (precisa dos binários no PATH, ver Requisitos acima).
   - **"Importar Relatório"** — carrega um relatório já gerado por qualquer
     uma das 5 ferramentas suportadas (Semgrep, ZAP, Snyk, Gitleaks ou
     Trivy), ou use os exemplos prontos em `data/samples/` pra testar sem
     precisar rodar nenhuma ferramenta de verdade. O formato é detectado
     automaticamente.
4. **Veja o Dashboard** — o score de postura é recalculado em tempo real, com
   a distribuição de achados por ferramenta e por tipo de scan, e anéis de
   risco em 3 estados (sem cobertura / coberto e limpo / coberto com risco).
5. **Explore os Findings** — busque por título/CVE, ordene clicando nas
   colunas, filtre por severidade/ferramenta/status/ativo, e vincule cada
   finding a um ativo cadastrado.
6. **Use a Inteligência Artificial** (configure a chave em Configurações,
   dentro da própria aba): explique uma vulnerabilidade específica em
   linguagem simples, rode a priorização com o breakdown do score, ou
   detecte padrões e anomalias no conjunto importado.
7. **Consulte o Attack Path** — cruza os findings com o contexto dos ativos
   pra montar cadeias de risco (exposição → vulnerabilidade → impacto).
   Determinístico, não depende de IA nem de nenhuma etapa anterior além do
   cadastro de ativos.

## Gerar Instalador Windows (.exe)
Veja `packaging/INSTALACAO.md` — transforma o projeto em um
`SentinelAI_Setup.exe` que instala sem precisar de Python nem pip na máquina
do usuário final.
