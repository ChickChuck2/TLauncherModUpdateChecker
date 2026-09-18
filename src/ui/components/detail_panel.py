"""
Painel de detalhes do mod selecionado.
Exibe: ícone, descrição, categorias, autores, downloads, links, changelog,
dependências, tipo de release e comparativo de versão.
"""

import webbrowser
import customtkinter as ctk
from typing import Optional
from src.core.models import ModItem, UpdateStatus
from src.services.image_service import ImageService


def _open_url(url: str):
    try:
        webbrowser.open(url)
    except Exception:
        pass


class DetailPanel(ctk.CTkFrame):
    """Painel direito com todos os detalhes do mod selecionado."""

    def __init__(self, master, on_apply_single: callable, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self.on_apply_single = on_apply_single
        self.current_mod: Optional[ModItem] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._show_placeholder()

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def _build_header(self):
        self.header = ctk.CTkFrame(self, fg_color="#1a1d20", corner_radius=8)
        self.header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        self.header.grid_columnconfigure(1, weight=1)

        # Ícone placeholder
        self.icon_lbl = ctk.CTkLabel(
            self.header, text="📦", font=ctk.CTkFont(size=48), width=64, anchor="center"
        )
        self.icon_lbl.grid(row=0, column=0, rowspan=3, padx=(14, 10), pady=14, sticky="w")

        # Nome
        self.lbl_name = ctk.CTkLabel(
            self.header, text="Selecione um mod",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        )
        self.lbl_name.grid(row=0, column=1, padx=0, pady=(12, 2), sticky="w")

        # Autores
        self.lbl_authors = ctk.CTkLabel(
            self.header, text="", font=ctk.CTkFont(size=11),
            text_color="#6e7681", anchor="w"
        )
        self.lbl_authors.grid(row=1, column=1, sticky="w")

        # Categorias
        self.lbl_categories = ctk.CTkLabel(
            self.header, text="", font=ctk.CTkFont(size=11),
            text_color="#58a6ff", anchor="w"
        )
        self.lbl_categories.grid(row=2, column=1, pady=(0, 12), sticky="w")

        # Badge de status + botão de update individual
        right_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        right_frame.grid(row=0, column=2, rowspan=3, padx=14, pady=10, sticky="e")

        self.badge_status = ctk.CTkLabel(
            right_frame, text="—",
            fg_color="#4a4a4a", text_color="#ffffff",
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold")
        )
        self.badge_status.pack(padx=10, pady=(0, 6))

        self.btn_update = ctk.CTkButton(
            right_frame, text="⚡ Aplicar no JSON",
            width=130, height=30,
            fg_color="#117a65", hover_color="#0e6655",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_apply_single,
            state="disabled"
        )
        self.btn_update.pack()

    def _build_body(self):
        self.body_scroll = ctk.CTkScrollableFrame(self, corner_radius=6, fg_color="transparent")
        self.body_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.body_scroll.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show_mod(self, mod: ModItem):
        self.current_mod = mod
        self._clear_body()
        self._render_header(mod)
        self._render_stats(mod)
        self._render_screenshots(mod)
        self._render_version_comparison(mod)
        self._render_description(mod)
        self._render_changelog(mod)
        self._render_links(mod)
        self._render_dependencies(mod)

    def clear(self):
        self.current_mod = None
        self._clear_body()
        self._show_placeholder()

    # ------------------------------------------------------------------ #
    #  Render helpers                                                      #
    # ------------------------------------------------------------------ #

    def _clear_body(self):
        for w in self.body_scroll.winfo_children():
            w.destroy()

    def _show_placeholder(self):
        self.lbl_name.configure(text="Selecione um mod na lista")
        self.lbl_authors.configure(text="")
        self.lbl_categories.configure(text="")
        self.badge_status.configure(text="—", fg_color="#4a4a4a")
        self.btn_update.configure(state="disabled")
        self.icon_lbl.configure(text="📦", image=None)
        self._header_img = None
        ctk.CTkLabel(
            self.body_scroll,
            text="Clique em qualquer mod da lista para ver seus detalhes completos aqui.",
            font=ctk.CTkFont(size=13),
            text_color="#6e7681",
            wraplength=360,
        ).pack(pady=40, padx=20)

    def _render_header(self, mod: ModItem):
        self.lbl_name.configure(text=mod.name)
        self.lbl_authors.configure(
            text=f"✍️  {', '.join(mod.authors)}" if mod.authors else "Autor desconhecido"
        )
        cats = [c.replace("-", " ").title() for c in mod.categories[:5]]
        self.lbl_categories.configure(
            text=f"🏷  {' · '.join(cats)}" if cats else ""
        )
        self.badge_status.configure(
            text=mod.status.label, fg_color=mod.status.color
        )
        can_update = mod.status == UpdateStatus.TLAUNCHER_CONFIRMED
        self.btn_update.configure(state="normal" if can_update else "disabled")

        # Carrega thumbnail em alta definição
        self.icon_lbl.configure(text="📦", image=None)
        self._header_img = None
        if mod.icon_url:
            cached = ImageService.get_sync(mod.icon_url, (56, 56))
            if cached:
                self._apply_header_icon(cached, mod)
            else:
                ImageService.get_async(
                    mod.icon_url, (56, 56),
                    lambda img, m=mod: self._apply_header_icon(img, m),
                    root=self
                )

    def _apply_header_icon(self, img, target_mod):
        if img and self.winfo_exists() and self.current_mod == target_mod:
            self._header_img = img
            self.icon_lbl.configure(image=img, text="")

    def _render_screenshots(self, mod: ModItem):
        if not mod.screenshot_urls:
            return
        sec = self._section("📸 Imagens / Capturas de Tela")
        scroll_row = ctk.CTkScrollableFrame(sec, orientation="horizontal", height=120, fg_color="transparent")
        scroll_row.pack(fill="x", padx=0, pady=2)

        for shot_url in mod.screenshot_urls[:6]:
            frame = ctk.CTkFrame(scroll_row, width=150, height=95, fg_color="#161b22", corner_radius=6)
            frame.pack(side="left", padx=4, pady=2)
            frame.pack_propagate(False)

            shot_lbl = ctk.CTkLabel(frame, text="🖼️", font=ctk.CTkFont(size=20), anchor="center")
            shot_lbl.pack(expand=True, fill="both")

            def _apply_shot(img, lbl=shot_lbl, m=mod):
                if img and self.winfo_exists() and self.current_mod == m:
                    lbl.configure(image=img, text="")

            cached = ImageService.get_sync(shot_url, (140, 90))
            if cached:
                _apply_shot(cached)
            else:
                ImageService.get_async(shot_url, (140, 90), _apply_shot, root=self)

    def _render_stats(self, mod: ModItem):
        has_downloads = mod.total_downloads > 0
        has_size = bool(mod.latest_size or mod.installed_size)
        has_provider = bool(mod.provider)
        has_license = bool(mod.mod_license)

        if not (has_downloads or has_size or has_provider or has_license):
            return

        sec = self._section("📊 Estatísticas e Informações")
        row = ctk.CTkFrame(sec, fg_color="transparent")
        row.pack(fill="x", padx=0, pady=(4, 0))

        if has_downloads:
            self._stat_badge(row, "Downloads Totais", mod.downloads_display, "#1f618d")
        if mod.monthly_downloads > 0:
            m = mod.monthly_downloads
            monthly = f"{m/1000:.0f}K" if m >= 1000 else str(m)
            self._stat_badge(row, "Downloads/Mês", monthly, "#145a32")
        if has_provider:
            self._stat_badge(row, "Fonte", mod.provider, "#4a235a")
        if has_license:
            self._stat_badge(row, "Licença", mod.mod_license, "#6e2f1a")

        release_type = (mod.latest_release_type or "release").capitalize()
        rt_color = {"Release": "#1e8449", "Beta": "#d68910", "Alpha": "#922b21"}.get(release_type, "#4a4a4a")
        self._stat_badge(row, "Tipo de Release", release_type, rt_color)

    def _render_version_comparison(self, mod: ModItem):
        if mod.status == UpdateStatus.PENDING:
            return

        sec = self._section("🔄 Comparativo de Versão")
        grid = ctk.CTkFrame(sec, fg_color="transparent")
        grid.pack(fill="x", padx=0, pady=4)
        grid.grid_columnconfigure((0, 1, 2), weight=1)

        # Instalado
        self._ver_box(grid, "📁 Instalado",
                      mod.installed_version_name or f"File #{mod.installed_file_id}",
                      "#1e3a5f", col=0)

        # Seta
        arrow_color = "#e67e22" if mod.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED) else "#2ecc71"
        ctk.CTkLabel(grid, text="→", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=arrow_color).grid(row=0, column=1, padx=4)

        # Web
        web_ver = mod.latest_version_name or (f"File #{mod.latest_file_id}" if mod.latest_file_id else "—")
        self._ver_box(grid, "🌐 Disponível na Web", web_ver, "#0e3d1e", col=2)

        # TLauncher disponível
        if mod.tlauncher_available:
            ctk.CTkLabel(
                sec,
                text="✅ Confirmado nos servidores oficiais do TLauncher (res.tlauncher.org)",
                font=ctk.CTkFont(size=11), text_color="#2ecc71"
            ).pack(anchor="w", padx=2, pady=(4, 0))
        elif mod.latest_file_id:
            ctk.CTkLabel(
                sec,
                text="⚠️  Novo arquivo ainda não disponível no repositório do TLauncher.",
                font=ctk.CTkFont(size=11), text_color="#e67e22"
            ).pack(anchor="w", padx=2, pady=(4, 0))

    def _render_description(self, mod: ModItem):
        if not mod.description:
            return
        sec = self._section("📝 Descrição")
        ctk.CTkLabel(
            sec, text=mod.description[:600] + ("…" if len(mod.description) > 600 else ""),
            font=ctk.CTkFont(size=12), text_color="#c9d1d9",
            wraplength=400, justify="left", anchor="w"
        ).pack(fill="x", padx=2, pady=4)

    def _render_changelog(self, mod: ModItem):
        if not mod.latest_changelog:
            return
        sec = self._section("📋 O que mudou nessa versão")
        changelog_text = mod.latest_changelog[:800] + ("…" if len(mod.latest_changelog) > 800 else "")
        box = ctk.CTkTextbox(sec, height=100, font=ctk.CTkFont(size=11), wrap="word",
                             fg_color="#161b22", text_color="#c9d1d9", corner_radius=6)
        box.pack(fill="x", padx=2, pady=4)
        box.insert("1.0", changelog_text)
        box.configure(state="disabled")

    def _render_links(self, mod: ModItem):
        links = []
        if mod.link:
            links.append(("🌐 CurseForge / Página do Mod", mod.link, "#1f618d"))
        if mod.source_url:
            links.append(("💻 Código Fonte", mod.source_url, "#145a32"))
        if mod.issues_url:
            links.append(("🐛 Reportar Bug", mod.issues_url, "#6e2f1a"))

        if not links:
            return

        sec = self._section("🔗 Links")
        link_row = ctk.CTkFrame(sec, fg_color="transparent")
        link_row.pack(fill="x", padx=0, pady=4)

        for label, url, color in links:
            btn = ctk.CTkButton(
                link_row, text=label, height=28,
                fg_color=color, hover_color="#2d3436",
                font=ctk.CTkFont(size=11),
                command=lambda u=url: _open_url(u)
            )
            btn.pack(side="left", padx=(0, 6))

    def _render_dependencies(self, mod: ModItem):
        if not mod.latest_dependencies:
            return
        sec = self._section("🔧 Dependências desta versão")
        for dep in mod.latest_dependencies[:8]:
            dep_name = dep.name or dep.slug or "Desconhecida"
            rel_color = {"required": "#922b21", "optional": "#6e2f1a", "incompatible": "#4a235a"}.get(dep.relation_type, "#4a4a4a")
            row = ctk.CTkFrame(sec, fg_color="transparent")
            row.pack(fill="x", padx=0, pady=1)
            ctk.CTkLabel(
                row, text=dep_name, font=ctk.CTkFont(size=11),
                text_color="#c9d1d9", anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=dep.relation_type.capitalize(),
                fg_color=rel_color, text_color="#ffffff",
                corner_radius=4, font=ctk.CTkFont(size=9)
            ).pack(side="right", padx=5, pady=2)

    # ------------------------------------------------------------------ #
    #  Widget helpers                                                      #
    # ------------------------------------------------------------------ #

    def _section(self, title: str) -> ctk.CTkFrame:
        """Cria uma seção com título separador."""
        wrap = ctk.CTkFrame(self.body_scroll, fg_color="#1a1d20", corner_radius=8)
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

    def _stat_badge(self, parent, label: str, value: str, color: str):
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
                     text_color="#ffffff", anchor="center",
                     wraplength=150).pack(pady=(0, 8))

    def _on_apply_single(self):
        if self.current_mod:
            self.on_apply_single(self.current_mod)
