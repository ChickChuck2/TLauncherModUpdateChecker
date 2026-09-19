"""
Testes automatizados para BackupService.
"""

import unittest
import os
import json
import tempfile
from pathlib import Path
from src.services.backup_service import BackupService


class TestBackupService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pack_dir = Path(self.temp_dir.name)
        self.json_path = str(self.pack_dir / "TLauncherAdditional.json")

        self.initial_data = {
            "modpack": {
                "name": "TestPack",
                "version": {"gameVersionDTO": {"name": "1.20.1"}, "mods": []}
            }
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f, indent=2)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_list_backups(self):
        # 1. Cria backup manual
        created_file = BackupService.create_manual_backup(self.json_path)
        self.assertTrue(os.path.exists(created_file))
        self.assertTrue(created_file.endswith(".json"))

        # 2. Cria também um .bak simulando o launcher
        quick_bak = self.pack_dir / "TLauncherAdditional.json.bak"
        with open(quick_bak, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f)

        # 3. Lista backups
        backups = BackupService.list_backups(self.json_path)
        self.assertGreaterEqual(len(backups), 2)
        names = [b["name"] for b in backups]
        self.assertTrue(any("manual_" in n for n in names))
        self.assertTrue(any("TLauncherAdditional.json.bak" in n for n in names))

    def test_export_backups(self):
        # Cria 2 backups
        BackupService.create_manual_backup(self.json_path)
        BackupService.create_manual_backup(self.json_path)

        export_target = self.pack_dir / "ExportTarget"
        export_target.mkdir()

        count, export_folder = BackupService.export_backups(
            self.json_path,
            str(export_target),
            pack_name="TestPack"
        )

        self.assertGreaterEqual(count, 3)  # atual + 2 snapshots
        self.assertTrue(os.path.exists(export_folder))
        exported_files = list(Path(export_folder).glob("*.json"))
        self.assertEqual(len(exported_files), count)

    def test_restore_backup(self):
        # 1. Cria backup do estado original
        original_backup = BackupService.create_manual_backup(self.json_path)

        # 2. Modifica o JSON original
        modified_data = {"modpack": {"name": "MODIFIED_NAME", "version": {}}}
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(modified_data, f, indent=2)

        # 3. Restaura a partir do backup
        success = BackupService.restore_backup(self.json_path, original_backup)
        self.assertTrue(success)

        # 4. Valida se o conteúdo voltou ao original
        with open(self.json_path, "r", encoding="utf-8") as f:
            restored_data = json.load(f)
        self.assertEqual(restored_data["modpack"]["name"], "TestPack")


if __name__ == "__main__":
    unittest.main()
