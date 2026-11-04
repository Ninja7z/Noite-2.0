from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from .audit_logger import AuditLogger
from .models import Capability, PermissionProfile
from .permission_manager import RESTRICTED_CAPABILITIES, PermissionManager

_CAPABILITY_LABELS = {
    Capability.FILE_READ: "Ler arquivos em diretórios autorizados",
    Capability.FILE_WRITE: "Criar e editar arquivos",
    Capability.FILE_DELETE: "Excluir arquivos",
    Capability.TERMINAL: "Executar comandos no terminal",
    Capability.APPLICATIONS: "Controlar aplicativos",
    Capability.NETWORK: "Acessar rede e serviços externos",
    Capability.MCP: "Chamar ferramentas MCP",
}

class SecuritySettingsDialog(QDialog):
    """Trusted, user-operated editor for the local permission policy."""

    def __init__(self, data_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Segurança e permissões")
        self.setMinimumWidth(480)
        self.manager = PermissionManager(Path(data_dir) / "security" / "permissions.json")
        self.audit = AuditLogger(Path(data_dir) / "security" / "audit.sqlite3")
        self._checks: dict[Capability, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "As permissões são aplicadas pelo núcleo, fora do modelo. "
            "O padrão inicial é Sem acesso."
        ))

        self.profile = QComboBox()
        self.profile.addItem("Sem acesso", PermissionProfile.NONE.value)
        self.profile.addItem("Acesso restrito", PermissionProfile.RESTRICTED.value)
        self.profile.addItem("Acesso total (configurável)", PermissionProfile.FULL.value)
        self.profile.setCurrentIndex(max(0, self.profile.findData(self.manager.profile.value)))
        layout.addWidget(self.profile)

        group = QGroupBox("Capacidades autorizadas")
        group_layout = QVBoxLayout(group)
        for capability, label in _CAPABILITY_LABELS.items():
            checkbox = QCheckBox(label)
            checkbox.setChecked(capability in self.manager.enabled)
            self._checks[capability] = checkbox
            group_layout.addWidget(checkbox)
        layout.addWidget(group)

        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.profile.currentIndexChanged.connect(self._update_controls)
        self._update_controls()

        history_button = QDialogButtonBox()
        self.history_button = history_button.addButton(
            "Ver histórico", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.history_button.clicked.connect(self._show_history)
        layout.addWidget(history_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _selected_profile(self) -> PermissionProfile:
        return PermissionProfile(self.profile.currentData())

    def _update_controls(self) -> None:
        profile = self._selected_profile()
        for capability, checkbox in self._checks.items():
            allowed_in_profile = (
                profile == PermissionProfile.FULL
                or (
                    profile == PermissionProfile.RESTRICTED
                    and capability in RESTRICTED_CAPABILITIES
                )
            )
            checkbox.setEnabled(allowed_in_profile)
            if not allowed_in_profile:
                checkbox.setChecked(False)
        if profile == PermissionProfile.NONE:
            self.note.setText("Nenhuma ferramenta poderá ser usada pela IA.")
        elif profile == PermissionProfile.RESTRICTED:
            self.note.setText(
                "Este perfil limita a IA à leitura e escrita controlada. "
                "Terminal, exclusão, aplicativos, rede e MCP permanecem bloqueados."
            )
        else:
            self.note.setText(
                "Marque somente as capacidades que deseja liberar. "
                "Acesso total não desativa confirmações nem o registro de auditoria."
            )

    def _save(self) -> None:
        profile = self._selected_profile()
        enabled = {cap for cap, checkbox in self._checks.items() if checkbox.isChecked()}
        try:
            self.manager.save_from_user(profile, enabled)
        except OSError as exc:
            QMessageBox.critical(self, "Falha ao salvar", str(exc))
            return
        self.accept()

    def _show_history(self) -> None:
        records = self.audit.recent(50)
        viewer = QDialog(self)
        viewer.setWindowTitle("Histórico de segurança")
        viewer.resize(760, 420)
        layout = QVBoxLayout(viewer)
        output = QPlainTextEdit()
        output.setReadOnly(True)
        if not records:
            output.setPlainText("Ainda não há operações registradas.")
        else:
            lines = []
            for row in records:
                lines.append(
                    f"{row['created_at']} | {row['decision']} | {row['risk']} | "
                    f"{row['actor']} | {row['tool']} | {row['operation']} | "
                    f"{row['resource']} | {row['execution_status']}\n{row['reason']}"
                )
            output.setPlainText("\n\n".join(lines))
        layout.addWidget(output)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(viewer.reject)
        close.accepted.connect(viewer.accept)
        layout.addWidget(close)
        viewer.exec()
