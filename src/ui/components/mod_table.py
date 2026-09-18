"""
Componente de Tabela e Lista de Mods com Busca, Filtros e Seleção.
"""

import customtkinter as ctk
from typing import List, Callable, Optional
from src.core.models import ModItem, UpdateStatus

class ModRow(ctk.CTkFrame):
    def __init__(self, master, mod: ModItem, on_toggle: Callable[[ModItem], None], **kwargs):
        super().__init__(master, corner_radius=6, **kwargs)
        self.mod = mod
        self.on_toggle = on_toggle

        self.grid_columnconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self):
        # 1. Checkbox de Seleção
        self.var_selected = ctk.BooleanVar(value=self.mod.selected)
        self.chk = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.var_selected,
            width=24,
            command=self._on_check_toggle
        )
        self.chk.grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        # 2. Informações do Mod (Nome e ID)
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        self.lbl_name = ctk.CTkLabel(
            info_frame,
            text=self.mod.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.lbl_name.pack(anchor="w")

        id_text = f"ID CurseForge: {self.mod.id}" if self.mod.id > 0 else "Mod Interno"
        self.lbl_id = ctk.CTkLabel(
            info_frame,
            text=f"{id_text} | Arquivo: {self.mod.installed_jar}",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            anchor="w"
        )
        self.lbl_id.pack(anchor="w")

        # 3. Comparativo de Versão
        ver_frame = ctk.CTkFrame(self, fg_color="transparent")
        ver_frame.grid(row=0, column=2, padx=12, pady=6, sticky="e")

        local_ver_text = self.mod.installed_version_name or f"File #{self.mod.installed_file_id}"
        self.lbl_local_ver = ctk.CTkLabel(
            ver_frame,
            text=f"Instalado: {local_ver_text}",
            font=ctk.CTkFont(size=11),
            text_color="#a0a0a0"
        )
        self.lbl_local_ver.pack(anchor="e")

        if self.mod.latest_version_name or self.mod.latest_file_id:
            web_ver_text = self.mod.latest_version_name or f"File #{self.mod.latest_file_id}"
            self.lbl_web_ver = ctk.CTkLabel(
                ver_frame,
                text=f"Web: {web_ver_text}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#3498db"
            )
            self.lbl_web_ver.pack(anchor="e")

        # 4. Badge de Status
        self.badge_status = ctk.CTkLabel(
            self,
            text=self.mod.status.label,
            fg_color=self.mod.status.color,
            text_color="#ffffff",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=10,
            pady=4,
            width=140
        )
        self.badge_status.grid(row=0, column=3, padx=(10, 14), pady=8, sticky="e")

    def _on_check_toggle(self):
        self.mod.selected = self.var_selected.get()
        self.on_toggle(self.mod)

    def update_view(self):
        self.var_selected.set(self.mod.selected)
        self.badge_status.configure(
            text=self.mod.status.label,
            fg_color=self.mod.status.color
        )
        # Habilita ou desabilita o checkbox com base na possibilidade de atualizar
        can_update = self.mod.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED)
        if not can_update and self.mod.status != UpdateStatus.UPDATED:
            self.chk.configure(state="disabled")
        else:
            self.chk.configure(state="normal")


class ModTable(ctk.CTkFrame):
    def __init__(self, master, on_selection_changed: Callable[[], None], **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.on_selection_changed = on_selection_changed
        self.all_mods: List[ModItem] = []
        self.filtered_mods: List[ModItem] = []
        self.row_widgets: List[ModRow] = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_toolbar()
        self._create_scroll_area()

    def _create_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)

        # Campo de busca
        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="🔎 Buscar mod por nome ou ID...",
            width=260
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.search_entry.bind("<KeyRelease>", lambda e: self.apply_filter())

        # Filtro de Status
        self.combo_filter = ctk.CTkComboBox(
            toolbar,
            values=["Todos os Mods", "Apenas c/ Atualizações", "Confirmados TLauncher", "Já Atualizados"],
            command=lambda v: self.apply_filter(),
            width=200
        )
        self.combo_filter.grid(row=0, column=1, padx=4, sticky="w")

        # Botões de Seleção Rápida
        self.btn_select_all_updates = ctk.CTkButton(
            toolbar,
            text="Marcar Todos com Update",
            width=160,
            command=self._select_all_updates,
            fg_color="#d35400",
            hover_color="#ba4a00"
        )
        self.btn_select_all_updates.grid(row=0, column=2, padx=4, sticky="e")

        self.btn_clear_selection = ctk.CTkButton(
            toolbar,
            text="Desmarcar",
            width=90,
            command=self._clear_selection,
            fg_color="#7f8c8d",
            hover_color="#626567"
        )
        self.btn_clear_selection.grid(row=0, column=3, padx=(4, 0), sticky="e")

    def _create_scroll_area(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.scroll_frame.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    def set_mods(self, mods: List[ModItem]):
        self.all_mods = mods
        self.apply_filter()

    def apply_filter(self):
        query = self.search_entry.get().strip().lower()
        filter_status = self.combo_filter.get()

        self.filtered_mods = []
        for mod in self.all_mods:
            # Filtro de busca textual
            matches_query = (query in mod.name.lower()) or (str(mod.id) in query) or (query in mod.slug.lower())
            if not matches_query:
                continue

            # Filtro por tipo de status
            if filter_status == "Apenas c/ Atualizações":
                if mod.status not in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED):
                    continue
            elif filter_status == "Confirmados TLauncher":
                if mod.status != UpdateStatus.TLAUNCHER_CONFIRMED:
                    continue
            elif filter_status == "Já Atualizados":
                if mod.status != UpdateStatus.UPDATED:
                    continue

            self.filtered_mods.append(mod)

        self._render_rows()

    def _render_rows(self):
        # Limpa linhas anteriores
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.row_widgets.clear()

        if not self.filtered_mods:
            lbl_empty = ctk.CTkLabel(
                self.scroll_frame,
                text="Nenhum mod encontrado para os filtros selecionados.",
                font=ctk.CTkFont(size=13),
                text_color="#888888"
            )
            lbl_empty.pack(pady=40)
            return

        for idx, mod in enumerate(self.filtered_mods):
            bg = "#212529" if idx % 2 == 0 else "#2b3035"
            row = ModRow(
                self.scroll_frame,
                mod=mod,
                on_toggle=self._on_row_toggle,
                fg_color=bg
            )
            row.pack(fill="x", padx=4, pady=2)
            row.update_view()
            self.row_widgets.append(row)

    def _on_row_toggle(self, mod: ModItem):
        self.on_selection_changed()

    def _select_all_updates(self):
        for mod in self.all_mods:
            if mod.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED):
                mod.selected = True
        self.apply_filter()
        self.on_selection_changed()

    def _clear_selection(self):
        for mod in self.all_mods:
            mod.selected = False
        self.apply_filter()
        self.on_selection_changed()

    def get_selected_mods(self) -> List[ModItem]:
        return [m for m in self.all_mods if m.selected]

    def refresh_visible_rows(self):
        for row in self.row_widgets:
            row.update_view()
