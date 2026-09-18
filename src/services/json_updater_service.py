"""
Serviço responsável por:
1. Atualizar o TLauncherAdditional.json com os novos metadados de versão.
2. Excluir o .jar antigo da pasta mods/ para evitar conflitos —
   o TLauncher baixará o novo arquivo ao iniciar.
"""

import time
import os
from pathlib import Path
from typing import List, Tuple
from src.core.models import ModItem, UpdateStatus
from src.core.json_manager import JsonManager
from src.services.update_service import UpdateService


class JsonUpdaterService:

    @staticmethod
    def _delete_old_jar(json_path: str, mod: ModItem) -> tuple[bool, str]:
        """
        Remove o .jar antigo da pasta mods/ adjacente ao JSON.
        Retorna (sucesso, mensagem).
        """
        if not mod.installed_jar:
            return True, ""  # Nada para apagar

        mods_dir = Path(json_path).parent / "mods"
        jar_path = mods_dir / mod.installed_jar

        if not jar_path.exists():
            return True, ""  # Já não existe, ok

        try:
            jar_path.unlink()
            return True, f"🗑 Removido: {mod.installed_jar}"
        except PermissionError:
            return False, f"⚠ Sem permissão para remover: {mod.installed_jar}"
        except Exception as e:
            return False, f"⚠ Erro ao remover {mod.installed_jar}: {e}"

    @staticmethod
    def apply_updates_to_json(
        json_path: str,
        mods_to_update: List[ModItem],
        delete_old_jars: bool = True,
    ) -> Tuple[int, int, str]:
        """
        Aplica as alterações de versão no TLauncherAdditional.json e,
        opcionalmente, exclui os .jar antigos da pasta mods/.

        O TLauncher baixará os novos arquivos ao iniciar o modpack.

        Retorna: (total_atualizados, total_erros, mensagem)
        """
        if not mods_to_update:
            return 0, 0, "Nenhum mod selecionado para atualização."

        # 1. Backup de segurança
        try:
            backup_file = JsonManager.backup_json(json_path)
        except Exception as e:
            return 0, len(mods_to_update), f"Falha ao criar backup do JSON: {e}"

        # 2. Carrega o JSON
        try:
            data = JsonManager.load_json(json_path)
        except Exception as e:
            return 0, len(mods_to_update), f"Falha ao ler o arquivo JSON: {e}"

        raw_mods = data.get("modpack", {}).get("version", {}).get("mods", [])
        if not raw_mods:
            return 0, len(mods_to_update), "A seção modpack.version.mods não foi encontrada no JSON."

        mods_by_id = {item.get("id"): item for item in raw_mods if item.get("id") is not None}

        updated_count = 0
        error_count = 0
        deleted_jars: List[str] = []
        failed_deletes: List[str] = []
        current_timestamp = int(time.time() * 1000)

        for mod in mods_to_update:
            if not mod.tlauncher_available and mod.status != UpdateStatus.TLAUNCHER_CONFIRMED:
                continue
            if not mod.latest_file_id or not mod.latest_jar_name:
                error_count += 1
                continue

            target_raw = mods_by_id.get(mod.id)
            if not target_raw:
                error_count += 1
                continue

            # 3. Remove o .jar antigo ANTES de salvar o JSON
            if delete_old_jars:
                ok, del_msg = JsonUpdaterService._delete_old_jar(json_path, mod)
                if ok and del_msg:
                    deleted_jars.append(mod.installed_jar)
                elif not ok:
                    failed_deletes.append(del_msg)

            # 4. Atualiza o JSON (versão e metadados)
            if "version" not in target_raw or not isinstance(target_raw["version"], dict):
                target_raw["version"] = {}

            ver_dict = target_raw["version"]
            ver_dict["id"] = mod.latest_file_id
            ver_dict["name"] = mod.latest_version_name or mod.latest_jar_name
            ver_dict["updateDate"] = current_timestamp

            if "metadata" not in ver_dict or not isinstance(ver_dict["metadata"], dict):
                ver_dict["metadata"] = {}

            meta = ver_dict["metadata"]
            meta["path"] = f"mods/{mod.latest_jar_name}"
            meta["url"] = f"/mods/{mod.id}/{mod.latest_file_id}/{mod.latest_jar_name}"

            # Garante que o SHA-1 e tamanho do novo arquivo sejam obtidos
            if not mod.latest_sha1 and mod.id and mod.latest_file_id:
                sha1, size = UpdateService.fetch_curseforge_file_hash(mod.id, mod.latest_file_id)
                if sha1:
                    mod.latest_sha1 = sha1
                if size and not mod.latest_size:
                    mod.latest_size = size

            if mod.latest_sha1:
                meta["sha1"] = mod.latest_sha1
            if mod.latest_size:
                meta["size"] = mod.latest_size

            mod.status = UpdateStatus.UPDATED
            mod.installed_file_id = mod.latest_file_id
            mod.installed_version_name = mod.latest_version_name or mod.latest_jar_name
            mod.installed_jar = mod.latest_jar_name
            updated_count += 1

        # 5. Salva o JSON
        try:
            JsonManager.save_json(json_path, data)
        except Exception as e:
            return 0, len(mods_to_update), f"Erro ao salvar alterações no JSON: {e}"

        # Monta mensagem de resultado
        lines = [
            f"✅ {updated_count} mod(s) atualizados no JSON.",
        ]
        if deleted_jars:
            lines.append(f"🗑 {len(deleted_jars)} .jar(s) antigo(s) removidos da pasta mods/.")
        if failed_deletes:
            lines.append("⚠ Alguns arquivos não puderam ser removidos (fechem o Minecraft antes):")
            lines.extend(f"  • {m}" for m in failed_deletes)
        lines.append(f"📦 Backup salvo em: {Path(backup_file).name}")
        lines.append("🎮 O TLauncher baixará as novas versões ao iniciar o modpack.")

        return updated_count, error_count, "\n".join(lines)
