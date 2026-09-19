"""
Componente de Seleção de Modpack e Botões de Controle.
"""

import customtkinter as ctk
from typing import Callable, List, Optional
from src.core.models import ModpackInfo
from src.services.settings_service import SettingsService

class PackSelector(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_pack_selected: Callable[[ModpackInfo], None],
        on_check_updates_clicked: Callable[[], None],
        on_apply_updates_clicked: Callable[[], None],
        on_refresh_packs_clicked: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, corner_radius=10, **kwargs)

        self.on_pack_selected = on_pack_selected
        self.on_check_updates_clicked = on_check_updates_clicked
        self.on_apply_updates_clicked = on_apply_updates_clicked
        self.on_refresh_packs_clicked = on_refresh_packs_clicked

        self.modpacks: List[ModpackInfo] = []
        self.selected_pack: Optional[ModpackInfo] = None

        self._create_widgets()

    def _create_widgets(self):
        # Grid layout
        self.grid_columnconfigure(1, weight=1)

        # Label Modpack
        self.lbl_title = ctk.CTkLabel(
            self,
            text="📦 Modpack:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_title.grid(row=0, column=0, padx=(16, 8), pady=12, sticky="w")

        # ComboBox para selecionar modpack
        self.combo_packs = ctk.CTkComboBox(
            self,
            values=["Nenhum modpack encontrado"],
            command=self._on_combo_change,
            width=260,
            font=ctk.CTkFont(size=13)
        )
        self.combo_packs.grid(row=0, column=1, padx=8, pady=12, sticky="w")

        # Detalhes do Modpack (Badge)
        self.lbl_pack_info = ctk.CTkLabel(
            self,
            text="Versão: - | Loader: - | Mods: 0",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        self.lbl_pack_info.grid(row=0, column=2, padx=12, pady=12, sticky="w")

        # Botão Atualizar Lista de Packs
        self.btn_refresh = ctk.CTkButton(
            self,
            text="🔄 Recarregar",
            width=100,
            command=self.on_refresh_packs_clicked,
            fg_color="#34495e",
            hover_color="#2c3e50"
        )
        self.btn_refresh.grid(row=0, column=3, padx=6, pady=12)

        # Botão Verificar Atualizações
        self.btn_check = ctk.CTkButton(
            self,
            text="🔍 Verificar Atualizações",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_check_updates_clicked,
            fg_color="#2980b9",
            hover_color="#1f618d"
        )
        self.btn_check.grid(row=0, column=4, padx=6, pady=12)

        # Botão Atualizar no JSON
        self.btn_apply = ctk.CTkButton(
            self,
            text="⚡ Aplicar Atualizações no JSON",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_apply_updates_clicked,
            fg_color="#27ae60",
            hover_color="#1e8449"
        )
        self.btn_apply.grid(row=0, column=5, padx=6, pady=12)

        # Botão Gerenciador de Backups
        self.btn_backups = ctk.CTkButton(
            self,
            text="🛡️ Backups",
            width=95,
            command=self._on_backups_clicked,
            fg_color="#4a5568",
            hover_color="#2d3748"
        )
        self.btn_backups.grid(row=0, column=6, padx=(6, 16), pady=12)

    def _on_backups_clicked(self):
        if not self.selected_pack:
            return
        from src.ui.components.backup_dialog import BackupManagerDialog
        BackupManagerDialog(
            self,
            modpack=self.selected_pack,
            on_restored=self.on_refresh_packs_clicked
        )

    def set_modpacks(self, modpacks: List[ModpackInfo]):
        self.modpacks = modpacks
        if not modpacks:
            self.combo_packs.configure(values=["Nenhum modpack encontrado"])
            self.combo_packs.set("Nenhum modpack encontrado")
            self.lbl_pack_info.configure(text="Nenhum modpack compatível com TLauncher")
            self.selected_pack = None
            return

        names = [f"{p.name} ({p.folder_name})" for p in modpacks]
        self.combo_packs.configure(values=names)

        # Restaura o último modpack selecionado, se disponível
        last_pack = SettingsService.get_last_modpack()
        selected_idx = 0
        if last_pack:
            for i, p in enumerate(modpacks):
                if p.folder_name == last_pack or p.name == last_pack:
                    selected_idx = i
                    break

        self.combo_packs.set(names[selected_idx])
        self._select_pack_by_index(selected_idx)

    def _on_combo_change(self, choice: str):
        idx = self.combo_packs.cget("values").index(choice)
        if 0 <= idx < len(self.modpacks):
            self._select_pack_by_index(idx)

    def _select_pack_by_index(self, index: int):
        self.selected_pack = self.modpacks[index]
        p = self.selected_pack
        info_text = f"🎮 MC: {p.game_version} | ⚙️ Loader: {p.loader.capitalize()} | 🧩 Mods: {p.total_mods}"
        self.lbl_pack_info.configure(text=info_text)
        SettingsService.set_last_modpack(p.folder_name)
        self.on_pack_selected(self.selected_pack)

    def set_buttons_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.combo_packs.configure(state=state)
        self.btn_refresh.configure(state=state)
        self.btn_check.configure(state=state)
        self.btn_apply.configure(state=state)
        self.btn_backups.configure(state=state)
