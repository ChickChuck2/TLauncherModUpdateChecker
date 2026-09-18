"""
Serviço de Empacotamento Rápido (Sync Zip) e Exportação via Drag-and-Drop / Clipboard.
Gera em milissegundos um pacote .zip com todos os arquivos essenciais do Modpack:
- TLauncherAdditional.json (e backup)
- Pasta config/ completa
- options.txt (ordem de resource packs e controles)
- optionsof.txt / optionsshaders.txt (se existirem)
- defaultconfigs/ e kubejs/ (se existirem)
"""

import os
import time
import zipfile
import tempfile
import struct
from typing import Optional, Tuple

try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import clr
    clr.AddReference("System.Windows.Forms")
    from System.Windows.Forms import Label, DataObject, DragDropEffects
    from System.Collections.Specialized import StringCollection
    HAS_WINFORMS_DND = True
except Exception:
    HAS_WINFORMS_DND = False


class PackExportService:

    _cache: dict = {}

    @classmethod
    def get_output_zip_path(cls, pack_dir: str) -> str:
        pack_name = os.path.basename(os.path.abspath(pack_dir))
        temp_dir = os.path.join(tempfile.gettempdir(), "TLauncherSyncPacks")
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, f"{pack_name}_Sync.zip")

    @classmethod
    def build_sync_zip(cls, pack_dir: str, force_rebuild: bool = False) -> Tuple[str, int, float, float]:
        """
        Compacta todos os arquivos essenciais do modpack em um arquivo .zip.
        Retorna (zip_path, total_arquivos, tamanho_kb, tempo_ms).
        """
        start_time = time.perf_counter()
        vpath = os.path.abspath(pack_dir)
        zip_path = cls.get_output_zip_path(vpath)

        # Se já estiver em cache e não for forçado, e o zip existir com menos de 10s
        if not force_rebuild and vpath in cls._cache:
            cache_info = cls._cache[vpath]
            if os.path.exists(cache_info["path"]) and (time.time() - cache_info["time"] < 15):
                return (
                    cache_info["path"],
                    cache_info["files"],
                    cache_info["size_kb"],
                    0.0
                )

        files_to_pack = []

        # Arquivos individuais essenciais
        single_files = [
            "TLauncherAdditional.json",
            "TLauncherAdditional.json.bak",
            "options.txt",
            "optionsof.txt",
            "optionsshaders.txt"
        ]
        for fn in single_files:
            fp = os.path.join(vpath, fn)
            if os.path.exists(fp):
                files_to_pack.append((fp, fn))

        # Pastas essenciais de configuração
        folder_targets = ["config", "defaultconfigs", "kubejs"]
        for dn in folder_targets:
            dp = os.path.join(vpath, dn)
            if os.path.exists(dp) and os.path.isdir(dp):
                for root, _, files in os.walk(dp):
                    for f in files:
                        if f.endswith(".log") or f.endswith(".tmp") or f.endswith(".bak"):
                            continue
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, vpath)
                        files_to_pack.append((full, rel))

        # Compacta em nível 1 para velocidade máxima (milissegundos)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            for full, rel in files_to_pack:
                try:
                    zf.write(full, rel)
                except Exception:
                    pass

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        size_kb = os.path.getsize(zip_path) / 1024 if os.path.exists(zip_path) else 0.0

        cls._cache[vpath] = {
            "path": zip_path,
            "files": len(files_to_pack),
            "size_kb": size_kb,
            "time": time.time()
        }

        return zip_path, len(files_to_pack), size_kb, elapsed_ms

    @staticmethod
    def copy_file_to_clipboard(file_path: str) -> bool:
        """
        Copia o arquivo .zip para a Área de Transferência do Windows como CF_HDROP,
        permitindo dar Ctrl+V diretamente em pastas, Discord, WhatsApp ou Telegram.
        """
        if not HAS_WIN32 or not os.path.exists(file_path):
            return False

        try:
            abs_path = os.path.abspath(file_path)
            # Estrutura DROPFILES
            offset = 20
            dropfiles = struct.pack("IIIIi", offset, 0, 0, 0, 1)
            files_str = abs_path + "\0\0"
            data = dropfiles + files_str.encode("utf-16le")

            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return False

    @staticmethod
    def start_native_drag(file_path: str) -> bool:
        """
        Inicia a operação nativa de Drag-and-Drop do Windows (OLE DoDragDrop).
        Permite que o usuário arraste o cursor da nossa janela e solte em qualquer
        pasta do Windows Explorer, Área de Trabalho ou Discord.
        """
        if not HAS_WINFORMS_DND or not os.path.exists(file_path):
            return False

        try:
            abs_path = os.path.abspath(file_path)
            lbl = Label()
            files = StringCollection()
            files.Add(abs_path)

            data = DataObject()
            data.SetFileDropList(files)

            lbl.DoDragDrop(data, DragDropEffects.Copy | DragDropEffects.Move)
            return True
        except Exception:
            return False
