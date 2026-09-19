"""
Painel de detalhes para um AddonItem (Resource Pack ou Shader Pack).
Exibe: ícone, estado ativo, comparativo de versão, descrição, links.
"""

import threading
import webbrowser
import customtkinter as ctk
from typing import Optional

from src.core.models import AddonUpdateStatus
from src.core.addon_models import AddonItem
from src.services.image_service import ImageService
from src.services.addon_service import AddonUpdateService
from src.ui.components.rich_content_renderer import RichContentRenderer


def _open(url: str):
    try:
        webbrowser.open(url)
    except Exception:
        pass


class AddonDetailPanel(ctk.CTkFrame):
    """Painel de detalhes de um addon selecionado."""

    def __init__(self, master, on_apply_single: callable, **kw):
        super().__init__(master, corner_radius=10, **kw)
        self.on_apply_single = on_apply_single
        self.current_addon: Optional[AddonItem] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._placeholder()

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        self.header = ctk.CTkFrame(self, fg_color="#1a1d20", corner_radius=8)
        self.header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        self.header.grid_columnconfigure(1, weight=1)

        # Ícone
        self.icon_lbl = ctk.CTkLabel(
            self.header, text="🎨", font=ctk.CTkFont(size=44), width=60, anchor="center"
        )
        self.icon_lbl.grid(row=0, column=0, rowspan=4, padx=(14, 10), pady=14, sticky="w")

        # Nome
        self.lbl_name = ctk.CTkLabel(
            self.header, text="Selecione um addon",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        )
        self.lbl_name.grid(row=0, column=1, padx=0, pady=(12, 2), sticky="w")

        # Tipo
        self.lbl_type = ctk.CTkLabel(
            self.header, text="", font=ctk.CTkFont(size=11),
            text_color="#58a6ff", anchor="w"
        )
        self.lbl_type.grid(row=1, column=1, sticky="w")

        # Estado ativo — em destaque
        self.lbl_state = ctk.CTkLabel(
            self.header, text="", font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.lbl_state.grid(row=2, column=1, sticky="w")

        # Autor
        self.lbl_authors = ctk.CTkLabel(
            self.header, text="", font=ctk.CTkFont(size=11),
            text_color="#6e7681", anchor="w"
        )
        self.lbl_authors.grid(row=3, column=1, pady=(0, 12), sticky="w")

        # Ações
        right = ctk.CTkFrame(self.header, fg_color="transparent")
        right.grid(row=0, column=2, rowspan=4, padx=14, pady=10, sticky="e")

        self.badge_status = ctk.CTkLabel(
            right, text="—", fg_color="#4a4a4a", text_color="#ffffff",
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold")
        )
        self.badge_status.pack(padx=10, pady=(0, 6))

        self.btn_update = ctk.CTkButton(
            right, text="⚡ Aplicar no JSON",
            width=130, height=30,
            fg_color="#117a65", hover_color="#0e6655",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_apply,
            state="disabled"
        )
        self.btn_update.pack()

    def _build_body(self):
        self.body = ctk.CTkScrollableFrame(self, corner_radius=6, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.body.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show_addon(self, addon: AddonItem):
        self.current_addon = addon
        self._clear()
        self._render_header(addon)
        self._render_state_warning(addon)
        self._render_stats(addon)
        self._render_screenshots(addon)
        self._render_version(addon)
        self._render_description(addon)
        self._render_links(addon)

    def clear(self):
        self.current_addon = None
        self._clear()
        self._placeholder()

    # ------------------------------------------------------------------ #
    #  Render                                                              #
    # ------------------------------------------------------------------ #

    def _clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def _placeholder(self):
        self.lbl_name.configure(text="Selecione um addon na lista")
        self.lbl_type.configure(text="")
        self.lbl_state.configure(text="", text_color="#ffffff")
        self.lbl_authors.configure(text="")
        self.badge_status.configure(text="—", fg_color="#4a4a4a")
        self.btn_update.configure(state="disabled")
        self.icon_lbl.configure(text="🎨", image=None)
        self._header_img = None
        ctk.CTkLabel(
            self.body,
            text="Clique em um addon da lista para ver os detalhes aqui.",
            font=ctk.CTkFont(size=13), text_color="#6e7681", wraplength=360
        ).pack(pady=40, padx=20)

    def _render_header(self, addon: AddonItem):
        default_icon = "🎨" if addon.addon_type.label == "Resource Pack" else "✨"
        self.icon_lbl.configure(text=default_icon, image=None)
        self._header_img = None
        self.lbl_name.configure(text=addon.name)
        self.lbl_type.configure(text=f"  {addon.addon_type.label}")
        self.lbl_state.configure(
            text=f"  {addon.active_label}",
            text_color=addon.active_color
        )
        self.lbl_authors.configure(
            text=f"  ✍️ {', '.join(addon.authors)}" if addon.authors else "  Autor desconhecido"
        )
        self.badge_status.configure(text=addon.status.label, fg_color=addon.status.color)
        can = addon.status == AddonUpdateStatus.TLAUNCHER_OK
        self.btn_update.configure(state="normal" if can else "disabled")

        if addon.icon_url:
            cached = ImageService.get_sync(addon.icon_url, (56, 56))
            if cached:
                self._apply_header_icon(cached, addon)
            else:
                ImageService.get_async(
                    addon.icon_url, (56, 56),
                    lambda img, a=addon: self._apply_header_icon(img, a),
                    root=self
                )

    def _apply_header_icon(self, img, target_addon):
        if img and self.winfo_exists() and self.current_addon == target_addon:
            self._header_img = img
            self.icon_lbl.configure(image=img, text="")

    def _render_screenshots(self, addon: AddonItem):
        if not addon.screenshot_urls:
            return
        sec = self._section("📸 Imagens / Capturas de Tela")
        scroll_row = ctk.CTkScrollableFrame(sec, orientation="horizontal", height=120, fg_color="transparent")
        scroll_row.pack(fill="x", padx=0, pady=2)

        for shot_url in addon.screenshot_urls[:6]:
            frame = ctk.CTkFrame(scroll_row, width=150, height=95, fg_color="#161b22", corner_radius=6)
            frame.pack(side="left", padx=4, pady=2)
            frame.pack_propagate(False)

            shot_lbl = ctk.CTkLabel(frame, text="🖼️", font=ctk.CTkFont(size=20), anchor="center")
            shot_lbl.pack(expand=True, fill="both")

            def _apply_shot(img, lbl=shot_lbl, a=addon):
                if img and self.winfo_exists() and self.current_addon == a:
                    lbl.configure(image=img, text="")

            cached = ImageService.get_sync(shot_url, (140, 90))
            if cached:
                _apply_shot(cached)
            else:
                ImageService.get_async(shot_url, (140, 90), _apply_shot, root=self)

    def _render_state_warning(self, addon: AddonItem):
        """Exibe aviso destacado sobre preservação de estado ativo."""
        sec = self._section("🔒 Estado no Jogo")
        state_label = "🟢 ATIVO — será mantido ativo após atualizar" if addon.is_active else "⚫ INATIVO — permanecerá inativo após atualizar"
        state_color = "#1e8449" if addon.is_active else "#566573"
        ctk.CTkLabel(
            sec, text=state_label,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=state_color, anchor="w"
        ).pack(anchor="w", padx=2, pady=2)
        ctk.CTkLabel(
            sec,
            text="O campo stateGameElement é preservado na atualização via JSON.",
            font=ctk.CTkFont(size=10), text_color="#6e7681", anchor="w"
        ).pack(anchor="w", padx=2, pady=(0, 4))

    def _render_stats(self, addon: AddonItem):
        if addon.total_downloads == 0 and not addon.categories:
            return
        sec = self._section("📊 Informações")
        row = ctk.CTkFrame(sec, fg_color="transparent")
        row.pack(fill="x", padx=0, pady=4)

        if addon.total_downloads > 0:
            self._badge(row, "Downloads", addon.downloads_display, "#1f618d")
        if addon.popularity > 0:
            self._badge(row, "Popularidade TL", str(addon.popularity), "#4a235a")
        if addon.categories:
            cats = " · ".join(addon.categories[:4])
            ctk.CTkLabel(
                sec, text=f"🏷  {cats}", font=ctk.CTkFont(size=11),
                text_color="#58a6ff", anchor="w"
            ).pack(anchor="w", padx=2, pady=(4, 0))

    def _render_version(self, addon: AddonItem):
        if addon.status == AddonUpdateStatus.PENDING:
            return
        sec = self._section("🔄 Versão")
        grid = ctk.CTkFrame(sec, fg_color="transparent")
        grid.pack(fill="x", padx=0, pady=4)
        grid.grid_columnconfigure((0, 1, 2), weight=1)

        self._ver_box(grid, "📁 Instalado",
                      addon.installed_version_name or f"#{addon.installed_file_id}", "#1e3a5f", 0)

        arrow_color = "#e67e22" if addon.status in (AddonUpdateStatus.UPDATE_AVAILABLE, AddonUpdateStatus.TLAUNCHER_OK) else "#2ecc71"
        ctk.CTkLabel(grid, text="→", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=arrow_color).grid(row=0, column=1, padx=4)

        web_ver = addon.latest_version_name or "—"
        self._ver_box(grid, "🌐 Disponível", web_ver, "#0e3d1e", 2)

        if addon.tlauncher_available:
            ctk.CTkLabel(
                sec, text="✅ Confirmado nos servidores do TLauncher",
                font=ctk.CTkFont(size=11), text_color="#2ecc71"
            ).pack(anchor="w", padx=2, pady=(4, 0))

    def _render_description(self, addon: AddonItem):
        sec = self._section("📝 Descrição")
        if addon.description or getattr(addon, "summary", ""):
            RichContentRenderer.render_into(
                parent=sec,
                content=addon.description or "",
                summary=getattr(addon, "summary", "") or None,
                max_initial_blocks=10,
            )
        elif addon.id > 0:
            lbl_loading = ctk.CTkLabel(
                sec,
                text="⚡ Carregando descrição oficial do addon...",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color="#8b949e",
                anchor="w",
            )
            lbl_loading.pack(fill="x", padx=2, pady=4)
            self._fetch_addon_description_async(addon, sec, lbl_loading)
        else:
            ctk.CTkLabel(
                sec,
                text="Nenhuma descrição disponível para este addon local.",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color="#6e7681",
                anchor="w",
            ).pack(fill="x", padx=2, pady=4)

    def _fetch_addon_description_async(self, addon: AddonItem, sec: ctk.CTkFrame, lbl_loading: ctk.CTkLabel):
        def _worker():
            try:
                data = AddonUpdateService.fetch_cfwidget(addon.id)
                if data:
                    addon.description = data.get("description", "") or addon.description
                    addon.summary = data.get("summary", "") or getattr(addon, "summary", "")
                    if not addon.icon_url and data.get("thumbnail"):
                        addon.icon_url = data.get("thumbnail")
            except Exception:
                pass

            def _update_ui():
                try:
                    if not self.winfo_exists() or self.current_addon != addon:
                        return
                    if hasattr(lbl_loading, "winfo_exists") and lbl_loading.winfo_exists():
                        lbl_loading.destroy()
                    RichContentRenderer.render_into(
                        parent=sec,
                        content=addon.description or "",
                        summary=getattr(addon, "summary", "") or None,
                        max_initial_blocks=10,
                    )
                except Exception:
                    pass

            try:
                if self.winfo_exists():
                    self.after(0, _update_ui)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _render_links(self, addon: AddonItem):
        links = []
        if addon.link:
            links.append(("🌐 Página do Addon", addon.link, "#1f618d"))

        if not links:
            return
        sec = self._section("🔗 Links")
        row = ctk.CTkFrame(sec, fg_color="transparent")
        row.pack(fill="x", padx=0, pady=4)
        for label, url, color in links:
            ctk.CTkButton(
                row, text=label, height=28,
                fg_color=color, hover_color="#2d3436",
                font=ctk.CTkFont(size=11),
                command=lambda u=url: _open(u)
            ).pack(side="left", padx=(0, 6))

    # ------------------------------------------------------------------ #
    #  Widget helpers                                                      #
    # ------------------------------------------------------------------ #

    def _section(self, title: str) -> ctk.CTkFrame:
        wrap = ctk.CTkFrame(self.body, fg_color="#1a1d20", corner_radius=8)
        wrap.pack(fill="x", padx=0, pady=(0, 8))
        wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            wrap, text=title, font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#8b949e", anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkFrame(wrap, height=1, fg_color="#30363d", corner_radius=0).pack(fill="x", padx=8, pady=(0, 6))
        inner = ctk.CTkFrame(wrap, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(0, 10))
        return inner

    def _badge(self, parent, label: str, value: str, color: str):
        frame = ctk.CTkFrame(parent, fg_color=color, corner_radius=6)
        frame.pack(side="left", padx=(0, 6), pady=2)
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=9),
                     text_color="#aaaaaa").pack(padx=8, pady=(4, 0))
        ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#ffffff").pack(padx=8, pady=(0, 6))

    def _ver_box(self, parent, label: str, version: str, color: str, col: int):
        box = ctk.CTkFrame(parent, fg_color=color, corner_radius=6)
        box.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(box, text=label, font=ctk.CTkFont(size=10),
                     text_color="#8b949e", anchor="center").pack(pady=(6, 2))
        ctk.CTkLabel(box, text=version, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#ffffff", anchor="center", wraplength=150).pack(pady=(0, 8))

    def _on_apply(self):
        if self.current_addon:
            self.on_apply_single(self.current_addon)
