"""
Gerenciador de I/O e manipulação segura do TLauncherAdditional.json.
"""

import json
import os
import shutil
import tempfile
from typing import Optional, Tuple, Dict, Any, List
from src.core.models import ModpackInfo, ModItem, UpdateStatus

class JsonManager:
    @staticmethod
    def load_json(filepath: str) -> Dict[str, Any]:
        """Carrega o arquivo JSON do TLauncher."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def backup_json(filepath: str) -> str:
        """Cria uma cópia de segurança .bak antes de qualquer alteração."""
        backup_path = filepath + ".bak"
        shutil.copy2(filepath, backup_path)
        return backup_path

    @staticmethod
    def save_json(filepath: str, data: Dict[str, Any]) -> bool:
        """
        Salva o JSON de forma atômica para evitar corrupção de arquivo.
        """
        dir_name = os.path.dirname(filepath)
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp_file:
            json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            temp_name = tmp_file.name

        # Substituição atômica segura no Windows
        if os.path.exists(filepath):
            os.replace(temp_name, filepath)
        else:
            shutil.move(temp_name, filepath)
        return True

    @staticmethod
    def parse_modpack(json_path: str, folder_name: str) -> Optional[ModpackInfo]:
        """
        Analisa o TLauncherAdditional.json e converte em ModpackInfo.
        """
        try:
            data = JsonManager.load_json(json_path)
        except Exception:
            return None

        modpack = data.get("modpack", {})
        pack_name = modpack.get("name") or folder_name
        version_data = modpack.get("version", {})

        # Versão do jogo e loader
        game_ver = version_data.get("gameVersionDTO", {}).get("name", "1.20.1")
        loaders = [t.get("name", "").lower() for t in version_data.get("minecraftVersionTypes", [])]
        loader = loaders[0] if loaders else "forge"

        raw_mods = version_data.get("mods", [])
        if not raw_mods:
            return None

        mod_items: List[ModItem] = []
        for raw in raw_mods:
            mod_id = raw.get("id")
            name = raw.get("name", "Sem Nome")
            slug = raw.get("lanName", "")
            link = raw.get("linkProject", "")
            user_install = raw.get("userInstall", False)

            ver_obj = raw.get("version", {})
            file_id = ver_obj.get("id")
            ver_name = ver_obj.get("name", "")
            meta = ver_obj.get("metadata", {})
            file_path = meta.get("path", "")
            sha1 = meta.get("sha1", "")
            size = meta.get("size", 0)

            # Mods gerados pelo Sinytra Connector ou sem ID
            is_local = (mod_id is None) or (mod_id < 0) or user_install
            status = UpdateStatus.LOCAL_ONLY if is_local else UpdateStatus.PENDING

            mod_items.append(ModItem(
                id=mod_id if mod_id is not None else -1,
                name=name,
                slug=slug,
                link=link,
                installed_file_id=file_id,
                installed_version_name=ver_name,
                installed_jar=os.path.basename(file_path),
                installed_sha1=sha1,
                installed_size=size,
                user_install=user_install,
                status=status,
                selected=False
            ))

        return ModpackInfo(
            name=pack_name,
            folder_name=folder_name,
            json_path=json_path,
            game_version=game_ver,
            loader=loader,
            mods=mod_items
        )
