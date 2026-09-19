"""
Renderizador visual rico para descrições de mods e changelogs (HTML e Markdown).
Transforma marcações brutas em interface gráfica moderna:
  - Banners e imagens reais carregadas assincronamente via ImageService
  - Badges (Shields.io, Discord, Patreon, Twitter, dependências) como botões interativos
  - Tipografia hierárquica (títulos H1-H6 com cores e espaçamentos estilizados)
  - Listas com marcadores (bullet points) alinhados
  - Blocos de código em cards escuros monoespaçados
  - Cartão de resumo destacado no topo
  - Controle de expansão/recolhimento para textos longos
"""

import html
import re
import urllib.parse
import webbrowser
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import customtkinter as ctk

from src.services.image_service import ImageService


def _open_url(url: str):
    """Abre URL no navegador padrão do sistema."""
    if url and url.startswith(("http://", "https://")):
        try:
            webbrowser.open(url)
        except Exception:
            pass


class ContentBlock:
    """Representa um bloco semântico de conteúdo."""
    def __init__(self, btype: str, **kwargs):
        self.type = btype
        self.data = kwargs

    def get(self, key: str, default=None):
        return self.data.get(key, default)


class RichContentParser:
    """Analisa HTML ou Markdown e extrai blocos semânticos ricos."""

    @staticmethod
    def parse_badge_info(img_url: str, link_url: str = "") -> Dict[str, Any]:
        """Extrai metadados visuais de badges (ícone, título, cor, link de destino)."""
        url_lower = img_url.lower()
        link_lower = (link_url or "").lower()

        icon = "🏷️"
        label = "Badge"
        color = "#21262d"
        hover = "#30363d"
        final_url = link_url

        # 1. Identificação por URL de destino (links sociais e apoio)
        if "twitter.com" in link_lower or "x.com" in link_lower:
            icon = "🐦"
            user = link_url.rstrip("/").split("/")[-1]
            label = f"Twitter: @{user}" if user and not user.startswith("twitter") else "Twitter"
            color = "#0c2d48"
            hover = "#14426b"
        elif "patreon.com" in link_lower:
            icon = "💖"
            label = "Apoiar no Patreon"
            color = "#3e1616"
            hover = "#5a1f1f"
        elif "discord" in link_lower:
            icon = "👾"
            label = "Comunidade Discord"
            color = "#20223d"
            hover = "#2f325a"
        elif "github.com" in link_lower:
            icon = "💻"
            label = "GitHub / Código Fonte"
            color = "#161b22"
            hover = "#30363d"
        elif "ko-fi.com" in link_lower:
            icon = "☕"
            label = "Apoiar no Ko-fi"
            color = "#3e1616"
            hover = "#5a1f1f"
        elif "curseforge.com" in link_lower:
            icon = "🔥"
            label = "CurseForge"
            color = "#3d1f0d"
            hover = "#5c2e14"
        elif "modrinth.com" in link_lower:
            icon = "🌿"
            label = "Modrinth"
            color = "#0d3319"
            hover = "#154d26"

        # 2. Identificação por URL do badge (Shields.io, Badgen, etc.)
        if "shields.io" in url_lower or "badgen.net" in url_lower:
            if "/badge/" in url_lower:
                part = img_url.split("/badge/")[-1].split("?")[0]
                parts = part.split("-")
                if len(parts) >= 2:
                    p0 = urllib.parse.unquote(parts[0]).replace("_", " ").strip()
                    p1 = urllib.parse.unquote(parts[1]).replace("_", " ").strip()
                    if "dependency" in p0.lower():
                        icon = "⚡"
                        label = f"Requer: {p1.title()}"
                        color = "#382800"
                        hover = "#543c00"
                    elif "donate" in p0.lower():
                        icon = "💖"
                        label = f"Apoiar: {p1.title()}"
                        color = "#3e1616"
                        hover = "#5a1f1f"
                    elif "version" in p0.lower():
                        icon = "🏷️"
                        label = f"Versão: {p1}"
                    elif "download" in p0.lower():
                        icon = "📥"
                        label = f"Downloads: {p1}"
                    else:
                        label = f"{p0}: {p1}".title()
            elif "/twitter/" in url_lower:
                icon = "🐦"
                user = img_url.split("/twitter/follow/")[-1].split("?")[0].split("/")[0]
                label = f"Twitter: @{user}"
                color = "#0c2d48"
                hover = "#14426b"
            elif "/discord/" in url_lower:
                icon = "👾"
                label = "Entrar no Discord"
                color = "#20223d"
                hover = "#2f325a"

        return {
            "icon": icon,
            "label": label,
            "color": color,
            "hover": hover,
            "url": final_url,
        }

    @staticmethod
    def is_badge_url(url: str) -> bool:
        """Determina se uma URL é de badge/selo (SVG, Shields.io, Badgen)."""
        u = url.lower()
        return ("shields.io" in u or ".svg" in u or "badgen.net" in u or "badge" in u)

    @classmethod
    def parse_html(cls, raw_html: str) -> List[ContentBlock]:
        """Converte HTML de CurseForge/CFWidget em blocos limpos."""
        blocks: List[ContentBlock] = []
        current_badges: List[Dict[str, Any]] = []

        class TreeParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.current_text = []
                self.current_link = None
                self.current_list = []
                self.in_list = False
                self.in_code = False
                self.code_text = []

            def flush_badges(self):
                nonlocal current_badges
                if current_badges:
                    blocks.append(ContentBlock("badge_group", badges=list(current_badges)))
                    current_badges.clear()

            def handle_starttag(self, tag, attrs):
                attr_dict = dict(attrs)

                if tag == "a":
                    self.current_link = attr_dict.get("href")
                elif tag == "img":
                    src = attr_dict.get("src", "")
                    alt = attr_dict.get("alt", "")
                    if src:
                        if cls.is_badge_url(src):
                            badge = cls.parse_badge_info(src, self.current_link or "")
                            current_badges.append(badge)
                        else:
                            self.flush_badges()
                            blocks.append(ContentBlock("banner_image", url=src, link_url=self.current_link, alt=alt))
                elif tag in ("ul", "ol"):
                    self.flush_badges()
                    self.in_list = True
                    self.current_list = []
                elif tag == "li":
                    self.current_text = []
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    self.flush_badges()
                    self.current_text = []
                elif tag in ("p", "div"):
                    self.current_text = []
                elif tag in ("pre", "code"):
                    self.in_code = True
                    self.code_text = []

            def handle_endtag(self, tag):
                if tag == "a":
                    self.current_link = None
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    t = html.unescape("".join(self.current_text)).strip()
                    if t:
                        lvl = int(tag[1])
                        blocks.append(ContentBlock("heading", level=lvl, text=t))
                    self.current_text = []
                elif tag == "li":
                    t = html.unescape("".join(self.current_text)).strip()
                    if t:
                        self.current_list.append(t)
                    self.current_text = []
                elif tag in ("ul", "ol"):
                    if self.current_list:
                        blocks.append(ContentBlock("list", items=list(self.current_list)))
                    self.in_list = False
                    self.current_list = []
                elif tag in ("p", "div"):
                    t = html.unescape("".join(self.current_text)).strip()
                    self.flush_badges()
                    if t:
                        blocks.append(ContentBlock("paragraph", text=t))
                    self.current_text = []
                elif tag in ("pre", "code"):
                    self.in_code = False
                    c = html.unescape("".join(self.code_text)).strip()
                    if c:
                        blocks.append(ContentBlock("code", code=c))
                    self.code_text = []

            def handle_data(self, data):
                if self.in_code:
                    self.code_text.append(data)
                else:
                    self.current_text.append(data)

        parser = TreeParser()
        try:
            parser.feed(raw_html)
            parser.flush_badges()
            t = html.unescape("".join(parser.current_text)).strip()
            if t:
                blocks.append(ContentBlock("paragraph", text=t))
        except Exception:
            clean = re.sub(r"<[^>]+>", " ", raw_html)
            clean = html.unescape(clean).strip()
            if clean:
                blocks.append(ContentBlock("paragraph", text=clean))

        return blocks

    @classmethod
    def parse_markdown(cls, raw_md: str) -> List[ContentBlock]:
        """Converte Markdown de Modrinth/CurseForge em blocos estruturados."""
        blocks: List[ContentBlock] = []
        lines = raw_md.splitlines()
        current_p = []
        current_list = []
        in_code = False
        code_lines = []

        def flush_p():
            if current_p:
                t = " ".join(current_p).strip()
                if t:
                    blocks.append(ContentBlock("paragraph", text=t))
                current_p.clear()

        def flush_list():
            if current_list:
                blocks.append(ContentBlock("list", items=list(current_list)))
                current_list.clear()

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_code:
                    in_code = False
                    blocks.append(ContentBlock("code", code="\n".join(code_lines)))
                    code_lines.clear()
                else:
                    flush_p()
                    flush_list()
                    in_code = True
                continue

            if in_code:
                code_lines.append(line)
                continue

            if not stripped:
                flush_p()
                flush_list()
                continue

            # Imagem markdown: ![alt](url)
            img_match = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
            if img_match:
                flush_p()
                flush_list()
                alt, url = img_match.groups()
                if cls.is_badge_url(url):
                    badge = cls.parse_badge_info(url)
                    blocks.append(ContentBlock("badge_group", badges=[badge]))
                else:
                    blocks.append(ContentBlock("banner_image", url=url, link_url=None, alt=alt))
                continue

            # Títulos: #, ##, ###
            head_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if head_match:
                flush_p()
                flush_list()
                lvl = len(head_match.group(1))
                txt = head_match.group(2).strip()
                txt = re.sub(r"\*\*([^*]+)\*\*", r"\1", txt)
                blocks.append(ContentBlock("heading", level=lvl, text=txt))
                continue

            # Itens de lista: - item ou * item
            list_match = re.match(r"^[-*•]\s+(.*)$", stripped)
            if list_match:
                flush_p()
                item_txt = list_match.group(1).strip()
                item_txt = re.sub(r"\*\*([^*]+)\*\*", r"\1", item_txt)
                current_list.append(item_txt)
                continue

            # Parágrafo
            flush_list()
            clean_line = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped)
            clean_line = re.sub(r"\*([^*]+)\*", r"\1", clean_line)
            clean_line = re.sub(r"_([^_]+)_", r"\1", clean_line)
            current_p.append(clean_line)

        flush_p()
        flush_list()
        return blocks

    @classmethod
    def parse_auto(cls, content: str) -> List[ContentBlock]:
        """Detecta automaticamente formato (HTML ou Markdown) e retorna lista de blocos."""
        if not content or not content.strip():
            return []
        c = content.strip()
        if re.search(r"<(p|div|h[1-6]|img|a|ul|ol|li|strong|b|br)[\s>]", c, re.IGNORECASE):
            return cls.parse_html(c)
        return cls.parse_markdown(c)


