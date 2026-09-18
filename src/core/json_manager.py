"""
Gerenciador de I/O e manipulação segura do TLauncherAdditional.json.
"""

import json
import os
import shutil
import tempfile
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
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
        """
        Cria cópia de segurança dupla e à prova de falhas antes de qualquer alteração:
        1. Cópia padrão filepath.bak (para restauração rápida do launcher).
        2. Cópia histórica imutável com timestamp no diretório .tlauncher_backups/
           ex: .tlauncher_backups/TLauncherAdditional_20260918_060530.json
        Valida tamanho em bytes e existência de ambos os arquivos antes de liberar o fluxo.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo original para backup não encontrado: {filepath}")

        src_size = os.path.getsize(filepath)
        if src_size == 0:
            raise ValueError(f"Arquivo original está vazio (0 bytes): {filepath}")

        # 1. Backup padrão .bak
        backup_path = filepath + ".bak"
        shutil.copy2(filepath, backup_path)
        if not os.path.exists(backup_path) or os.path.getsize(backup_path) != src_size:
            raise RuntimeError(f"Falha de integridade ao criar backup padrão: {backup_path}")

        # 2. Backup histórico com timestamp no diretório .tlauncher_backups/
        parent_dir = os.path.dirname(filepath)
        backups_dir = os.path.join(parent_dir, ".tlauncher_backups")
        os.makedirs(backups_dir, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        hist_name = f"TLauncherAdditional_{timestamp_str}.json"
        hist_path = os.path.join(backups_dir, hist_name)
        shutil.copy2(filepath, hist_path)

        if not os.path.exists(hist_path) or os.path.getsize(hist_path) != src_size:
            raise RuntimeError(f"Falha de integridade ao criar backup histórico: {hist_path}")

        return hist_path

    @staticmethod
    def save_json(filepath: str, data: Dict[str, Any]) -> bool:
        """
        Salva o JSON de forma atômica e validada para evitar corrupção de arquivo:
        1. Escreve em arquivo temporário no mesmo volume/diretório.
        2. Valida se o arquivo temporário pode ser lido e possui JSON íntegro.
        3. Substituição atômica segura no Windows com os.replace.
        """
        dir_name = os.path.dirname(filepath)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp_file:
                json.dump(data, tmp_file, indent=2, ensure_ascii=False)
                temp_name = tmp_file.name

            # Validação pós-escrita antes de substituir o arquivo original
            with open(temp_name, "r", encoding="utf-8") as f_check:
                check_data = json.load(f_check)
                if not isinstance(check_data, dict):
                    raise ValueError("Dados gerados no arquivo temporário não formam um objeto JSON válido.")

            # Substituição atômica segura no Windows
            if os.path.exists(filepath):
                os.replace(temp_name, filepath)
            else:
                shutil.move(temp_name, filepath)
            return True
        except Exception as e:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            raise e

    @staticmethod
    def restore_backup(filepath: str, backup_path: Optional[str] = None) -> bool:
        """Restaura o arquivo JSON a partir de um backup específico ou do .bak padrão."""
        target_backup = backup_path or (filepath + ".bak")
        if not os.path.exists(target_backup):
            raise FileNotFoundError(f"Arquivo de backup não encontrado: {target_backup}")
        shutil.copy2(target_backup, filepath)
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

            # Metadados visuais e informativos já presentes no JSON do TLauncher
            pic = raw.get("picture")
            icon_url = f"https://rescl.tlauncher.org/b/pictures/compress/{pic}.png" if pic else None

            raw_pics = raw.get("pictures", [])
            screenshot_urls = [
                f"https://rescl.tlauncher.org/b/pictures/max/{p}.png"
                for p in raw_pics if p
            ] if isinstance(raw_pics, list) else []

            total_dl = raw.get("downloadALL", 0) or raw.get("download_count", 0) or 0
            monthly_dl = raw.get("downloadMonth", 0) or 0

            author_val = raw.get("author")
            authors = [author_val] if isinstance(author_val, str) and author_val else []

            cats_raw = raw.get("categories", [])
            categories = [
                c.get("name") or c.get("shortName")
                for c in cats_raw
                if isinstance(c, dict) and (c.get("name") or c.get("shortName"))
            ] if isinstance(cats_raw, list) else []

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
                selected=False,
                icon_url=icon_url,
                screenshot_urls=screenshot_urls,
                total_downloads=total_dl,
                monthly_downloads=monthly_dl,
                authors=authors,
                categories=categories,
            ))

        return ModpackInfo(
            name=pack_name,
            folder_name=folder_name,
            json_path=json_path,
            game_version=game_ver,
            loader=loader,
            mods=mod_items
        )
