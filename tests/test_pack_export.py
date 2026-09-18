import os
import unittest
import tempfile
import zipfile
from src.services.pack_export_service import PackExportService


class TestPackExportService(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Cria arquivos fictícios do modpack
        with open(os.path.join(self.test_dir, "TLauncherAdditional.json"), "w", encoding="utf-8") as f:
            f.write('{"test": true}')
        with open(os.path.join(self.test_dir, "options.txt"), "w", encoding="utf-8") as f:
            f.write('fov:70')
        cfg_dir = os.path.join(self.test_dir, "config")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "mod.cfg"), "w", encoding="utf-8") as f:
            f.write('enabled=true')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_build_sync_zip(self):
        zip_path, file_count, size_kb, elapsed_ms = PackExportService.build_sync_zip(self.test_dir, force_rebuild=True)
        self.assertTrue(os.path.exists(zip_path))
        self.assertEqual(file_count, 3)
        self.assertGreater(size_kb, 0)
        
        # Valida conteúdo do ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            self.assertIn("TLauncherAdditional.json", names)
            self.assertIn("options.txt", names)
            self.assertIn("config/mod.cfg", names)


if __name__ == "__main__":
    unittest.main()
