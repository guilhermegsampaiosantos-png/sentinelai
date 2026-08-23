"""
ui/theme.py
Paleta central de cores da SentinelAI — usada por toda a UI.

Objetivo: sair do combo genérico "dark tipo GitHub + verde neon em tudo"
e ter hierarquia de cor de verdade:
  - ACCENT (azul)     -> ações primárias / marca
  - AI_ACCENT (roxo)  -> tudo que é IA (visualmente distinto de ações comuns)
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
TEXT_FAINT   = "#5c6785"

# Marca / ações primárias (azul — substitui o verde neon usado em tudo)
ACCENT         = "#4f8dff"
ACCENT_HOVER   = "#6ea1ff"
ACCENT_PRESSED = "#3b74e0"
ACCENT_ON      = "#071022"  # texto sobre fundo ACCENT

# IA (verde — diferencia visualmente ações de IA das ações comuns)
AI_ACCENT         = "#1fbf75"
AI_ACCENT_HOVER   = "#3fd48c"
AI_ACCENT_PRESSED = "#17a863"
AI_ACCENT_ON      = "#052013"

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
