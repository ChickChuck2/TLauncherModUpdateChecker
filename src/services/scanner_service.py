"""
Serviço para descoberta e varredura de modpacks do TLauncher.
"""

import os
from typing import List, Optional
from src.core.config import DEFAULT_MINECRAFT_DIRS, TLAUNCHER_JSON_FILENAME
from src.core.models import ModpackInfo
from src.core.json_manager import JsonManager

class ScannerService:
    @staticmethod
    def find_versions_directory() -> Optional[str]:
        """Localiza a primeira pasta de versões existente."""
        for path in DEFAULT_MINECRAFT_DIRS:
            if os.path.exists(path) and os.path.isdir(path):
                return path
        return None

    @staticmethod
    def scan_modpacks(base_dir: Optional[str] = None) -> List[ModpackInfo]:
        """
        Varre todos os modpacks gerenciados pelo TLauncher dentro do diretório base.
        """
        target_dir = base_dir or ScannerService.find_versions_directory()
        if not target_dir or not os.path.exists(target_dir):
            return []

        modpacks: List[ModpackInfo] = []
        try:
            entries = os.listdir(target_dir)
        except Exception:
            return []

        for entry in entries:
            folder_path = os.path.join(target_dir, entry)
            if not os.path.isdir(folder_path):
                continue

            json_file = os.path.join(folder_path, TLAUNCHER_JSON_FILENAME)
            if os.path.exists(json_file):
                info = JsonManager.parse_modpack(json_file, folder_name=entry)
                if info and info.total_mods > 0:
                    modpacks.append(info)

        return modpacks
