"""
Serviço de atualização de Resource Packs e Shader Packs via modificação do JSON.

Regra de ouro:
    O campo `stateGameElement` ("active" / "no_active") é SEMPRE copiado do
    registro existente para a versão atualizada. Nunca é sobrescrito.
"""

import json
import shutil
from pathlib import Path
from typing import List, Tuple
from src.core.models import AddonType, AddonUpdateStatus
from src.core.addon_models import AddonItem
from src.services.update_service import UpdateService


class AddonUpdaterService:

    @staticmethod
    def apply_updates(
        json_path: str,
        addons_to_update: List[AddonItem],
    ) -> Tuple[int, int, str]:
        """
        Atualiza os metadados de versão dos addons no JSON.

        Preserva SEMPRE:
          - stateGameElement  → estado ativo/inativo no jogo
          - favorite          → favorito do usuário
          - userInstall       → instalação manual

        Retorna: (n_success, n_errors, message)
        """
        json_path_obj = Path(json_path)

        # Backup atômico
        backup_path = json_path_obj.with_suffix(".json.bak")
        shutil.copy2(json_path_obj, backup_path)

        try:
            with open(json_path_obj, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return 0, len(addons_to_update), f"Erro ao ler JSON: {e}"

        success_count = 0
        error_count = 0

        for addon in addons_to_update:
            if addon.status not in (AddonUpdateStatus.UPDATE_AVAILABLE, AddonUpdateStatus.TLAUNCHER_OK):
                continue
            if not addon.latest_file_id or not addon.latest_version_name:
                error_count += 1
                continue

            raw_list = data.get("modpack", {}).get("version", {}).get(addon.addon_type.json_key, [])
            updated = False

            for entry in raw_list:
                if entry.get("id") != addon.id:
                    continue

                # ── Preserva o estado ativo (CRÍTICO) ──────────────────────
                state_preserved = entry.get("stateGameElement", "no_active")
                # ────────────────────────────────────────────────────────────

                # Atualiza apenas os metadados de versão
                ver = entry.setdefault("version", {})
                meta = ver.setdefault("metadata", {})

                old_id = ver.get("id")
                old_name = ver.get("name", "")

                ver["id"] = addon.latest_file_id
                ver["name"] = addon.latest_version_name
                ver["available"] = False
                ver["remove"] = False

                # Garante que o SHA-1 e tamanho do novo arquivo sejam obtidos
                if not addon.latest_sha1 and addon.id and addon.latest_file_id:
                    sha1, size = UpdateService.fetch_curseforge_file_hash(addon.id, addon.latest_file_id)
                    if sha1:
                        addon.latest_sha1 = sha1
                    if size and not addon.latest_size:
                        addon.latest_size = size

                if addon.latest_sha1:
                    meta["sha1"] = addon.latest_sha1
                if addon.latest_size:
                    meta["size"] = addon.latest_size
                if addon.latest_url:
                    meta["url"] = addon.latest_url
                    # Atualiza o path local baseado no nome do arquivo
                    file_name = addon.latest_url.split("/")[-1]
                    meta["path"] = f"{addon.addon_type.folder}/{file_name}"

                # ── Garante que stateGameElement foi preservado ──────────────
                entry["stateGameElement"] = state_preserved
                # ────────────────────────────────────────────────────────────

                addon.status = AddonUpdateStatus.UPDATED
                addon.installed_file_id = addon.latest_file_id
                addon.installed_version_name = addon.latest_version_name
                success_count += 1
                updated = True
                break

            if not updated:
                error_count += 1

        try:
            with open(json_path_obj, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Restaura backup em caso de falha
            shutil.copy2(backup_path, json_path_obj)
            return 0, len(addons_to_update), f"Erro ao salvar JSON: {e}"

        if success_count > 0 and error_count == 0:
            msg = (f"✅ {success_count} addon(s) atualizados no JSON.\n"
                   f"O estado ativo/inativo foi preservado para todos.\n"
                   f"Backup salvo em: {backup_path.name}")
        elif success_count > 0:
            msg = (f"⚠️ {success_count} atualizados, {error_count} erro(s).\n"
                   f"Estado ativo preservado nos que foram atualizados.")
        else:
            msg = f"❌ Nenhum addon atualizado. {error_count} erro(s)."

        return success_count, error_count, msg
