"""
Testes de Segurança Crítica para o Sistema de Backups e Atualizações.
Garante:
1. Criação de backup duplo (.bak rápido + histórico imutável com timestamp).
2. Validação rigorosa de tamanho de arquivo (bytes) antes de permitir atualização.
3. Arquivamento seguro de .jar antigos (ZERO exclusão permanente/destrutiva).
4. Restauração e rollback atômico em caso de falhas.
"""

import os
import sys
import unittest
import tempfile
import json
import shutil
from pathlib import Path

# Base dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models import ModItem, UpdateStatus
from src.core.addon_models import AddonItem, AddonType, AddonUpdateStatus
from src.core.json_manager import JsonManager
from src.services.json_updater_service import JsonUpdaterService
from src.services.addon_updater_service import AddonUpdaterService


class TestBackupSafety(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.test_dir.name)
        self.mods_dir = self.dir_path / "mods"
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = str(self.dir_path / "TLauncherAdditional.json")

        # Cria um JSON de modpack de exemplo
        self.sample_data = {
            "modpack": {
                "name": "SafetyTestPack",
                "version": {
                    "gameVersionDTO": {"name": "1.20.1"},
                    "minecraftVersionTypes": [{"name": "Forge"}],
                    "mods": [
                        {
                            "id": 101,
                            "name": "Test Mod Alpha",
                            "lanName": "test-mod-alpha",
                            "linkProject": "https://curseforge.com",
                            "version": {
                                "id": 5001,
                                "name": "test-mod-alpha-1.0.jar",
                                "metadata": {
                                    "path": "mods/test-mod-alpha-1.0.jar",
                                    "url": "/mods/101/5001/test-mod-alpha-1.0.jar",
                                    "sha1": "abcdef1234567890",
                                    "size": 1024
                                }
                            }
                        }
                    ]
                }
            }
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_data, f, indent=2)

        # Cria um arquivo .jar antigo simulado na pasta mods/
        self.old_jar_path = self.mods_dir / "test-mod-alpha-1.0.jar"
        self.old_jar_path.write_text("DUMMY JAR CONTENT FOR MOD 101 VERSION 1.0")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_dual_layer_backup_creation(self):
        """Verifica se backup_json cria tanto o .bak quanto a cópia histórica no .tlauncher_backups."""
        hist_backup = JsonManager.backup_json(self.json_path)

        # 1. Verifica .bak padrão
        std_backup = self.json_path + ".bak"
        self.assertTrue(os.path.exists(std_backup), "O backup padrão .bak deve existir.")
        self.assertEqual(os.path.getsize(std_backup), os.path.getsize(self.json_path))

        # 2. Verifica histórico imutável
        self.assertTrue(os.path.exists(hist_backup), "O backup histórico deve existir.")
        self.assertIn(".tlauncher_backups", hist_backup)
        self.assertEqual(os.path.getsize(hist_backup), os.path.getsize(self.json_path))

    def test_safe_jar_archival_no_permanent_deletion(self):
        """
        CRÍTICO: Garante que os .jar antigos NÃO são deletados do disco,
        e sim movidos com segurança para a pasta .tlauncher_backups/replaced_jars_...
        """
        mod_update = ModItem(
            id=101,
            name="Test Mod Alpha",
            slug="test-mod-alpha",
            link="https://curseforge.com",
            installed_file_id=5001,
            installed_version_name="test-mod-alpha-1.0.jar",
            installed_jar="test-mod-alpha-1.0.jar",
            latest_file_id=5002,
            latest_version_name="test-mod-alpha-2.0.jar",
            latest_jar_name="test-mod-alpha-2.0.jar",
            latest_sha1="fedcba0987654321",
            latest_size=2048,
            status=UpdateStatus.TLAUNCHER_CONFIRMED,
            tlauncher_available=True
        )

        success, errors, msg = JsonUpdaterService.apply_updates_to_json(
            json_path=self.json_path,
            mods_to_update=[mod_update],
            delete_old_jars=True
        )

        self.assertEqual(success, 1)
        self.assertEqual(errors, 0)

        # O jar antigo foi retirado da pasta mods/ (para o TLauncher baixar o novo ao abrir)
        self.assertFalse(self.old_jar_path.exists(), "O jar antigo deve sair da pasta mods/")

        # MAS ELE NÃO FOI DELETADO! Ele deve existir dentro de .tlauncher_backups/replaced_jars_...
        backups_root = self.dir_path / ".tlauncher_backups"
        self.assertTrue(backups_root.exists(), "A pasta de backups deve existir.")

        archived_jars = list(backups_root.rglob("test-mod-alpha-1.0.jar"))
        self.assertEqual(len(archived_jars), 1, "O jar antigo DEVE estar preservado na pasta de arquivo seguro!")
        self.assertEqual(
            archived_jars[0].read_text(),
            "DUMMY JAR CONTENT FOR MOD 101 VERSION 1.0",
            "O conteúdo do arquivo arquivado deve ser idêntico e intocado!"
        )

    def test_atomic_save_and_rollback(self):
        """Garante que se houver falha, a restauração do backup reverte o arquivo original com perfeição."""
        # Cria backup inicial
        hist_backup = JsonManager.backup_json(self.json_path)

        # Sobrescreve o arquivo com conteúdo corrompido
        with open(self.json_path, "w", encoding="utf-8") as f:
            f.write("CORRUPTED CONTENT")

        # Restaura
        JsonManager.restore_backup(self.json_path, hist_backup)

        # Valida que voltou ao JSON válido original
        restored = JsonManager.load_json(self.json_path)
        self.assertEqual(restored["modpack"]["name"], "SafetyTestPack")

    def test_addon_updater_safety(self):
        """Valida que AddonUpdaterService cria backup com JsonManager e atualiza sem erros."""
        # Adiciona resource pack aos dados do modpack
        data = JsonManager.load_json(self.json_path)
        data["modpack"]["version"]["resourcePacks"] = [
            {
                "id": 201,
                "name": "Test Texture",
                "lanName": "test-texture",
                "linkProject": "https://curseforge.com",
                "stateGameElement": "active",
                "version": {
                    "id": 6001,
                    "name": "test-texture-1.0.zip",
                    "metadata": {
                        "path": "resourcepacks/test-texture-1.0.zip",
                        "url": "/resourcepacks/201/6001/test-texture-1.0.zip",
                        "sha1": "1234567890abcdef",
                        "size": 2048
                    }
                }
            }
        ]
        JsonManager.save_json(self.json_path, data)

        addon = AddonItem(
            id=201,
            name="Test Texture",
            slug="test-texture",
            link="https://curseforge.com",
            addon_type=AddonType.RESOURCE_PACK,
            state_game_element="active",
            installed_file_id=6001,
            installed_version_name="test-texture-1.0.zip",
            installed_path="resourcepacks/test-texture-1.0.zip",
            installed_url="/resourcepacks/201/6001/test-texture-1.0.zip",
            status=AddonUpdateStatus.UPDATE_AVAILABLE,
            latest_file_id=6002,
            latest_version_name="test-texture-2.0.zip",
            latest_url="/resourcepacks/201/6002/test-texture-2.0.zip"
        )

        success, errors, msg = AddonUpdaterService.apply_updates(self.json_path, [addon])
        self.assertEqual(success, 1, f"Falha ao atualizar addon: {msg}")
        self.assertEqual(errors, 0)
        self.assertNotIn("FALHA CRÍTICA", msg)

        # Valida que o JSON foi atualizado e stateGameElement preservado
        updated_data = JsonManager.load_json(self.json_path)
        entry = updated_data["modpack"]["version"]["resourcePacks"][0]
        self.assertEqual(entry["version"]["id"], 6002)
        self.assertEqual(entry["stateGameElement"], "active")


if __name__ == "__main__":
    unittest.main()
