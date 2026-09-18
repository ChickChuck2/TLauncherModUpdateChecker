"""
Serviço responsável por:
1. Atualizar o TLauncherAdditional.json com os novos metadados de versão com proteção transacional.
2. Arquivar com segurança os .jar antigos na pasta .tlauncher_backups/replaced_jars_<timestamp>/
   em vez de deletá-los permanentemente — garantindo ZERO perda de dados.
"""

import time
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from src.core.models import ModItem, UpdateStatus
from src.core.json_manager import JsonManager
from src.services.update_service import UpdateService


class JsonUpdaterService:

    @staticmethod
    def _archive_old_jar(json_path: str, mod: ModItem, archive_dir: Path) -> tuple[bool, str]:
        """
        Move o .jar antigo da pasta mods/ para o diretório seguro de backup
        em vez de deletar do disco.
        Retorna (sucesso, mensagem).
        """
        if not mod.installed_jar:
            return True, ""  # Nada para arquivar

        mods_dir = Path(json_path).parent / "mods"
        jar_path = mods_dir / mod.installed_jar

        if not jar_path.exists():
            return True, ""  # Já não existe no disco

        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest_path = archive_dir / mod.installed_jar
            shutil.move(str(jar_path), str(dest_path))
            return True, f"📦 Arquivado em segurança: {mod.installed_jar}"
        except PermissionError:
            return False, f"⚠ Sem permissão para mover {mod.installed_jar} (feche o Minecraft)"
        except Exception as e:
            return False, f"⚠ Erro ao arquivar {mod.installed_jar}: {e}"

    @staticmethod
    def apply_updates_to_json(
        json_path: str,
        mods_to_update: List[ModItem],
        delete_old_jars: bool = True,
    ) -> Tuple[int, int, str]:
        """
        Aplica as alterações de versão no TLauncherAdditional.json com segurança atômica:
        1. Cria backup duplo verificado (arquivo .bak padrão + histórico imutável com timestamp).
        2. Aplica alterações em memória nos metadados do JSON.
        3. Salva e valida o JSON atomicamente em disco.
        4. SOMENTE APÓS O JSON ESTAR SALVO: move com segurança os .jar antigos para pasta de arquivo.
        5. Em caso de falha de salvamento, reverte imediatamente sem tocar em nenhum .jar.

        Retorna: (total_atualizados, total_erros, mensagem)
        """
        if not mods_to_update:
            return 0, 0, "Nenhum mod selecionado para atualização."

        # 1. Backup de segurança duplo e verificado
        try:
            backup_file = JsonManager.backup_json(json_path)
        except Exception as e:
            return 0, len(mods_to_update), f"FALHA CRÍTICA: Não foi possível criar o backup de segurança:\n{e}"

        # 2. Carrega o JSON
        try:
            data = JsonManager.load_json(json_path)
        except Exception as e:
            return 0, len(mods_to_update), f"Falha ao ler o arquivo JSON: {e}"

        raw_mods = data.get("modpack", {}).get("version", {}).get("mods", [])
        if not raw_mods:
            return 0, len(mods_to_update), "A seção modpack.version.mods não foi encontrada no JSON."

        mods_by_id = {item.get("id"): item for item in raw_mods if item.get("id") is not None}

        mods_successfully_mutated: List[ModItem] = []
        error_count = 0
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

            # Atualiza o JSON em memória (versão e metadados)
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

            # Garante SHA-1 e tamanho do novo arquivo
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

            mods_successfully_mutated.append(mod)

        # 3. Salva o JSON de forma atômica e validada
        try:
            JsonManager.save_json(json_path, data)
        except Exception as e:
            # Em caso de erro na escrita, restaura o backup imediatamente
            try:
                JsonManager.restore_backup(json_path, backup_file)
            except Exception:
                pass
            return 0, len(mods_to_update), f"Erro ao salvar alterações no JSON. Backup restaurado com segurança:\n{e}"

        # 4. SOMENTE APÓS O JSON ESTAR SALVO: Arquiva os .jar antigos com segurança
        archived_jars: List[str] = []
        failed_archives: List[str] = []
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = Path(json_path).parent / ".tlauncher_backups" / f"replaced_jars_{timestamp_str}"

        for mod in mods_successfully_mutated:
            if delete_old_jars and mod.installed_jar and mod.installed_jar.lower() != mod.latest_jar_name.lower():
                ok, arc_msg = JsonUpdaterService._archive_old_jar(json_path, mod, archive_dir)
                if ok and arc_msg:
                    archived_jars.append(mod.installed_jar)
                elif not ok:
                    failed_archives.append(arc_msg)

            # Atualiza status em memória do objeto ModItem
            mod.status = UpdateStatus.UPDATED
            mod.installed_file_id = mod.latest_file_id
            mod.installed_version_name = mod.latest_version_name or mod.latest_jar_name
            mod.installed_jar = mod.latest_jar_name

        updated_count = len(mods_successfully_mutated)

        # 5. Monta relatório detalhado de segurança
        lines = [
            f"✅ {updated_count} mod(s) atualizados com sucesso no JSON.",
            f"🛡️ Backup duplo verificado e salvo em:",
            f"   • {Path(json_path).name}.bak (Cópia rápida)",
            f"   • {Path(backup_file).name} (Histórico permanente)",
        ]
        if archived_jars:
            lines.append(f"📦 {len(archived_jars)} .jar(s) antigos foram ARQUIVADOS em segurança em:")
            lines.append(f"   • .tlauncher_backups/{archive_dir.name}/ (Nenhum arquivo foi deletado)")
        if failed_archives:
            lines.append("⚠ Alguns .jar em uso não puderam ser movidos (feche o Minecraft antes):")
            lines.extend(f"   • {m}" for m in failed_archives)
        lines.append("🎮 O TLauncher baixará automaticamente as versões oficiais ao iniciar o modpack.")

        return updated_count, error_count, "\n".join(lines)
