"""
ui/theme.py
Paleta central de cores da SentinelAI — usada por toda a UI.

Objetivo: sair do combo genérico "dark tipo GitHub + verde neon em tudo"
e ter hierarquia de cor de verdade:
  - ACCENT (azul)     -> ações primárias / marca, inclusive as de IA — a
                         equipe decidiu manter uma cor só de ação em todo
                         o app em vez de reservar um roxo separado pra IA
  - SEV_*             -> severidade (semântico, nunca usado como decoração)
"""

# Fundos
BG_APP         = "#0a0d16"
BG_SURFACE     = "#121726"
BG_SURFACE_ALT = "#0d1120"
BG_ELEVATED    = "#1a2136"
BG_INPUT       = "#161d30"

# Bordas
BORDER        = "#242c42"
BORDER_STRONG = "#3a4562"

# Texto
TEXT_PRIMARY = "#eef1f8"
TEXT_MUTED   = "#8993ac"
# Antes #5c6785: 3.17:1 contra BG_SURFACE, abaixo do mínimo 4.5:1 da WCAG AA
# para texto normal — texto "apagado" de propósito não pode virar texto
# ilegível. #828fb0 continua mais escuro que TEXT_MUTED (mantém a
# hierarquia) mas passa de 5:1 contra todos os fundos usados (SURFACE/APP/
# ELEVATED), verificado via razão de contraste WCAG (luminância relativa).
TEXT_FAINT   = "#828fb0"

# Marca / ações primárias (azul — substitui o verde neon usado em tudo)
ACCENT         = "#4f8dff"
ACCENT_HOVER   = "#6ea1ff"
ACCENT_PRESSED = "#3b74e0"
ACCENT_ON      = "#071022"  # texto sobre fundo ACCENT

# IA — mesmo azul do ACCENT. Chegou a ser roxo (pra diferenciar ações de
# IA das ações comuns) e antes disso verde, mas a equipe preferiu manter
# uma cor de ação só no app inteiro. Os aliases continuam existindo pra
# não precisar mexer em todo ui/views/ai_view.py — só apontam pro mesmo
# valor do ACCENT agora.
AI_ACCENT         = ACCENT
AI_ACCENT_HOVER   = ACCENT_HOVER
AI_ACCENT_PRESSED = ACCENT_PRESSED
AI_ACCENT_ON      = ACCENT_ON

# Severidade / status (semântico — não usar como decoração)
SEV_CRITICAL = "#f0455c"
SEV_HIGH     = "#f2924a"
SEV_MEDIUM   = "#f0c34e"
SEV_LOW      = "#3fc38a"
SEV_INFO     = "#4f8dff"

SUCCESS = "#3fc38a"
WARNING = "#f2924a"
DANGER  = "#f0455c"

SEVERITY_COLORS = {
    "critical": SEV_CRITICAL,
    "high":     SEV_HIGH,
    "medium":   SEV_MEDIUM,
    "low":      SEV_LOW,
    "info":     SEV_INFO,
}

# Paleta categórica (tons frios) para gráficos sem significado semântico
# (ex.: distribuição por ferramenta) — não usa vermelho/laranja/amarelo/verde
# pra não ser confundida com severidade, nem o verde de IA.
CHART_PALETTE = ["#4f8dff", "#38bdf8", "#818cf8", "#94a3b8", "#60a5fa"]

SEVERITY_LABELS_PT = {
    "critical": "CRÍTICA",
    "high":     "ALTA",
    "medium":   "MÉDIA",
    "low":      "BAIXA",
    "info":     "INFO",
}


def rgba(hex_color: str, alpha: float) -> str:
    """Converte #RRGGBB + alpha (0-1) para rgba(r,g,b,a) — formato que o Qt
    entende sem a pegadinha do #AARRGGBB."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def button_style(bg: str, hover: str, pressed: str, fg: str = ACCENT_ON,
                  radius: int = 8, outline: bool = False) -> str:
    """Gera QSS de botão consistente. outline=True -> botão com apenas borda,
    fundo transparente (usado para ações secundárias)."""
    if outline:
        return f"""
            QPushButton {{
                background: transparent; color: {bg};
                border: 1px solid {bg}; border-radius: {radius}px;
                padding: 0 16px; font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover {{ background: {rgba(bg, 0.12)}; color: {hover}; border-color: {hover}; }}
            QPushButton:pressed {{ background: {rgba(bg, 0.2)}; }}
            QPushButton:disabled {{ color: {TEXT_FAINT}; border-color: {BORDER}; }}
        """
    return f"""
        QPushButton {{
            background: {bg}; color: {fg};
            border: none; border-radius: {radius}px;
            padding: 0 16px; font-weight: 600; font-size: 13px;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: {pressed}; }}
        QPushButton:disabled {{ background: {BORDER}; color: {TEXT_FAINT}; }}
    """
