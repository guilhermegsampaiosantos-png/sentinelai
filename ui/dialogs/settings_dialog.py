"""
ui/dialogs/settings_dialog.py
Diálogo de Configurações — hoje só a Groq API Key (P2 #15 da revisão de
UX: antes esse campo morava dentro da aba de IA, no meio da tela de
trabalho, e não era salvo em lugar nenhum).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PyQt6.QtCore import Qt

from core import settings as settings_store
from ui import theme
from ui.icons import icon


class SettingsDialog(QDialog):
    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.setWindowTitle("Configurações")
        self.setFixedWidth(420)
        self.setStyleSheet(f"QDialog {{ background:{theme.BG_APP}; }}")
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = QLabel("Provedor de IA")
        title.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; font-size:14px; font-weight:bold;")
        lay.addWidget(title)

        self.status_icon = QLabel()
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"font-size:11px; font-family:monospace;")
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        lay.addLayout(status_row)
        self._refresh_status()

        info = QLabel(
            "A SentinelAI usa Ollama local automaticamente quando disponível. "
            "Sem Ollama, configure uma Groq API Key abaixo (gratuita em "
            "console.groq.com)."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{theme.TEXT_MUTED}; font-size:11px;")
        lay.addWidget(info)

        lbl = QLabel("Groq API Key:")
        lbl.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; font-size:12px;")
        lay.addWidget(lbl)

        current = settings_store.load()
        self.key_input = QLineEdit(current.groq_api_key)
        self.key_input.setPlaceholderText("gsk_...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                background:{theme.BG_INPUT}; border:1px solid {theme.BORDER}; border-radius:6px;
                color:{theme.TEXT_PRIMARY}; padding:6px 10px; font-size:12px;
            }}
        """)
        lay.addWidget(self.key_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(32)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{theme.TEXT_MUTED};
                border:1px solid {theme.BORDER}; border-radius:6px; padding:0 14px; font-size:12px; }}
            QPushButton:hover {{ color:{theme.TEXT_PRIMARY}; border-color:{theme.BORDER_STRONG}; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton(" Salvar")
        btn_save.setIcon(icon("save", theme.ACCENT_ON, 14))
        btn_save.setFixedHeight(32)
        btn_save.setStyleSheet(theme.button_style(theme.ACCENT, theme.ACCENT_HOVER, theme.ACCENT_PRESSED))
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        lay.addLayout(btn_row)

    def _refresh_status(self):
        if self.provider.available:
            self.status_icon.setPixmap(icon("check", theme.SUCCESS, 14).pixmap(14, 14))
            self.status_label.setText(f"IA ativa — backend: {self.provider.backend_name.upper()}")
            self.status_label.setStyleSheet(f"color:{theme.SUCCESS}; font-size:11px; font-family:monospace;")
        else:
            self.status_icon.setPixmap(icon("x", theme.DANGER, 14).pixmap(14, 14))
            self.status_label.setText("IA indisponível — configure Ollama ou uma Groq API Key")
            self.status_label.setStyleSheet(f"color:{theme.DANGER}; font-size:11px; font-family:monospace;")

    def _save(self):
        key = self.key_input.text().strip()
        settings_store.save(settings_store.AppSettings(groq_api_key=key))
        if key:
            self.provider.set_groq_key(key)
        self._refresh_status()
        self.accept()
