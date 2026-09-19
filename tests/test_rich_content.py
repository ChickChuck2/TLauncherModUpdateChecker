"""
Suíte de Testes Unitários para o Renderizador e Parser de Conteúdo Rico.
Testa:
  1. Extração semântica de badges (Shields.io, Twitter, Patreon, Discord, GitHub, dependências)
  2. Parse de HTML rico com banners, listas e formatações (ex: CurseForge / CFWidget)
  3. Parse de Markdown com títulos, listas, blocos de código (ex: Modrinth)
  4. Decodificação de entidades HTML (&nbsp;, &amp;, &quot;, etc.)
  5. Tratamento de entradas vazias, nulas ou malformadas
  6. Renderização de widgets no CustomTkinter (RichContentRenderer) incluindo toggle de expansão
"""

import os
import sys
import unittest

# Garante que o diretório raiz esteja no sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

from src.ui.components.rich_content_renderer import (
    RichContentParser,
    RichContentRenderer,
    ContentBlock,
)


class TestRichContent(unittest.TestCase):

    def test_parse_html_with_badges_and_banners(self):
        sample = (
            '<p><img src="https://i.imgur.com/YSXHWf5.png" alt="">'
            '<img src="https://img.shields.io/badge/dependency-titanium-E04E14?labelColor=2D2D2D&style=for-the-badge" alt="">'
            '<a href="https://twitter.com/Buuz135mods" target="_blank">'
            '<img src="https://img.shields.io/twitter/follow/Buuz135mods?color=E04E14&style=for-the-badge"></a>'
            '<a href="https://www.patreon.com/buuz135" target="_blank">'
            '<img src="https://img.shields.io/badge/DONATE-PATREON-E04E14?style=for-the-badge"></a>'
            '<a href="https://discord.gg/4tPfwjn" target="_blank">'
            '<img src="https://img.shields.io/discord/357597633566605313?label=JOIN-DISCORD&style=for-the-badge"></a>'
            '</p>'
            '<p><strong>Industrial Foregoing</strong> &amp; friends is a comprehensive automation mod.</p>'
            '<h3>Key Features:</h3>'
            '<ul>'
            '<li><strong>Resource Automation</strong>: Process ores and fluids.</li>'
            '<li><strong>Farming Tools</strong>: Automate crops.</li>'
            '</ul>'
        )
        blocks = RichContentParser.parse_auto(sample)
        self.assertGreater(len(blocks), 3)

        # 1. Verifica banner de imagem real
        banners = [b for b in blocks if b.type == "banner_image"]
        self.assertTrue(len(banners) >= 1)
        self.assertEqual(banners[0].get("url"), "https://i.imgur.com/YSXHWf5.png")

        # 2. Verifica grupo de badges convertidos
        badge_groups = [b for b in blocks if b.type == "badge_group"]
        self.assertTrue(len(badge_groups) >= 1)
        badges = badge_groups[0].get("badges")
        labels = [b["label"] for b in badges]
        urls = [b.get("url") for b in badges]

        self.assertTrue(any("Titanium" in l for l in labels))
        self.assertTrue(any("Twitter" in l for l in labels))
        self.assertTrue(any("Patreon" in l for l in labels))
        self.assertTrue(any("Discord" in l for l in labels))

        self.assertIn("https://twitter.com/Buuz135mods", urls)
        self.assertIn("https://www.patreon.com/buuz135", urls)
        self.assertIn("https://discord.gg/4tPfwjn", urls)

        # 3. Verifica parágrafo com decodificação de entidades HTML
        paragraphs = [b for b in blocks if b.type == "paragraph"]
        self.assertTrue(any("Industrial Foregoing & friends" in p.get("text") for p in paragraphs))

        # 4. Verifica título
        headings = [b for b in blocks if b.type == "heading"]
        self.assertTrue(any("Key Features:" in h.get("text") for h in headings))

        # 5. Verifica lista
        lists = [b for b in blocks if b.type == "list"]
        self.assertEqual(len(lists), 1)
        self.assertEqual(len(lists[0].get("items")), 2)

    def test_parse_badge_info_varieties(self):
        # Dependência
        b_dep = RichContentParser.parse_badge_info(
            "https://img.shields.io/badge/dependency-cloth_config-E04E14"
        )
        self.assertEqual(b_dep["icon"], "⚡")
        self.assertIn("Cloth Config", b_dep["label"])

        # Twitter por link
        b_tw = RichContentParser.parse_badge_info("", "https://twitter.com/author_name")
        self.assertEqual(b_tw["icon"], "🐦")
        self.assertIn("author_name", b_tw["label"])

        # Patreon por link
        b_pat = RichContentParser.parse_badge_info("", "https://www.patreon.com/my_mod")
        self.assertEqual(b_pat["icon"], "💖")

        # GitHub por link
        b_gh = RichContentParser.parse_badge_info("", "https://github.com/org/repo")
        self.assertEqual(b_gh["icon"], "💻")

    def test_parse_markdown(self):
        sample = (
            "# Sodium\n\n"
            "A high-performance rendering engine for Minecraft.\n\n"
            "## Key Features\n"
            "- Faster chunk rendering\n"
            "- Reduced memory allocations\n\n"
            "```json\n"
            '{"status": "ok"}\n'
            "```"
        )
        blocks = RichContentParser.parse_auto(sample)
        types = [b.type for b in blocks]
        self.assertIn("heading", types)
        self.assertIn("paragraph", types)
        self.assertIn("list", types)
        self.assertIn("code", types)

        # Valida conteúdo do bloco de código
        code_block = next(b for b in blocks if b.type == "code")
        self.assertIn('"status": "ok"', code_block.get("code"))

    def test_empty_and_malformed_content(self):
        self.assertEqual(RichContentParser.parse_auto(""), [])
        self.assertEqual(RichContentParser.parse_auto(None), [])
        self.assertEqual(RichContentParser.parse_auto("   \n\t  "), [])

        # HTML quebrado / não fechado
        broken_html = "<p>Texto sem fechar a tag <b>negrito"
        blocks = RichContentParser.parse_auto(broken_html)
        self.assertTrue(len(blocks) >= 1)
        self.assertIn("Texto sem fechar", blocks[0].get("text"))

    def test_render_into_customtkinter(self):
        """Verifica que a renderização cria os widgets no CustomTkinter sem erros de runtime."""
        root = ctk.CTk()
        try:
            parent_frame = ctk.CTkFrame(root)
            parent_frame.pack()

            sample = (
                '<p><img src="https://i.imgur.com/YSXHWf5.png">'
                '<img src="https://img.shields.io/badge/dependency-titanium-E04E14">'
                '<a href="https://discord.gg/test"><img src="https://img.shields.io/discord/123"></a></p>'
                '<p>Descrição de teste do mod.</p>'
                '<h3>Tópico de Recursos</h3>'
                '<ul><li>Item 1</li><li>Item 2</li></ul>'
                '<code>config = true</code>'
            )

            RichContentRenderer.render_into(
                parent=parent_frame,
                content=sample,
                summary="Resumo de teste de alta prioridade",
                max_initial_blocks=4,
            )

            # Verifica que foram gerados widgets filhos
            children = parent_frame.winfo_children()
            self.assertGreater(len(children), 2)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
