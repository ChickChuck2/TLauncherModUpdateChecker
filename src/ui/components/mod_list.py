"""
Lista lateral de mods em formato de cards compactos.
Exibe: ícone placeholder, nome, status badge, downloads e seleção.
Ordenação padrão: por popularidade (total_downloads desc).
"""

import tkinter as tk
import customtkinter as ctk
from typing import List, Callable, Optional
from src.core.models import ModItem, UpdateStatus
from src.services.image_service import ImageService


SORT_OPTIONS = {
    "Confirmados + Mais Pesados": lambda m: (
        0 if m.status == UpdateStatus.TLAUNCHER_CONFIRMED else
        (1 if m.status == UpdateStatus.UPDATE_AVAILABLE else 2),
        -(m.installed_size or 0),
        -m.total_downloads
    ),
    "Mais Pesados (Tamanho ↓)":  lambda m: -(m.installed_size or 0),
    "Mais Leves (Tamanho ↑)":    lambda m: (m.installed_size or 0),
    "Popularidade (↓)":          lambda m: -m.total_downloads,
    "Popularidade (↑)":          lambda m: m.total_downloads,
    "Confirmados + Populares":   lambda m: (
        0 if m.status == UpdateStatus.TLAUNCHER_CONFIRMED else
        (1 if m.status == UpdateStatus.UPDATE_AVAILABLE else 2),
        -m.total_downloads
    ),
    "Nome (A-Z)":                lambda m: m.name.lower(),
    "Atualizações":              lambda m: (0 if m.status in (UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATE_AVAILABLE) else 1),
    "Status":                    lambda m: m.status.value,
}

STATUS_FILTER_OPTIONS = [
    "Todos",
    "Com Atualização",
    "Confirmados TLauncher",
    "Confirmados: Pesados (5MB+)",
    "Updates: Pesados (5MB+)",
    "Mods Pesados (5MB+)",
    "Mods Muito Pesados (10MB+)",
    "Em Dia",
    "Não Encontrado",
    "Aplicados",
]

STATUS_FILTER_MAP = {
    "Todos":                       None,
    "Com Atualização":             {UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED},
    "Confirmados TLauncher":       {UpdateStatus.TLAUNCHER_CONFIRMED},
    "Confirmados: Pesados (5MB+)": lambda m: m.status == UpdateStatus.TLAUNCHER_CONFIRMED and m.is_heavy,
    "Updates: Pesados (5MB+)":     lambda m: m.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED) and m.is_heavy,
    "Mods Pesados (5MB+)":         lambda m: m.is_heavy,
    "Mods Muito Pesados (10MB+)":  lambda m: m.is_very_heavy,
    "Em Dia":                      {UpdateStatus.UP_TO_DATE},
    "Não Encontrado":              {UpdateStatus.NOT_FOUND},
    "Aplicados":                   {UpdateStatus.UPDATED},
}


