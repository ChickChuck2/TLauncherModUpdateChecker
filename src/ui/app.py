"""
Janela Principal — Layout com Abas
  Aba 1: Mods (Master-Detail)
  Aba 2: Resource Packs & Shader Packs
"""

import threading
import tkinter.messagebox as messagebox
import customtkinter as ctk
from typing import List, Optional

from src.core.models import ModpackInfo, ModItem, UpdateStatus
from src.services.scanner_service import ScannerService
from src.services.update_service import UpdateService
from src.services.json_updater_service import JsonUpdaterService
from src.ui.components.pack_selector import PackSelector
from src.ui.components.progress_panel import ProgressPanel
from src.ui.components.mod_list import ModList
from src.ui.components.detail_panel import DetailPanel
from src.ui.components.drag_export_card import DragExportCard
from src.ui.tabs.addon_tab import AddonTab


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TLauncher Mod Update Checker")
        self.geometry("1280x800")
        self.minsize(1100, 660)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.current_modpack: Optional[ModpackInfo] = None
        self.is_checking: bool = False

        self._build_header()
        self._build_main()
        self._load_modpacks()

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#0d1117", height=56, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⚡ TLauncher Mod Checker",
            font=ctk.CTkFont(size=17, weight="bold"), text_color="#58a6ff"
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            header,
            text="Sincronização via JSON · Download oficial pelo TLauncher",
            font=ctk.CTkFont(size=11), text_color="#6e7681"
        ).pack(side="left", padx=4)

        # Contador de selecionados (canto direito)
        self.lbl_selected = ctk.CTkLabel(
            header, text="0 selecionados",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#f0883e"
        )
        self.lbl_selected.pack(side="right", padx=20)

    def _build_main(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # ---- Barra superior: seletor de pack + progresso ----
        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(0, weight=1)

        self.pack_selector = PackSelector(
            top,
            on_pack_selected=self._on_pack_selected,
            on_check_updates_clicked=self._on_check_updates,
            on_apply_updates_clicked=self._on_apply_all,
            on_refresh_packs_clicked=self._load_modpacks,
        )
        self.pack_selector.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.drag_export_card = DragExportCard(top)
        self.drag_export_card.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.progress_panel = ProgressPanel(top)
        self.progress_panel.grid(row=2, column=0, sticky="ew")

        # ---- Abas: Mods | Resource Packs & Shaders ----
        self.tabview = ctk.CTkTabview(
            outer,
            anchor="nw",
            fg_color="#161b22",
            segmented_button_fg_color="#0d1117",
            segmented_button_selected_color="#1f618d",
            segmented_button_selected_hover_color="#196090",
            segmented_button_unselected_color="#0d1117",
            segmented_button_unselected_hover_color="#1a1d20",
        )
        self.tabview.grid(row=1, column=0, sticky="nsew")

        # Aba Mods
        tab_mods = self.tabview.add("🧩  Mods")
        tab_mods.grid_rowconfigure(0, weight=1)
        tab_mods.grid_columnconfigure(0, weight=3)
        tab_mods.grid_columnconfigure(1, weight=5)

        self.mod_list = ModList(
            tab_mods,
            on_mod_selected=self._on_mod_selected,
            on_selection_changed=self._update_selected_counter,
        )
        self.mod_list.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.detail_panel = DetailPanel(
            tab_mods,
            on_apply_single=self._on_apply_single,
        )
        self.detail_panel.grid(row=0, column=1, sticky="nsew")

        # Aba Resource Packs & Shaders
        tab_addons = self.tabview.add("🎨  Resource Packs & Shaders")
        tab_addons.grid_rowconfigure(0, weight=1)
        tab_addons.grid_columnconfigure(0, weight=1)

        self.addon_tab = AddonTab(tab_addons)
        self.addon_tab.grid(row=0, column=0, sticky="nsew")


    # ------------------------------------------------------------------ #
    #  Modpack                                                             #
    # ------------------------------------------------------------------ #

    def _load_modpacks(self):
        modpacks = ScannerService.scan_modpacks()
        self.pack_selector.set_modpacks(modpacks)

    def _on_pack_selected(self, pack: ModpackInfo):
        self.current_modpack = pack
        self.drag_export_card.set_modpack(pack)
        self.mod_list.set_mods(pack.mods)
        self.detail_panel.clear()
        self.progress_panel.reset()
        self._refresh_stats()
        self._update_selected_counter()
        # Carrega Resource Packs e Shader Packs do mesmo JSON
        self.addon_tab.load(
            json_path=pack.json_path,
            game_version=pack.game_version,
        )

    # ------------------------------------------------------------------ #
    #  Mod selecionado no painel de detalhe                                #
    # ------------------------------------------------------------------ #

    def _on_mod_selected(self, mod: ModItem):
        self.detail_panel.show_mod(mod)

    # ------------------------------------------------------------------ #
    #  Verificação de atualizações                                         #
    # ------------------------------------------------------------------ #

    def _on_check_updates(self):
        if not self.current_modpack or self.is_checking:
            return

        pack = self.current_modpack
        valid = [m for m in pack.mods if m.status != UpdateStatus.LOCAL_ONLY and m.id > 0]
        if not valid:
            self.progress_panel.lbl_status.configure(text="Nenhum mod oficial para verificar.")
            return

        self.is_checking = True
        self._check_total = len(valid)
        self.pack_selector.set_buttons_enabled(False)

        # 1. Pré-marcar todos como CHECKING → feedback imediato na lista
        self.progress_panel.start_checking(self._check_total)
        self.mod_list.set_all_checking(valid)

        threading.Thread(
            target=self._run_check_thread,
            args=(pack, valid),
            daemon=True
        ).start()

    def _run_check_thread(self, pack, valid):
        def on_progress(current: int, total: int, mod: ModItem):
            self.after(0, self._on_progress_tick, current, total, mod)

        UpdateService.check_all_mods(
            mods=valid,
            game_version=pack.game_version,
            loader=pack.loader,
            progress_callback=on_progress,
            max_workers=8,
        )
        self.after(0, self._check_done)

    def _on_progress_tick(self, current: int, total: int, mod: ModItem):
        """
        Chamado a cada mod concluído — atualiza APENAS o card daquele mod
        em vez de re-renderizar a lista inteira.
        """
        # Atualiza barra e indicador do mod verificado
        self.progress_panel.tick(
            current=current,
            total=total,
            mod_name=mod.name,
            status_label=mod.status.label,
            status_color=mod.status.color,
        )

        # Atualiza só o card deste mod (O(1))
        self.mod_list.refresh_card_for_mod(mod)

        # Atualiza estatísticas (badges numéricas)
        self._refresh_stats()

        # Se o painel de detalhe exibe este mod, atualiza-o
        if self.detail_panel.current_mod and self.detail_panel.current_mod.id == mod.id:
            self.detail_panel.show_mod(mod)

    def _check_done(self):
        self.is_checking = False
        self.pack_selector.set_buttons_enabled(True)
        self._refresh_stats()

        # Re-renderiza com ordenação final (agora por popularidade com updates no topo)
        self.mod_list._refresh()

        mods = self.current_modpack.mods if self.current_modpack else []
        updates = sum(
            1 for m in mods
            if m.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED)
        )
        tlauncher_only = sum(1 for m in mods if m.status == UpdateStatus.TLAUNCHER_CONFIRMED)
        if updates:
            msg = (f"✅ {updates} mod(s) com atualização · "
                   f"{tlauncher_only} confirmados no TLauncher — prontos para aplicar!")
        else:
            msg = "✅ Todos os mods verificados estão em dia."
        self.progress_panel.done(msg)

    # ------------------------------------------------------------------ #
    #  Aplicação de atualizações                                           #
    # ------------------------------------------------------------------ #

    def _on_apply_all(self):
        selected = self.mod_list.get_selected_mods()
        if not selected:
            messagebox.showwarning("Nenhum mod selecionado",
                                   "Marque ao menos um mod com atualização disponível antes de aplicar.")
            return
        self._apply_updates(selected)

    def _on_apply_single(self, mod: ModItem):
        self._apply_updates([mod])

    def _apply_updates(self, mods_to_update: List[ModItem]):
        if not self.current_modpack:
            return

        confirm = messagebox.askyesno(
            "Confirmar alteração no JSON",
            f"Atualizar metadados de {len(mods_to_update)} mod(s) no TLauncherAdditional.json?\n\n"
            "• Backup .bak criado automaticamente.\n"
            "• Nenhum arquivo .jar será baixado pelo app.\n"
            "• O TLauncher realizará os downloads ao iniciar."
        )
        if not confirm:
            return

        success, errors, msg = JsonUpdaterService.apply_updates_to_json(
            json_path=self.current_modpack.json_path,
            mods_to_update=mods_to_update,
        )
        if success > 0:
            messagebox.showinfo("Concluído", msg)
        else:
            messagebox.showerror("Erro", msg)

        self.mod_list._refresh()
        self._refresh_stats()
        self._update_selected_counter()
        self.drag_export_card.set_modpack(self.current_modpack)
        # Refresca painel de detalhe
        if self.detail_panel.current_mod:
            self.detail_panel.show_mod(self.detail_panel.current_mod)

    # ------------------------------------------------------------------ #
    #  Stats e contadores                                                  #
    # ------------------------------------------------------------------ #

    def _refresh_stats(self):
        if not self.current_modpack:
            return
        mods = self.current_modpack.mods
        total = len(mods)
        up_to_date = sum(1 for m in mods if m.status == UpdateStatus.UP_TO_DATE)
        updates = sum(1 for m in mods if m.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED))
        tlauncher = sum(1 for m in mods if m.status == UpdateStatus.TLAUNCHER_CONFIRMED)
        self.progress_panel.update_stats(total, up_to_date, updates, tlauncher)

    def _update_selected_counter(self):
        n = len(self.mod_list.get_selected_mods())
        self.lbl_selected.configure(text=f"{n} selecionado(s)")


def run_app():
    app = MainApp()
    app.mainloop()
