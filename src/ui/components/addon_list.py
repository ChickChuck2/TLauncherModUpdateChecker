"""
Lista de cards de addons (Resource Packs / Shader Packs).
Ordenação padrão: popularidade desc.
"""

import tkinter as tk
import customtkinter as ctk
from typing import List, Callable, Optional

from src.core.models import AddonType, AddonUpdateStatus
from src.core.addon_models import AddonItem
from src.services.image_service import ImageService


SORT_OPTIONS = {
    "Popularidade (↓)":  lambda a: -a.popularity,
    "Downloads (↓)":     lambda a: -a.total_downloads,
    "Nome (A-Z)":        lambda a: a.name.lower(),
    "Atualizações":      lambda a: (0 if a.status in (AddonUpdateStatus.UPDATE_AVAILABLE, AddonUpdateStatus.TLAUNCHER_OK) else 1),
    "Ativos primeiro":   lambda a: (0 if a.is_active else 1),
}

FILTER_OPTIONS = ["Todos", "Ativos", "Inativos", "Com Atualização", "Em Dia", "Local"]
FILTER_MAP = {
    "Todos":           None,
    "Ativos":          lambda a: a.is_active,
    "Inativos":        lambda a: not a.is_active,
    "Com Atualização": lambda a: a.status in (AddonUpdateStatus.UPDATE_AVAILABLE, AddonUpdateStatus.TLAUNCHER_OK),
    "Em Dia":          lambda a: a.status == AddonUpdateStatus.UP_TO_DATE,
    "Local":           lambda a: a.status == AddonUpdateStatus.LOCAL_ONLY,
}


