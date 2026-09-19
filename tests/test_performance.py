"""
Testes de desempenho e integridade da reciclagem de widgets e renderização progressiva.
"""

import unittest
import time
import customtkinter as ctk
from src.core.models import ModItem, UpdateStatus
from src.core.addon_models import AddonItem, AddonType, AddonUpdateStatus
from src.ui.components.mod_list import ModList, ModCard
from src.ui.components.addon_list import AddonList, AddonCard


class TestPerformanceAndRecycling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cria uma janela CTk oculta para hospedar os componentes
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.update_idletasks()
            cls.root.destroy()
        except Exception:
            pass

    def _generate_mods(self, count: int = 230):
        mods = []
        for i in range(count):
            mods.append(ModItem(
                id=1000 + i,
                name=f"Performance Mod {i:03d}",
                slug=f"perf-mod-{i}",
                link=f"https://curseforge.com/minecraft/mc-mods/perf-mod-{i}",
                installed_file_id=5000 + i,
                installed_version_name="1.0.0",
                installed_jar=f"perf-mod-{i}-1.0.0.jar",
                status=UpdateStatus.UPDATE_AVAILABLE if i % 3 == 0 else UpdateStatus.UP_TO_DATE,
                total_downloads=1000 * i,
                selected=False
            ))
        return mods

    def _generate_addons(self, count: int = 100):
        addons = []
        for i in range(count):
            addons.append(AddonItem(
                id=2000 + i,
                name=f"Texture Pack {i:03d}",
                slug=f"texture-pack-{i}",
                link=f"https://curseforge.com/minecraft/texture-packs/texture-pack-{i}",
                addon_type=AddonType.RESOURCE_PACK,
                state_game_element="active" if i % 2 == 0 else "no_active",
                installed_file_id=6000 + i,
                installed_version_name="1.0.0",
                installed_path=f"resourcepacks/TexturePack{i}.zip",
                installed_url=f"/resourcepacks/2000/{6000+i}/TexturePack{i}.zip",
                status=AddonUpdateStatus.UPDATE_AVAILABLE if i % 2 == 0 else AddonUpdateStatus.UP_TO_DATE,
                total_downloads=500 * i,
                popularity=100 * i,
                selected=False
            ))
        return addons

    def test_mod_list_widget_pooling_and_speed(self):
        selected_mods = []
        mod_list = ModList(
            self.root,
            on_mod_selected=lambda m: selected_mods.append(m),
            on_selection_changed=lambda: None
        )
        mod_list.pack()

        mods_230 = self._generate_mods(230)

        # 1. Primeira carga de 230 mods (primeiro lote imediato)
        t0 = time.perf_counter()
        mod_list.set_mods(mods_230)
        t_first_chunk = time.perf_counter() - t0

        # O primeiro chunk de 35 deve ser renderizado instantaneamente (< 0.25s)
        self.assertLess(t_first_chunk, 0.40, f"Primeiro lote demorou {t_first_chunk:.3f}s, esperado < 0.40s")
        self.assertEqual(len(mod_list.cards), ModList.CHUNK_SIZE)
        self.assertEqual(len(mod_list._card_pool), ModList.CHUNK_SIZE)

        # Processa os eventos pendentes para terminar todos os lotes em segundo plano
        while mod_list._render_job:
            self.root.update()

        self.assertEqual(len(mod_list.cards), 230)
        self.assertEqual(len(mod_list._card_pool), 230)

        # 2. Teste de reciclagem: trocar ou reordenar deve ser muito mais rápido que criar do zero
        t0 = time.perf_counter()
        # Inverte ordem dos mods
        mod_list.set_mods(list(reversed(mods_230)))
        t_recycle_first = time.perf_counter() - t0
        self.assertLess(t_recycle_first, 0.40, f"Reciclagem do primeiro chunk demorou {t_recycle_first:.3f}s")

        while mod_list._render_job:
            self.root.update()

        # O pool não deve ter duplicado: exatamente 230 widgets mantidos
        self.assertEqual(len(mod_list._card_pool), 230)
        self.assertEqual(len(mod_list.cards), 230)
        # Primeiro card agora é o último mod (nome decrescente)
        self.assertEqual(mod_list.cards[0].mod.name, "Performance Mod 229")

        # 3. Teste de busca com debounce
        mod_list.search.delete(0, "end")
        mod_list.search.insert(0, "005")
        mod_list._on_search_key()
        self.assertIsNotNone(mod_list._search_timer)

        # Dispara o timer do debounce
        mod_list._refresh()
        while mod_list._render_job:
            self.root.update()

        self.assertEqual(len(mod_list.cards), 1)
        self.assertEqual(mod_list.cards[0].mod.name, "Performance Mod 005")
        # Os outros 229 cards permanecem no pool em pack_forget
        self.assertEqual(len(mod_list._card_pool), 230)

        # 4. Limpar busca restaura todos usando o pool
        mod_list.search.delete(0, "end")
        mod_list._refresh()
        while mod_list._render_job:
            self.root.update()
        self.assertEqual(len(mod_list.cards), 230)
        self.assertEqual(len(mod_list._card_pool), 230)

        # 5. Teste de seleção e marcação de updates
        mod_list._select_all_updates()
        while mod_list._render_job:
            self.root.update()

        selected = mod_list.get_selected_mods()
        expected_selected_count = sum(1 for m in mods_230 if m.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED))
        self.assertEqual(len(selected), expected_selected_count)

        self.root.update_idletasks()
        mod_list.destroy()

    def test_addon_list_widget_pooling(self):
        addon_list = AddonList(
            self.root,
            on_addon_selected=lambda a: None,
            on_selection_changed=lambda: None
        )
        addon_list.pack()

        addons_100 = self._generate_addons(100)
        addon_list.set_addons(addons_100)

        # Finaliza renderização de segundo plano
        while addon_list._render_job:
            self.root.update()

        self.assertEqual(len(addon_list.cards), 100)
        self.assertEqual(len(addon_list._card_pool), 100)

        # Filtro
        addon_list.filter_combo.set("Com Atualização")
        addon_list._refresh()
        while addon_list._render_job:
            self.root.update()

        self.assertEqual(len(addon_list.cards), 50)
        self.assertEqual(len(addon_list._card_pool), 100)

        self.root.update_idletasks()
        addon_list.destroy()


if __name__ == "__main__":
    unittest.main()