class RichContentRenderer:
    """Constrói widgets CustomTkinter atraentes e funcionais a partir dos blocos."""

    @classmethod
    def render_into(
        cls,
        parent: ctk.CTkFrame,
        content: str,
        summary: Optional[str] = None,
        max_initial_blocks: int = 12,
    ):
        """
        Renderiza conteúdo rico dentro do frame de container fornecido.
        """
        # 1. Cartão de Resumo em destaque (se disponível)
        if summary and summary.strip():
            sum_card = ctk.CTkFrame(
                parent,
                fg_color="#161b22",
                border_color="#30363d",
                border_width=1,
                corner_radius=8
            )
            sum_card.pack(fill="x", padx=2, pady=(2, 10))

            top_row = ctk.CTkFrame(sum_card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                top_row,
                text="💡 RESUMO DO MOD",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#58a6ff"
            ).pack(side="left")

            ctk.CTkLabel(
                sum_card,
                text=summary.strip(),
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color="#e6edf3",
                wraplength=380,
                justify="left",
                anchor="w"
            ).pack(fill="x", padx=10, pady=(0, 10))

        # 2. Parse do conteúdo
        blocks = RichContentParser.parse_auto(content)
        if not blocks:
            if not summary:
                ctk.CTkLabel(
                    parent,
                    text="Nenhuma descrição fornecida.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="#6e7681",
                    anchor="w"
                ).pack(fill="x", padx=2, pady=4)
            return

        # 3. Renderização completa de todos os blocos (sem ocultar nada)
        for block in blocks:
            cls._render_single_block(parent, block)

    @classmethod
    def _render_single_block(cls, parent: ctk.CTkFrame, block: ContentBlock) -> Optional[ctk.CTkBaseClass]:
        btype = block.type

        # ------------------- BANNER / IMAGEM -------------------
        if btype == "banner_image":
            url = block.get("url")
            link_url = block.get("link_url")
            if not url:
                return None

            img_frame = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=8, border_color="#30363d", border_width=1)
            img_frame.pack(fill="x", padx=2, pady=4)

            lbl_img = ctk.CTkLabel(
                img_frame,
                text="🖼️ Carregando imagem...",
                font=ctk.CTkFont(size=11),
                text_color="#6e7681",
                height=70,
            )
            lbl_img.pack(fill="both", expand=True, padx=4, pady=4)

            if link_url:
                lbl_img.configure(cursor="hand2")
                lbl_img.bind("<Button-1>", lambda e, u=link_url: _open_url(u))

            def on_img_ready(img, target_lbl=lbl_img, target_url=link_url):
                try:
                    if hasattr(target_lbl, "winfo_exists") and target_lbl.winfo_exists() and img:
                        target_lbl.configure(image=img, text="")
                except Exception:
                    pass

            ImageService.get_async(url, (380, 120), on_img_ready, root=parent)
            return img_frame

        # ------------------- GRUPO DE BADGES / CHIPS -------------------
        elif btype == "badge_group":
            badges = block.get("badges", [])
            if not badges:
                return None

            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=(4, 6))

            for b in badges:
                icon = b.get("icon", "🏷️")
                lbl = b.get("label", "")
                url = b.get("url", "")
                bg_col = b.get("color", "#21262d")
                hov_col = b.get("hover", "#30363d")

                btn = ctk.CTkButton(
                    row,
                    text=f"{icon} {lbl}",
                    height=26,
                    corner_radius=13,
                    fg_color=bg_col,
                    hover_color=hov_col,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#ffffff",
                    command=(lambda u=url: _open_url(u)) if url else None,
                    state="normal" if url else "disabled"
                )
                btn.pack(side="left", padx=(0, 6), pady=2)

            return row

        # ------------------- TÍTULO (H1-H6) -------------------
        elif btype == "heading":
            lvl = block.get("level", 2)
            txt = block.get("text", "")
            sizes = {1: 15, 2: 13, 3: 12, 4: 11, 5: 11, 6: 10}
            colors = {1: "#58a6ff", 2: "#79c0ff", 3: "#a5d6ff", 4: "#c9d1d9"}

            f_size = sizes.get(lvl, 12)
            t_col = colors.get(lvl, "#79c0ff")

            lbl_h = ctk.CTkLabel(
                parent,
                text=txt,
                font=ctk.CTkFont(size=f_size, weight="bold"),
                text_color=t_col,
                anchor="w",
                justify="left"
            )
            lbl_h.pack(fill="x", padx=2, pady=(8, 2))
            return lbl_h

        # ------------------- PARÁGRAFO -------------------
        elif btype == "paragraph":
            txt = block.get("text", "")
            if not txt:
                return None

            lbl_p = ctk.CTkLabel(
                parent,
                text=txt,
                font=ctk.CTkFont(size=12),
                text_color="#c9d1d9",
                wraplength=390,
                justify="left",
                anchor="w"
            )
            lbl_p.pack(fill="x", padx=2, pady=3)
            return lbl_p

        # ------------------- LISTA COM MARCADORES -------------------
        elif btype == "list":
            items = block.get("items", [])
            if not items:
                return None

            list_frame = ctk.CTkFrame(parent, fg_color="transparent")
            list_frame.pack(fill="x", padx=2, pady=3)

            for item in items:
                i_row = ctk.CTkFrame(list_frame, fg_color="transparent")
                i_row.pack(fill="x", pady=2)

                ctk.CTkLabel(
                    i_row,
                    text="•",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#58a6ff"
                ).pack(side="left", anchor="n", padx=(4, 6))

                ctk.CTkLabel(
                    i_row,
                    text=item,
                    font=ctk.CTkFont(size=12),
                    text_color="#c9d1d9",
                    wraplength=370,
                    justify="left",
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)

            return list_frame

        # ------------------- BLOCO DE CÓDIGO -------------------
        elif btype == "code":
            code = block.get("code", "")
            if not code:
                return None

            box = ctk.CTkTextbox(
                parent,
                height=min(120, max(45, len(code.splitlines()) * 18)),
                font=ctk.CTkFont(family="Consolas", size=11),
                wrap="none",
                fg_color="#0d1117",
                border_color="#30363d",
                border_width=1,
                text_color="#79c0ff",
                corner_radius=6
            )
            box.pack(fill="x", padx=2, pady=4)
            box.insert("1.0", code)
            box.configure(state="disabled")
            return box

        return None
