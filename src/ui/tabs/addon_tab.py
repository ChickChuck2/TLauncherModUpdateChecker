"""
Aba completa de Resource Packs e Shader Packs.
Layout master-detail: lista esquerda (cards) + painel de detalhes direito.
"""

import threading
import tkinter.messagebox as messagebox
import customtkinter as ctk
from typing import List, Optional, Callable

from src.core.models import AddonType, AddonUpdateStatus
from src.core.addon_models import AddonItem
from src.services.addon_service import AddonScannerService, AddonUpdateService
from src.services.addon_updater_service import AddonUpdaterService
from src.ui.components.addon_list import AddonList
from src.ui.components.addon_detail_panel import AddonDetailPanel


class AddonTab(ctk.CTkFrame):
    """
    Aba unificada para Resource Packs e Shader Packs.
    Possui sub-abas internas para alternar entre os dois tipos.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.json_path: Optional[str] = None
        self.game_version: str = "1.20.1"
        self.is_checking: bool = False

        # Estado por tipo de addon
        self._addons: dict = {
            AddonType.RESOURCE_PACK: [],
            AddonType.SHADER_PACK: [],
        }
        self._current_type: AddonType = AddonType.RESOURCE_PACK

        self._build_toolbar()
        self._build_sub_tabs()

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bar.grid_columnconfigure(2, weight=1)

        # Selector de tipo
        self.type_tab = ctk.CTkSegmentedButton(
            bar,
            values=["🎨 Resource Packs", "✨ Shader Packs"],
            command=self._on_type_switch,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
        )
        self.type_tab.set("🎨 Resource Packs")
        self.type_tab.grid(row=0, column=0, padx=12, pady=10)

        # Botão verificar atualizações
        self.btn_check = ctk.CTkButton(
            bar, text="🔍 Verificar Atualizações",
            height=34, width=180,
            fg_color="#1f618d", hover_color="#196090",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_check,
        )
        self.btn_check.grid(row=0, column=1, padx=(0, 6), pady=10)

        # Botão aplicar selecionados
        self.btn_apply = ctk.CTkButton(
            bar, text="⚡ Aplicar Selecionados",
            height=34, width=170,
            fg_color="#117a65", hover_color="#0e6655",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_apply_all,
        )
        self.btn_apply.grid(row=0, column=3, padx=(0, 12), pady=10)

        # Aviso de preservação
        ctk.CTkLabel(
            bar,
            text="🔒 Estado ativo/inativo preservado ao atualizar",
            font=ctk.CTkFont(size=10), text_color="#3a9a5c"
        ).grid(row=0, column=2, padx=4)

        # Status e progresso
        self.lbl_status = ctk.CTkLabel(
            bar, text="", font=ctk.CTkFont(size=11), text_color="#6e7681"
        )
        self.lbl_status.grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 6))

        self.progress = ctk.CTkProgressBar(bar, height=6, corner_radius=3)
        self.progress.set(0)
        self.progress.grid(row=2, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 10))

    def _build_sub_tabs(self):
        """Cria o layout master-detail compartilhado entre RP e SP."""
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=5)

        self.addon_list = AddonList(
            content,
            on_addon_selected=self._on_addon_selected,
            on_selection_changed=self._on_selection_changed,
        )
        self.addon_list.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.detail_panel = AddonDetailPanel(
            content,
            on_apply_single=self._on_apply_single,
        )
        self.detail_panel.grid(row=0, column=1, sticky="nsew")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def load(self, json_path: str, game_version: str):
        """Carrega resource packs e shader packs do JSON do modpack."""
        self.json_path = json_path
        self.game_version = game_version

        for addon_type in AddonType:
            self._addons[addon_type] = AddonScannerService.parse_addons(json_path, addon_type)

        self._refresh_list()
        self.detail_panel.clear()
        self.progress.set(0)
        self.lbl_status.configure(text=self._summary_text())

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    def _on_type_switch(self, value: str):
        self._current_type = (
            AddonType.RESOURCE_PACK if "Resource" in value else AddonType.SHADER_PACK
        )
        self._refresh_list()
        self.detail_panel.clear()

    def _on_addon_selected(self, addon: AddonItem):
        self.detail_panel.show_addon(addon)

    def _on_selection_changed(self):
        pass  # futuro: atualizar contador

    def _on_check(self):
        if not self.json_path or self.is_checking:
            return

        current_addons = self._addons[self._current_type]
        checkable = [a for a in current_addons if a.is_official]
        if not checkable:
            self.lbl_status.configure(text="Nenhum addon oficial para verificar nesta lista.")
            return

        self.is_checking = True
        self.btn_check.configure(state="disabled")
        self.btn_apply.configure(state="disabled")
        self.progress.set(0)
        self.lbl_status.configure(text="Iniciando verificação...")

        threading.Thread(
            target=self._check_thread,
            args=(checkable,),
            daemon=True
        ).start()

    def _check_thread(self, addons: List[AddonItem]):
        total = len(addons)

        def on_progress(current: int, _total: int, addon: AddonItem):
            try:
                if self.winfo_exists():
                    self.after(0, self._on_progress_tick, current, total, addon)
            except Exception:
                pass

        AddonUpdateService.check_all_addons(
            addons=addons,
            game_version=self.game_version,
            progress_callback=on_progress,
            max_workers=6,
        )
        try:
            if self.winfo_exists():
                self.after(0, self._check_done)
        except Exception:
            pass

    def _on_progress_tick(self, current: int, total: int, addon: AddonItem):
        try:
            if not self.winfo_exists():
                return
            self.progress.set(current / total)
            self.lbl_status.configure(text=f"Verificando: {addon.name}")
            self.addon_list.refresh_cards()
            if self.detail_panel.current_addon and self.detail_panel.current_addon.id == addon.id:
                self.detail_panel.show_addon(addon)
        except Exception:
            pass

    def _check_done(self):
        try:
            if not self.winfo_exists():
                return
            self.is_checking = False
            self.btn_check.configure(state="normal")
            self.btn_apply.configure(state="normal")
            self.progress.set(1)
            self.addon_list.refresh_cards()
            self.lbl_status.configure(text=self._summary_text())
        except Exception:
            pass

    def _on_apply_all(self):
        selected = self.addon_list.get_selected()
        if not selected:
            messagebox.showwarning(
                "Nenhum addon selecionado",
                "Marque ao menos um addon com atualização disponível."
            )
            return
        self._apply(selected)

    def _on_apply_single(self, addon: AddonItem):
        self._apply([addon])

    def _apply(self, addons: List[AddonItem]):
        if not self.json_path:
            return

        type_label = self._current_type.label
        confirm = messagebox.askyesno(
            "Confirmar Atualização",
            f"Atualizar {len(addons)} {type_label}(s) no JSON?\n\n"
            "✅ O estado Ativo/Inativo de cada addon será PRESERVADO.\n"
            "📦 Backup .bak criado automaticamente.\n"
            "🎮 O TLauncher realizará o download ao iniciar."
        )
        if not confirm:
            return

        success, errors, msg = AddonUpdaterService.apply_updates(
            json_path=self.json_path,
            addons_to_update=addons,
        )

        if success > 0:
            messagebox.showinfo("Concluído", msg)
        else:
            messagebox.showerror("Erro", msg)

        self.addon_list.refresh_cards()
        self.lbl_status.configure(text=self._summary_text())
        if self.detail_panel.current_addon:
            self.detail_panel.show_addon(self.detail_panel.current_addon)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _refresh_list(self):
        self.addon_list.set_addons(self._addons[self._current_type])

    def _summary_text(self) -> str:
        addons = self._addons[self._current_type]
        total = len(addons)
        updates = sum(
            1 for a in addons
            if a.status in (AddonUpdateStatus.UPDATE_AVAILABLE, AddonUpdateStatus.TLAUNCHER_OK)
        )
        active = sum(1 for a in addons if a.is_active)
        label = self._current_type.label
        if updates:
            return f"{label}s: {total} total · {active} ativos · {updates} com atualização disponível"
        return f"{label}s: {total} total · {active} ativos"
