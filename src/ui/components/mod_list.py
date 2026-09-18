"""
Lista lateral de mods em formato de cards compactos.
Exibe: ícone placeholder, nome, status badge, downloads e seleção.
Ordenação padrão: por popularidade (total_downloads desc).
"""

import tkinter as tk
import customtkinter as ctk
from typing import List, Callable, Optional
from src.core.models import ModItem, UpdateStatus


SORT_OPTIONS = {
    "Popularidade (↓)": lambda m: -m.total_downloads,
    "Popularidade (↑)": lambda m: m.total_downloads,
    "Nome (A-Z)":       lambda m: m.name.lower(),
    "Atualizações":     lambda m: (0 if m.status in (UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATE_AVAILABLE) else 1),
    "Status":           lambda m: m.status.value,
}

STATUS_FILTER_OPTIONS = [
    "Todos",
    "Com Atualização",
    "Confirmados TLauncher",
    "Em Dia",
    "Não Encontrado",
    "Aplicados",
]

STATUS_FILTER_MAP = {
    "Todos":                  None,
    "Com Atualização":        {UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED},
    "Confirmados TLauncher":  {UpdateStatus.TLAUNCHER_CONFIRMED},
    "Em Dia":                 {UpdateStatus.UP_TO_DATE},
    "Não Encontrado":         {UpdateStatus.NOT_FOUND},
    "Aplicados":              {UpdateStatus.UPDATED},
}


class ModCard(ctk.CTkFrame):
    """Card compacto de um mod na lista lateral."""

    SELECTED_BG    = "#1c3a5e"
    UNSELECTED_EVEN = "#1e2025"
    UNSELECTED_ODD  = "#252830"

    def __init__(
        self,
        master,
        mod: ModItem,
        row_index: int,
        on_click: Callable[[ModItem], None],
        on_check: Callable[[ModItem], None],
        **kwargs,
    ):
        bg = self.UNSELECTED_EVEN if row_index % 2 == 0 else self.UNSELECTED_ODD
        super().__init__(master, corner_radius=6, fg_color=bg, **kwargs)
        self.mod = mod
        self.row_index = row_index
        self.on_click = on_click
        self.on_check = on_check
        self._bg = bg
        self._selected_as_card = False

        self.grid_columnconfigure(1, weight=1)
        self._build()
        self.bind("<Button-1>", self._handle_click)

    def _build(self):
        # ---- Checkbox de atualização ----
        self.var_chk = tk.BooleanVar(value=self.mod.selected)
        self.chk = ctk.CTkCheckBox(self, text="", variable=self.var_chk, width=20, command=self._on_chk)
        self.chk.grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=8, sticky="w")
        can_select = self.mod.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")

        # ---- Ícone placeholder ----
        self.icon_lbl = ctk.CTkLabel(
            self, text="📦", font=ctk.CTkFont(size=20), width=32, anchor="center"
        )
        self.icon_lbl.grid(row=0, column=1, rowspan=2, padx=(2, 8), pady=6, sticky="w")
        self.icon_lbl.bind("<Button-1>", self._handle_click)

        # ---- Nome ----
        self.lbl_name = ctk.CTkLabel(
            self, text=self.mod.name, font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", wraplength=170
        )
        self.lbl_name.grid(row=0, column=2, padx=4, pady=(8, 1), sticky="w")
        self.lbl_name.bind("<Button-1>", self._handle_click)

        # ---- Downloads ----
        dl_text = f"⬇ {self.mod.downloads_display}" if self.mod.total_downloads > 0 else "⬇ —"
        self.lbl_dl = ctk.CTkLabel(
            self, text=dl_text, font=ctk.CTkFont(size=10),
            text_color="#6e7681", anchor="w"
        )
        self.lbl_dl.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="w")
        self.lbl_dl.bind("<Button-1>", self._handle_click)

        # ---- Badge de status ----
        self.badge = ctk.CTkLabel(
            self,
            text=self.mod.status.label,
            fg_color=self.mod.status.color,
            text_color=self.mod.status.text_color,
            corner_radius=4,
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="center", width=90
        )
        self.badge.grid(row=0, column=3, rowspan=2, padx=(4, 10), pady=8, sticky="e")
        self.badge.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event=None):
        self.on_click(self.mod)

    def _on_chk(self):
        self.mod.selected = self.var_chk.get()
        self.on_check(self.mod)

    def set_card_selected(self, selected: bool):
        """Destaca o card quando selecionado no painel de detalhes."""
        self._selected_as_card = selected
        new_bg = self.SELECTED_BG if selected else self._bg
        self.configure(fg_color=new_bg)

    def refresh(self):
        self.var_chk.set(self.mod.selected)
        self.badge.configure(text=self.mod.status.label, fg_color=self.mod.status.color)
        dl_text = f"⬇ {self.mod.downloads_display}" if self.mod.total_downloads > 0 else "⬇ —"
        self.lbl_dl.configure(text=dl_text)
        can_select = self.mod.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")


