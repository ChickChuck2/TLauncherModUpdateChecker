"""
Serviço responsável por atualizar exclusivamente o arquivo TLauncherAdditional.json,
sem realizar downloads de arquivos binários .jar pelo aplicativo.
"""

import time
from typing import List, Tuple
from src.core.models import ModItem, UpdateStatus
from src.core.json_manager import JsonManager

class JsonUpdaterService:
    @staticmethod
    def apply_updates_to_json(json_path: str, mods_to_update: List[ModItem]) -> Tuple[int, int, str]:
        """
        Aplica as alterações de versão diretamente no TLauncherAdditional.json
        para que o próprio TLauncher realize o download oficial ao iniciar.

        Retorna: (total_atualizados, total_erros, mensagem)
        """
        if not mods_to_update:
            return 0, 0, "Nenhum mod selecionado para atualização."

        # 1. Cria backup de segurança automático
        try:
            backup_file = JsonManager.backup_json(json_path)
        except Exception as e:
            return 0, len(mods_to_update), f"Falha ao criar backup do JSON: {e}"

        # 2. Carrega o arquivo JSON
        try:
            data = JsonManager.load_json(json_path)
        except Exception as e:
            return 0, len(mods_to_update), f"Falha ao ler o arquivo JSON: {e}"

        raw_mods = data.get("modpack", {}).get("version", {}).get("mods", [])
        if not raw_mods:
            return 0, len(mods_to_update), "A seção modpack.version.mods não foi encontrada no JSON."

        # Mapeia mods por ID para busca em O(1)
        mods_by_id = {item.get("id"): item for item in raw_mods if item.get("id") is not None}

        updated_count = 0
        error_count = 0
        current_timestamp = int(time.time() * 1000)

        for mod in mods_to_update:
            if not mod.latest_file_id or not mod.latest_jar_name:
                error_count += 1
                continue

            target_raw = mods_by_id.get(mod.id)
            if not target_raw:
                error_count += 1
                continue

            # Atualiza o objeto de versão
            if "version" not in target_raw or not isinstance(target_raw["version"], dict):
                target_raw["version"] = {}

            ver_dict = target_raw["version"]
            ver_dict["id"] = mod.latest_file_id
            ver_dict["name"] = mod.latest_version_name or mod.latest_jar_name
            ver_dict["updateDate"] = current_timestamp

            # Atualiza metadados do arquivo para o padrão TLauncher
            if "metadata" not in ver_dict or not isinstance(ver_dict["metadata"], dict):
                ver_dict["metadata"] = {}

            meta = ver_dict["metadata"]
            meta["path"] = f"mods/{mod.latest_jar_name}"
            meta["url"] = f"/mods/{mod.id}/{mod.latest_file_id}/{mod.latest_jar_name}"

            if mod.latest_sha1:
                meta["sha1"] = mod.latest_sha1
            if mod.latest_size:
                meta["size"] = mod.latest_size

            mod.status = UpdateStatus.UPDATED
            mod.installed_file_id = mod.latest_file_id
            mod.installed_version_name = mod.latest_version_name or mod.latest_jar_name
            mod.installed_jar = mod.latest_jar_name
            updated_count += 1

        # 3. Salva o arquivo JSON com as alterações aplicadas
        try:
            JsonManager.save_json(json_path, data)
        except Exception as e:
            return 0, len(mods_to_update), f"Erro ao salvar alterações no JSON: {e}"

        msg = (
            f"Sucesso! {updated_count} mod(s) atualizado(s) no arquivo JSON.\n"
            f"Backup salvo em: {backup_file}\n"
            f"Ao abrir o TLauncher, o download oficial dessas versões será acionado automaticamente!"
        )
        return updated_count, error_count, msg