class ModCard(ctk.CTkFrame):
    """Card compacto de um mod na lista lateral."""

    SELECTED_BG     = "#1c3a5e"
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
        self._icon_image = None
        self._current_icon_url: Optional[str] = None

        self.grid_columnconfigure(1, weight=1)
        self._build()
        self.bind("<Button-1>", self._handle_click)

    def _build(self):
        # ---- Checkbox de atualização ----
        self.var_chk = tk.BooleanVar(value=self.mod.selected)
        self.chk = ctk.CTkCheckBox(self, text="", variable=self.var_chk, width=20, command=self._on_chk)
        self.chk.grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=8, sticky="w")
        can_select = self.mod.status in (UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")

        # ---- Ícone / Thumbnail ----
        self.icon_lbl = ctk.CTkLabel(
            self, text="📦", font=ctk.CTkFont(size=20), width=32, height=32, anchor="center"
        )
        self.icon_lbl.grid(row=0, column=1, rowspan=2, padx=(2, 8), pady=6, sticky="w")
        self.icon_lbl.bind("<Button-1>", self._handle_click)
        self._load_icon()

        # ---- Nome ----
        self.lbl_name = ctk.CTkLabel(
            self, text=self.mod.name, font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", wraplength=170
        )
        self.lbl_name.grid(row=0, column=2, padx=4, pady=(8, 1), sticky="w")
        self.lbl_name.bind("<Button-1>", self._handle_click)

        # ---- Downloads e Tamanho ----
        sub_text, sub_color = self._subtitle_info()
        self.lbl_dl = ctk.CTkLabel(
            self, text=sub_text, font=ctk.CTkFont(size=10),
            text_color=sub_color, anchor="w"
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

    def _subtitle_info(self) -> tuple:
        parts = []
        if self.mod.total_downloads > 0:
            parts.append(f"⬇ {self.mod.downloads_display}")
        sz = self.mod.size_display
        if sz and sz != "—":
            parts.append(f"📦 {sz}")

        text = "  •  ".join(parts) if parts else (f"⬇ {self.mod.downloads_display}" if self.mod.total_downloads > 0 else "⬇ —")

        if self.mod.is_very_heavy:
            color = "#f0883e"  # Âmbar-laranja para mods muito pesados (10MB+)
        elif self.mod.is_heavy:
            color = "#e3b341"  # Dourado para mods pesados (5MB+)
        else:
            color = "#6e7681"  # Cinza padrão
        return text, color

    def bind_mod(self, mod: ModItem, row_index: int):
        """Atualiza os dados de um card existente sem recriar widgets (pooling)."""
        self.mod = mod
        self.row_index = row_index
        self._bg = self.UNSELECTED_EVEN if row_index % 2 == 0 else self.UNSELECTED_ODD
        self._selected_as_card = False
        self.configure(fg_color=self._bg)

        self.var_chk.set(self.mod.selected)
        can_select = self.mod.status in (UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")

        self.lbl_name.configure(text=self.mod.name)
        sub_text, sub_color = self._subtitle_info()
        self.lbl_dl.configure(text=sub_text, text_color=sub_color)

        self.badge.configure(
            text=self.mod.status.label,
            fg_color=self.mod.status.color,
            text_color=self.mod.status.text_color
        )
        self._load_icon()

    def _load_icon(self):
        if not self.mod.icon_url:
            self._icon_image = None
            self._current_icon_url = None
            self.icon_lbl.configure(image=None, text="📦")
            return
        url = self.mod.icon_url
        self._current_icon_url = url
        cached = ImageService.get_sync(url, (28, 28))
        if cached:
            self._apply_icon(cached, url)
        else:
            self._icon_image = None
            self.icon_lbl.configure(image=None, text="📦")
            ImageService.get_async(url, (28, 28), lambda img, u=url: self._apply_icon(img, u), root=self)

    def _apply_icon(self, img, requested_url: Optional[str] = None):
        if requested_url is not None and requested_url != getattr(self, "_current_icon_url", None):
            return
        if img and self.winfo_exists():
            self._icon_image = img
            self.icon_lbl.configure(image=img, text="")

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
        self.badge.configure(
            text=self.mod.status.label,
            fg_color=self.mod.status.color,
            text_color=self.mod.status.text_color
        )
        sub_text, sub_color = self._subtitle_info()
        self.lbl_dl.configure(text=sub_text, text_color=sub_color)
        can_select = self.mod.status in (UpdateStatus.TLAUNCHER_CONFIRMED, UpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")
        if self.mod.icon_url and not self._icon_image:
            self._load_icon()


class ModList(ctk.CTkFrame):
    """
    Painel esquerdo: barra de ferramentas (busca + filtros + ordenação)
    + lista scrollável de ModCards com pool de widgets e renderização progressiva.
    """

    CHUNK_SIZE = 35

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
        self._card_pool: List[ModCard] = []
        self._card_index: dict = {}  # mod.id -> ModCard
        self._active_card: Optional[ModCard] = None
        self._empty_label: Optional[ctk.CTkLabel] = None
        self._render_job: Optional[str] = None
        self._search_timer: Optional[str] = None

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
        self.search.bind("<KeyRelease>", self._on_search_key)
        self.search.bind("<Return>", lambda _: self._refresh())

        self.sort_combo = ctk.CTkComboBox(
            bar, values=list(SORT_OPTIONS.keys()), width=215, height=32,
            command=lambda _: self._refresh()
        )
        self.sort_combo.set("Popularidade (↓)")
        self.sort_combo.grid(row=0, column=1, padx=(0, 0))

    def _build_quick_actions(self):
        qa = ctk.CTkFrame(self, fg_color="transparent")
        qa.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))

        self.filter_combo = ctk.CTkComboBox(
            qa, values=STATUS_FILTER_OPTIONS, width=215, height=28,
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
        if self._render_job:
            try:
                self.after_cancel(self._render_job)
            except Exception:
                pass
            self._render_job = None
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None
        self.all_mods = mods
        self._card_index = {}
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

    def _on_search_key(self, _event=None):
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
        self._search_timer = self.after(150, self._refresh)

    def _refresh(self):
        self._search_timer = None
        if self._render_job:
            try:
                self.after_cancel(self._render_job)
            except Exception:
                pass
            self._render_job = None

        query = self.search.get().strip().lower()
        status_filter_key = self.filter_combo.get()
        allowed_statuses = STATUS_FILTER_MAP.get(status_filter_key)
        sort_key = SORT_OPTIONS.get(self.sort_combo.get(), SORT_OPTIONS["Popularidade (↓)"])

        filtered = []
        for m in self.all_mods:
            if query and query not in m.name.lower() and query not in str(m.id) and query not in m.slug.lower():
                continue
            if allowed_statuses is not None:
                if callable(allowed_statuses):
                    if not allowed_statuses(m):
                        continue
                elif m.status not in allowed_statuses:
                    continue
            filtered.append(m)

        self.visible_mods = sorted(filtered, key=sort_key)
        self._render()

    def _render(self):
        self.cards.clear()
        self._card_index = {}
        self._active_card = None

        if not self.visible_mods:
            for c in self._card_pool:
                c.pack_forget()
            if not self._empty_label:
                self._empty_label = ctk.CTkLabel(
                    self.scroll, text="Nenhum mod encontrado.",
                    text_color="#6e7681", font=ctk.CTkFont(size=12)
                )
            self._empty_label.pack(pady=30)
            self.lbl_count.configure(text="0 mods")
            return

        if self._empty_label and self._empty_label.winfo_ismapped():
            self._empty_label.pack_forget()

        self.lbl_count.configure(text=f"{len(self.visible_mods)} mods")
        # Inicia renderização progressiva com o primeiro lote imediato
        self._render_chunk(start_idx=0, chunk_size=self.CHUNK_SIZE)

    def _render_chunk(self, start_idx: int, chunk_size: int = 35):
        if not self.winfo_exists():
            return

        end_idx = min(start_idx + chunk_size, len(self.visible_mods))
        for idx in range(start_idx, end_idx):
            mod = self.visible_mods[idx]
            if idx < len(self._card_pool):
                card = self._card_pool[idx]
                card.bind_mod(mod, idx)
                card.pack(fill="x", padx=2, pady=2)
            else:
                card = ModCard(
                    self.scroll, mod=mod, row_index=idx,
                    on_click=self._on_card_click,
                    on_check=lambda _: self.on_selection_changed()
                )
                card.pack(fill="x", padx=2, pady=2)
                self._card_pool.append(card)
            self.cards.append(card)
            self._card_index[mod.id] = card

        if end_idx < len(self.visible_mods):
            self._render_job = self.after(2, lambda: self._render_chunk(end_idx, chunk_size))
        else:
            self._render_job = None
            # Oculta cards do pool excedentes à lista visível atual
            for i in range(len(self.visible_mods), len(self._card_pool)):
                self._card_pool[i].pack_forget()

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
