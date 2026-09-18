"""
Testes de Integração e Validação dos Módulos Core e Serviços.
"""

import os
import sys
import unittest
import tempfile
import json
import shutil

# Adiciona o diretório base ao sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models import ModItem, UpdateStatus
from src.core.json_manager import JsonManager
from src.services.scanner_service import ScannerService
from src.services.update_service import UpdateService
from src.services.json_updater_service import JsonUpdaterService

REAL_JSON_PATH = r"D:\Games\.minecraft\versions\UltimateMinePack\TLauncherAdditional.json"

class TestIntegration(unittest.TestCase):
    def test_01_scanner_service(self):
        """Valida se o scanner localiza modpacks válidos."""
        packs = ScannerService.scan_modpacks()
        self.assertGreater(len(packs), 0, "Deveria encontrar ao menos 1 modpack com TLauncherAdditional.json")
        pack_names = [p.name for p in packs]
        print(f"Modpacks encontrados: {pack_names}")
        self.assertIn("HorrorHardcoreZoio 2", pack_names)

    def test_02_parse_modpack(self):
        """Valida o parse correto do modpack e dos mods."""
        if not os.path.exists(REAL_JSON_PATH):
            self.skipTest("Arquivo real não disponível")

        pack = JsonManager.parse_modpack(REAL_JSON_PATH, "UltimateMinePack")
        self.assertIsNotNone(pack)
        self.assertEqual(pack.game_version, "1.20.1")
        self.assertEqual(pack.loader, "forge")
        self.assertGreaterEqual(len(pack.mods), 230)

    def test_03_tlauncher_url_availability(self):
        """Valida que o repositório oficial do TLauncher responde com o novo arquivo do CurseForge."""
        # Chisels & Bits (ID: 231095, File ID: 7620767)
        available = UpdateService.check_tlauncher_availability(
            project_id=231095,
            file_id=7620767,
            jar_name="chisels-and-bits-forge-20.1.20.jar"
        )
        self.assertTrue(available, "O arquivo oficial no repo do TLauncher deve responder 200 OK")

    def test_04_json_updater_simulation(self):
        """Testa a alteração no JSON em um arquivo temporário de teste, sem afetar o arquivo real."""
        if not os.path.exists(REAL_JSON_PATH):
            self.skipTest("Arquivo real não disponível")

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_json = os.path.join(tmp_dir, "TLauncherAdditional.json")
            shutil.copy2(REAL_JSON_PATH, test_json)

            # Mod simulado para atualizar
            dummy_mod = ModItem(
                id=231095,
                name="Chisels & Bits - For Forge",
                slug="chisels-and-bits",
                link="https://curseforge.com",
                installed_file_id=5203366,
                installed_version_name="chisels-and-bits-forge-1.4.148",
                installed_jar="chisels-and-bits-forge-1.4.148.jar",
                latest_file_id=7620767,
                latest_version_name="chisels-and-bits-forge-20.1.20",
                latest_jar_name="chisels-and-bits-forge-20.1.20.jar",
                status=UpdateStatus.TLAUNCHER_CONFIRMED
            )

            success, errors, msg = JsonUpdaterService.apply_updates_to_json(test_json, [dummy_mod])
            self.assertEqual(success, 1)
            self.assertEqual(errors, 0)
            self.assertTrue(os.path.exists(test_json + ".bak"), "Backup .bak deve ser criado")

            # Verifica se o arquivo JSON modificado contém os novos dados
            with open(test_json, "r", encoding="utf-8") as f:
                modified_data = json.load(f)

            raw_mods = modified_data["modpack"]["version"]["mods"]
            target = next(m for m in raw_mods if m.get("id") == 231095)
            self.assertEqual(target["version"]["id"], 7620767)
            self.assertEqual(target["version"]["metadata"]["path"], "mods/chisels-and-bits-forge-20.1.20.jar")
            self.assertEqual(target["version"]["metadata"]["url"], "/mods/231095/7620767/chisels-and-bits-forge-20.1.20.jar")

if __name__ == "__main__":
    unittest.main()