class AddonCard(ctk.CTkFrame):
    """Card compacto de um addon na lista."""

    BG_EVEN = "#1e2025"
    BG_ODD  = "#252830"
    BG_SEL  = "#1c3a5e"

    def __init__(self, master, addon: AddonItem, idx: int,
                 on_click: Callable, on_check: Callable, **kw):
        bg = self.BG_EVEN if idx % 2 == 0 else self.BG_ODD
        super().__init__(master, corner_radius=6, fg_color=bg, **kw)
        self.addon = addon
        self.idx = idx
        self._bg = bg
        self.on_click = on_click
        self.on_check = on_check
        self._icon_image = None
        self._current_icon_url: Optional[str] = None
        self.grid_columnconfigure(2, weight=1)
        self._build()
        self.bind("<Button-1>", self._click)

    def _build(self):
        # Checkbox
        self.var = tk.BooleanVar(value=self.addon.selected)
        can_select = self.addon.status in (AddonUpdateStatus.TLAUNCHER_OK, AddonUpdateStatus.UPDATED)
        self.chk = ctk.CTkCheckBox(self, text="", variable=self.var, width=20,
                                   command=self._chk_changed,
                                   state="normal" if can_select else "disabled")
        self.chk.grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=8, sticky="w")

        # Ícone (emoji por tipo ou thumbnail)
        default_icon = "🎨" if self.addon.addon_type == AddonType.RESOURCE_PACK else "✨"
        self.icon_lbl = ctk.CTkLabel(
            self, text=default_icon, font=ctk.CTkFont(size=18), width=28, height=28, anchor="center"
        )
        self.icon_lbl.grid(row=0, column=1, rowspan=2, padx=(2, 8), pady=6, sticky="w")
        self.icon_lbl.bind("<Button-1>", self._click)
        self._load_icon()

        # Nome
        self.lbl_name = ctk.CTkLabel(self, text=self.addon.name,
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     anchor="w", wraplength=165)
        self.lbl_name.grid(row=0, column=2, padx=4, pady=(8, 1), sticky="w")
        self.lbl_name.bind("<Button-1>", self._click)

        # Info secundária: ativo + downloads
        info = self.addon.active_label
        if self.addon.total_downloads > 0:
            info += f"  ⬇ {self.addon.downloads_display}"
        self.lbl_info = ctk.CTkLabel(self, text=info,
                                     font=ctk.CTkFont(size=10), text_color="#6e7681", anchor="w")
        self.lbl_info.grid(row=1, column=2, padx=4, pady=(0, 8), sticky="w")
        self.lbl_info.bind("<Button-1>", self._click)

        # Badge de status
        self.badge = ctk.CTkLabel(
            self, text=self.addon.status.label,
            fg_color=self.addon.status.color, text_color="#ffffff",
            corner_radius=4, font=ctk.CTkFont(size=9, weight="bold"),
            anchor="center", width=88
        )
        self.badge.grid(row=0, column=3, rowspan=2, padx=(4, 10), pady=8, sticky="e")
        self.badge.bind("<Button-1>", self._click)

    def bind_addon(self, addon: AddonItem, idx: int):
        """Atualiza os dados de um card existente sem recriar widgets (pooling)."""
        self.addon = addon
        self.idx = idx
        self._bg = self.BG_EVEN if idx % 2 == 0 else self.BG_ODD
        self.configure(fg_color=self._bg)

        self.var.set(self.addon.selected)
        can_select = self.addon.status in (AddonUpdateStatus.TLAUNCHER_OK, AddonUpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")

        self.lbl_name.configure(text=self.addon.name)

        info = self.addon.active_label
        if self.addon.total_downloads > 0:
            info += f"  ⬇ {self.addon.downloads_display}"
        self.lbl_info.configure(text=info)

        self.badge.configure(
            text=self.addon.status.label,
            fg_color=self.addon.status.color
        )
        self._load_icon()

    def _load_icon(self):
        default_icon = "🎨" if self.addon.addon_type == AddonType.RESOURCE_PACK else "✨"
        if not self.addon.icon_url:
            self._icon_image = None
            self._current_icon_url = None
            self.icon_lbl.configure(image=None, text=default_icon)
            return
        url = self.addon.icon_url
        self._current_icon_url = url
        cached = ImageService.get_sync(url, (28, 28))
        if cached:
            self._apply_icon(cached, url)
        else:
            self._icon_image = None
            self.icon_lbl.configure(image=None, text=default_icon)
            ImageService.get_async(url, (28, 28), lambda img, u=url: self._apply_icon(img, u), root=self)

    def _apply_icon(self, img, requested_url: Optional[str] = None):
        if requested_url is not None and requested_url != getattr(self, "_current_icon_url", None):
            return
        if img and self.winfo_exists():
            self._icon_image = img
            self.icon_lbl.configure(image=img, text="")

    def _click(self, _e=None):
        self.on_click(self.addon)

    def _chk_changed(self):
        self.addon.selected = self.var.get()
        self.on_check()

    def set_selected(self, selected: bool):
        self.configure(fg_color=self.BG_SEL if selected else self._bg)

    def refresh(self):
        self.var.set(self.addon.selected)
        self.badge.configure(text=self.addon.status.label, fg_color=self.addon.status.color)
        info = self.addon.active_label
        if self.addon.total_downloads > 0:
            info += f"  ⬇ {self.addon.downloads_display}"
        self.lbl_info.configure(text=info)
        can_select = self.addon.status in (AddonUpdateStatus.TLAUNCHER_OK, AddonUpdateStatus.UPDATED)
        self.chk.configure(state="normal" if can_select else "disabled")
        if self.addon.icon_url and not self._icon_image:
            self._load_icon()


class AddonList(ctk.CTkFrame):
    """Painel esquerdo com toolbar + lista scrollável de AddonCards com pool de widgets e renderização progressiva."""

    CHUNK_SIZE = 35

    def __init__(self, master,
                 on_addon_selected: Callable[[AddonItem], None],
                 on_selection_changed: Callable[[], None],
                 **kw):
        super().__init__(master, corner_radius=10, **kw)
        self.on_addon_selected = on_addon_selected
        self.on_selection_changed = on_selection_changed
        self.all_addons: List[AddonItem] = []
        self.visible_addons: List[AddonItem] = []
        self.cards: List[AddonCard] = []
        self._card_pool: List[AddonCard] = []
        self._card_index: dict = {}
        self._active_card: Optional[AddonCard] = None
        self._empty_label: Optional[ctk.CTkLabel] = None
        self._render_job: Optional[str] = None
        self._search_timer: Optional[str] = None

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_toolbar()
        self._build_actions()
        self._build_scroll()

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        bar.grid_columnconfigure(0, weight=1)

        self.search = ctk.CTkEntry(bar, placeholder_text="🔎 Buscar...", height=32)
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.search.bind("<KeyRelease>", self._on_search_key)
        self.search.bind("<Return>", lambda _: self._refresh())

        self.sort_combo = ctk.CTkComboBox(
            bar, values=list(SORT_OPTIONS.keys()), width=140, height=32,
            command=lambda _: self._refresh()
        )
        self.sort_combo.set("Popularidade (↓)")
        self.sort_combo.grid(row=0, column=1)

    def _build_actions(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))

        self.filter_combo = ctk.CTkComboBox(
            row, values=FILTER_OPTIONS, width=140, height=28,
            command=lambda _: self._refresh()
        )
        self.filter_combo.set("Todos")
        self.filter_combo.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row, text="Marcar updates", height=28, width=105,
            fg_color="#d35400", hover_color="#ba4a00",
            command=self._select_updates
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            row, text="Desmarcar", height=28, width=80,
            fg_color="#4a4a4a", hover_color="#383838",
            command=self._clear
        ).pack(side="left")

        self.lbl_count = ctk.CTkLabel(row, text="0", font=ctk.CTkFont(size=11),
                                      text_color="#6e7681")
        self.lbl_count.pack(side="right")

    def _build_scroll(self):
        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=6, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll.grid_columnconfigure(0, weight=1)

    # --- Public ---

    def set_addons(self, addons: List[AddonItem]):
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
        self.all_addons = addons
        self._card_index = {}
        self._refresh()

    def refresh_cards(self):
        for c in self.cards:
            c.refresh()

    def get_selected(self) -> List[AddonItem]:
        return [a for a in self.all_addons if a.selected]

    # --- Internal ---

    def _on_search_key(self, _e=None):
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
        flt_key = self.filter_combo.get()
        flt_fn = FILTER_MAP.get(flt_key)
        sort_fn = SORT_OPTIONS.get(self.sort_combo.get(), SORT_OPTIONS["Popularidade (↓)"])

        filtered = [
            a for a in self.all_addons
            if (not query or query in a.name.lower())
            and (flt_fn is None or flt_fn(a))
        ]
        self.visible_addons = sorted(filtered, key=sort_fn)
        self._render()

    def _render(self):
        self.cards.clear()
        self._card_index = {}
        self._active_card = None

        if not self.visible_addons:
            for c in self._card_pool:
                c.pack_forget()
            if not self._empty_label:
                self._empty_label = ctk.CTkLabel(
                    self.scroll, text="Nenhum addon encontrado.",
                    text_color="#6e7681", font=ctk.CTkFont(size=12)
                )
            self._empty_label.pack(pady=30)
            self.lbl_count.configure(text="0")
            return

        if self._empty_label and self._empty_label.winfo_ismapped():
            self._empty_label.pack_forget()

        self.lbl_count.configure(text=f"{len(self.visible_addons)}")
        self._render_chunk(start_idx=0, chunk_size=self.CHUNK_SIZE)

    def _render_chunk(self, start_idx: int, chunk_size: int = 35):
        if not self.winfo_exists():
            return

        end_idx = min(start_idx + chunk_size, len(self.visible_addons))
        for idx in range(start_idx, end_idx):
            addon = self.visible_addons[idx]
            if idx < len(self._card_pool):
                card = self._card_pool[idx]
                card.bind_addon(addon, idx)
                card.pack(fill="x", padx=2, pady=2)
            else:
                card = AddonCard(self.scroll, addon, idx, self._card_click, self.on_selection_changed)
                card.pack(fill="x", padx=2, pady=2)
                self._card_pool.append(card)
            self.cards.append(card)
            self._card_index[id(addon)] = card

        if end_idx < len(self.visible_addons):
            self._render_job = self.after(2, lambda: self._render_chunk(end_idx, chunk_size))
        else:
            self._render_job = None
            for i in range(len(self.visible_addons), len(self._card_pool)):
                self._card_pool[i].pack_forget()

    def _card_click(self, addon: AddonItem):
        for c in self.cards:
            c.set_selected(c.addon is addon)
            if c.addon is addon:
                self._active_card = c
        self.on_addon_selected(addon)

    def _select_updates(self):
        for a in self.all_addons:
            if a.status in (AddonUpdateStatus.UPDATE_AVAILABLE, AddonUpdateStatus.TLAUNCHER_OK):
                a.selected = True
        self._refresh()
        self.on_selection_changed()

    def _clear(self):
        for a in self.all_addons:
            a.selected = False
        self._refresh()
        self.on_selection_changed()
