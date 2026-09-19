"""
Testes para persistência de modpack selecionado (SettingsService)
e categorização/ordenação por Mods Pesados.
"""

import unittest
import os
import customtkinter as ctk
from src.core.models import ModItem, ModpackInfo, UpdateStatus
from src.services.settings_service import SettingsService, SETTINGS_FILE
from src.ui.components.pack_selector import PackSelector
from src.ui.components.mod_list import ModList, SORT_OPTIONS, STATUS_FILTER_MAP


class TestSettingsAndHeavyMods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.update_idletasks()
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        # Limpa cache do SettingsService antes de cada teste
        SettingsService._cache = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                os.remove(SETTINGS_FILE)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                os.remove(SETTINGS_FILE)
            except Exception:
                pass

    def test_settings_service_persistence(self):
        # 1. Sem configuração prévia
        self.assertIsNone(SettingsService.get_last_modpack())

        # 2. Salva modpack
        SettingsService.set_last_modpack("FTB StoneBlock 3")
        self.assertEqual(SettingsService.get_last_modpack(), "FTB StoneBlock 3")

        # 3. Força recarga do arquivo
        SettingsService._cache = None
        self.assertEqual(SettingsService.get_last_modpack(), "FTB StoneBlock 3")

    def test_pack_selector_auto_restores_last_modpack(self):
        # Salva "PackB" como último selecionado
        SettingsService.set_last_modpack("folder_b")

        pack_a = ModpackInfo(name="Pack A", folder_name="folder_a", json_path="a.json", game_version="1.20.1", loader="forge")
        pack_b = ModpackInfo(name="Pack B", folder_name="folder_b", json_path="b.json", game_version="1.20.1", loader="forge")
        pack_c = ModpackInfo(name="Pack C", folder_name="folder_c", json_path="c.json", game_version="1.20.1", loader="forge")

        selected = []
        selector = PackSelector(
            self.root,
            on_pack_selected=lambda p: selected.append(p),
            on_check_updates_clicked=lambda: None,
            on_apply_updates_clicked=lambda: None,
            on_refresh_packs_clicked=lambda: None
        )
        selector.pack()

        selector.set_modpacks([pack_a, pack_b, pack_c])

        # Deve ter selecionado pack_b automaticamente
        self.assertIsNotNone(selector.selected_pack)
        self.assertEqual(selector.selected_pack.folder_name, "folder_b")
        self.assertEqual(selected[-1].folder_name, "folder_b")

        # Ao trocar para pack_c, deve salvar pack_c
        selector._select_pack_by_index(2)
        self.assertEqual(SettingsService.get_last_modpack(), "folder_c")

        selector.destroy()

    def test_mod_item_size_and_heavy_properties(self):
        mod_light = ModItem(
            id=1, name="Light Mod", slug="light", link="",
            installed_file_id=1, installed_version_name="1.0", installed_jar="light.jar",
            installed_size=500 * 1024  # 500 KB
        )
        self.assertEqual(mod_light.size_display, "500 KB")
        self.assertFalse(mod_light.is_heavy)
        self.assertFalse(mod_light.is_very_heavy)

        mod_heavy = ModItem(
            id=2, name="Create", slug="create", link="",
            installed_file_id=2, installed_version_name="1.0", installed_jar="create.jar",
            installed_size=14 * 1024 * 1024  # 14 MB
        )
        self.assertEqual(mod_heavy.size_display, "14.0 MB")
        self.assertTrue(mod_heavy.is_heavy)
        self.assertTrue(mod_heavy.is_very_heavy)

    def test_mod_list_heavy_sorting_and_filtering(self):
        m1 = ModItem(
            id=1, name="Light Normal", slug="m1", link="",
            installed_file_id=1, installed_version_name="1.0", installed_jar="m1.jar",
            installed_size=1 * 1024 * 1024,
            status=UpdateStatus.UP_TO_DATE
        )
        m2 = ModItem(
            id=2, name="Heavy Confirmed", slug="m2", link="",
            installed_file_id=2, installed_version_name="1.0", installed_jar="m2.jar",
            installed_size=15 * 1024 * 1024,
            status=UpdateStatus.TLAUNCHER_CONFIRMED
        )
        m3 = ModItem(
            id=3, name="Medium Confirmed", slug="m3", link="",
            installed_file_id=3, installed_version_name="1.0", installed_jar="m3.jar",
            installed_size=6 * 1024 * 1024,
            status=UpdateStatus.TLAUNCHER_CONFIRMED
        )
        m4 = ModItem(
            id=4, name="Very Heavy UpToDate", slug="m4", link="",
            installed_file_id=4, installed_version_name="1.0", installed_jar="m4.jar",
            installed_size=25 * 1024 * 1024,
            status=UpdateStatus.UP_TO_DATE
        )

        mod_list = ModList(
            self.root,
            on_mod_selected=lambda m: None,
            on_selection_changed=lambda: None
        )
        mod_list.pack()
        mod_list.set_mods([m1, m2, m3, m4])

        # 1. Ordenação: Confirmados + Mais Pesados
        mod_list.sort_combo.set("Confirmados + Mais Pesados")
        mod_list._refresh()
        while mod_list._render_job:
            self.root.update()

        # Esperado: m2 (15MB confirmado), m3 (6MB confirmado), m4 (25MB em dia), m1 (1MB em dia)
        names_order = [m.name for m in mod_list.visible_mods]
        self.assertEqual(names_order, ["Heavy Confirmed", "Medium Confirmed", "Very Heavy UpToDate", "Light Normal"])

        # 2. Ordenação: Mais Pesados (Tamanho ↓)
        mod_list.sort_combo.set("Mais Pesados (Tamanho ↓)")
        mod_list._refresh()
        while mod_list._render_job:
            self.root.update()
        names_order = [m.name for m in mod_list.visible_mods]
        self.assertEqual(names_order, ["Very Heavy UpToDate", "Heavy Confirmed", "Medium Confirmed", "Light Normal"])

        # 3. Filtro: Confirmados: Pesados (5MB+)
        mod_list.filter_combo.set("Confirmados: Pesados (5MB+)")
        mod_list._refresh()
        while mod_list._render_job:
            self.root.update()
        filtered_names = [m.name for m in mod_list.visible_mods]
        self.assertEqual(filtered_names, ["Heavy Confirmed", "Medium Confirmed"])

        # 4. Filtro: Mods Muito Pesados (10MB+)
        mod_list.filter_combo.set("Mods Muito Pesados (10MB+)")
        mod_list._refresh()
        while mod_list._render_job:
            self.root.update()
        filtered_names = [m.name for m in mod_list.visible_mods]
        self.assertEqual(set(filtered_names), {"Very Heavy UpToDate", "Heavy Confirmed"})

        mod_list.destroy()


if __name__ == "__main__":
    unittest.main()