class ModList(ctk.CTkFrame):
    """
    Painel esquerdo: barra de ferramentas (busca + filtros + ordenação)
    + lista scrollável de ModCards.
    """

    def __init__(
        self,
        master,
        on_mod_selected: Callable[[ModItem], None],
        on_selection_changed: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, corner_radius=10, **kwargs)
        self.on_mod_selected = on_mod_selected
        self.on_selection_changed = on_selection_changed

        self.all_mods: List[ModItem] = []
        self.visible_mods: List[ModItem] = []
        self.cards: List[ModCard] = []
        self._active_card: Optional[ModCard] = None

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_toolbar()
        self._build_quick_actions()
        self._build_scroll()

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        bar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(bar, placeholder_text="🔎 Buscar...", height=32)
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.search.bind("<KeyRelease>", lambda _: self._refresh())

        self.sort_combo = ctk.CTkComboBox(
            bar, values=list(SORT_OPTIONS.keys()), width=155, height=32,
            command=lambda _: self._refresh()
        )
        self.sort_combo.set("Popularidade (↓)")
        self.sort_combo.grid(row=0, column=1, padx=(0, 0))

    def _build_quick_actions(self):
        qa = ctk.CTkFrame(self, fg_color="transparent")
        qa.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))

        self.filter_combo = ctk.CTkComboBox(
            qa, values=STATUS_FILTER_OPTIONS, width=160, height=28,
            command=lambda _: self._refresh()
        )
        self.filter_combo.set("Todos")
        self.filter_combo.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            qa, text="Marcar updates", height=28, width=115,
            fg_color="#d35400", hover_color="#ba4a00",
            command=self._select_all_updates
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            qa, text="Desmarcar", height=28, width=80,
            fg_color="#4a4a4a", hover_color="#383838",
            command=self._clear_selection
        ).pack(side="left")

        self.lbl_count = ctk.CTkLabel(
            qa, text="0 mods", font=ctk.CTkFont(size=11), text_color="#6e7681"
        )
        self.lbl_count.pack(side="right")

    def _build_scroll(self):
        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=6, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def set_mods(self, mods: List[ModItem]):
        self.all_mods = mods
        self._card_index: dict = {}  # mod.id -> ModCard
        self._refresh()

    def set_all_checking(self, mods_to_check: List[ModItem]):
        """Marca todos os mods da lista como CHECKING para feedback imediato."""
        ids = {m.id for m in mods_to_check}
        for card in self.cards:
            if card.mod.id in ids:
                card.mod.status = UpdateStatus.CHECKING
                card.refresh()

    def refresh_card_for_mod(self, mod: ModItem):
        """
        Atualiza APENAS o card do mod especificado.
        O(1) via _card_index sem re-renderizar a lista.
        """
        card = self._card_index.get(mod.id)
        if card:
            card.refresh()
            # Se o detalhe aberto é este mod, sinaliza para quem escuta
            if self._active_card and self._active_card.mod.id == mod.id:
                self.on_mod_selected(mod)

    def refresh_all_cards(self):
        """Atualiza todos os cards visíveis (compatibilidade)."""
        for card in self.cards:
            card.refresh()

    def get_selected_mods(self) -> List[ModItem]:
        return [m for m in self.all_mods if m.selected]

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _refresh(self):
        query = self.search.get().strip().lower()
        status_filter_key = self.filter_combo.get()
        allowed_statuses = STATUS_FILTER_MAP.get(status_filter_key)
        sort_key = SORT_OPTIONS.get(self.sort_combo.get(), SORT_OPTIONS["Popularidade (↓)"])

        filtered = []
        for m in self.all_mods:
            if query and query not in m.name.lower() and query not in str(m.id) and query not in m.slug.lower():
                continue
            if allowed_statuses and m.status not in allowed_statuses:
                continue
            filtered.append(m)

        self.visible_mods = sorted(filtered, key=sort_key)
        self._render()

    def _render(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.cards.clear()
        self._card_index = {}
        self._active_card = None

        if not self.visible_mods:
            ctk.CTkLabel(
                self.scroll, text="Nenhum mod encontrado.",
                text_color="#6e7681", font=ctk.CTkFont(size=12)
            ).pack(pady=30)
            self.lbl_count.configure(text="0 mods")
            return

        for idx, mod in enumerate(self.visible_mods):
            card = ModCard(
                self.scroll, mod=mod, row_index=idx,
                on_click=self._on_card_click,
                on_check=lambda _: self.on_selection_changed()
            )
            card.pack(fill="x", padx=2, pady=2)
            self.cards.append(card)
            self._card_index[mod.id] = card  # registro rápido

        self.lbl_count.configure(text=f"{len(self.visible_mods)} mods")

    def _on_card_click(self, mod: ModItem):
        # Destaca o card clicado
        for card in self.cards:
            card.set_card_selected(card.mod is mod)
            if card.mod is mod:
                self._active_card = card
        self.on_mod_selected(mod)

    def _select_all_updates(self):
        for m in self.all_mods:
            if m.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED):
                m.selected = True
        self._refresh()
        self.on_selection_changed()

    def _clear_selection(self):
        for m in self.all_mods:
            m.selected = False
        self._refresh()
        self.on_selection_changed()
