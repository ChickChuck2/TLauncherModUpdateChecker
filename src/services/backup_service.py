"""
Serviço para gerenciamento, listagem, exportação e restauração de backups do TLauncher.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from src.core.json_manager import JsonManager
from src.core.models import ModpackInfo


class BackupService:

    @staticmethod
    def get_backup_dir(json_path: str) -> Path:
        """Retorna o diretório .tlauncher_backups do modpack, garantindo sua existência."""
        parent_dir = Path(json_path).parent
        backup_dir = parent_dir / ".tlauncher_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @staticmethod
    def list_backups(json_path: str) -> List[Dict[str, Any]]:
        """
        Lista todos os snapshots de backup disponíveis para o modpack especificado.
        Retorna lista ordenada do mais recente para o mais antigo.
        """
        backups: List[Dict[str, Any]] = []
        if not json_path or not os.path.exists(json_path):
            return backups

        parent_dir = Path(json_path).parent
        backup_dir = parent_dir / ".tlauncher_backups"

        # 1. Backups históricos (.tlauncher_backups/TLauncherAdditional_*.json)
        if backup_dir.exists() and backup_dir.is_dir():
            for entry in backup_dir.glob("TLauncherAdditional_*.json"):
                if entry.is_file():
                    stat = entry.stat()
                    backups.append({
                        "name": entry.name,
                        "path": str(entry),
                        "mtime": stat.st_mtime,
                        "date_str": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
                        "size_kb": round(stat.st_size / 1024, 1),
                        "is_quick_bak": False,
                    })

        # 2. Backup rápido (.bak na raiz do pack)
        quick_bak = parent_dir / "TLauncherAdditional.json.bak"
        if quick_bak.exists() and quick_bak.is_file():
            stat = quick_bak.stat()
            backups.append({
                "name": "TLauncherAdditional.json.bak (Rápido)",
                "path": str(quick_bak),
                "mtime": stat.st_mtime,
                "date_str": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
                "size_kb": round(stat.st_size / 1024, 1),
                "is_quick_bak": True,
            })

        # Ordena do mais recente para o mais antigo
        backups.sort(key=lambda b: b["mtime"], reverse=True)
        return backups

    @staticmethod
    def create_manual_backup(json_path: str) -> str:
        """
        Gera um snapshot manual imediato com timestamp no diretório .tlauncher_backups.
        Garante nome único mesmo em execuções no mesmo segundo.
        Retorna o caminho do arquivo criado.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Arquivo JSON do modpack não encontrado: {json_path}")

        backup_dir = BackupService.get_backup_dir(json_path)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_name = f"TLauncherAdditional_manual_{timestamp_str}.json"
        dest_path = backup_dir / dest_name
        counter = 1
        while dest_path.exists():
            dest_name = f"TLauncherAdditional_manual_{timestamp_str}_{counter}.json"
            dest_path = backup_dir / dest_name
            counter += 1

        shutil.copy2(json_path, str(dest_path))
        if not dest_path.exists() or dest_path.stat().st_size == 0:
            raise RuntimeError("Falha de integridade ao criar backup manual.")

        return str(dest_path)

    @staticmethod
    def export_backups(json_path: str, dest_dir: str, pack_name: str = "Modpack") -> Tuple[int, str]:
        """
        Copia todos os arquivos de backup e o JSON atual para uma pasta externa de escolha do usuário.
        Retorna (total_arquivos_copiados, caminho_da_pasta_criada).
        """
        if not os.path.exists(dest_dir):
            raise FileNotFoundError(f"Diretório de destino não existe: {dest_dir}")

        safe_name = "".join(c for c in pack_name if c.isalnum() or c in (" ", "_", "-")).strip()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_folder = Path(dest_dir) / f"Backup_{safe_name}_{timestamp_str}"
        export_folder.mkdir(parents=True, exist_ok=True)

        copied = 0
        # Copia o JSON atual
        if os.path.exists(json_path):
            shutil.copy2(json_path, export_folder / "TLauncherAdditional_atual.json")
            copied += 1

        # Copia todos os snapshots do diretório de backup
        backup_dir = Path(json_path).parent / ".tlauncher_backups"
        if backup_dir.exists():
            for item in backup_dir.glob("*.json"):
                shutil.copy2(str(item), export_folder / item.name)
                copied += 1

        # Copia também o .bak se existir
        quick_bak = Path(json_path).parent / "TLauncherAdditional.json.bak"
        if quick_bak.exists():
            shutil.copy2(str(quick_bak), export_folder / "TLauncherAdditional.json.bak")
            copied += 1

        return copied, str(export_folder)

    @staticmethod
    def restore_backup(json_path: str, backup_path: str) -> bool:
        """
        Restaura o TLauncherAdditional.json a partir do arquivo de backup selecionado.
        Cria um backup preventivo do estado atual antes da restauração.
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Arquivo de backup para restauração não encontrado: {backup_path}")

        # Cria backup preventivo do estado atual antes de restaurar
        if os.path.exists(json_path):
            try:
                BackupService.create_manual_backup(json_path)
            except Exception:
                pass

        return JsonManager.restore_backup(json_path, backup_path)

    @staticmethod
    def open_backup_folder(json_path: str) -> bool:
        """Abre o diretório .tlauncher_backups no Windows Explorer."""
        backup_dir = BackupService.get_backup_dir(json_path)
        try:
            os.startfile(str(backup_dir))
            return True
        except Exception:
            return False
