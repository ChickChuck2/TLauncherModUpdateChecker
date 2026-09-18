"""
Serviço de carregamento e cache de imagens para thumbnails e capturas de tela.

Arquitetura de Cache em 3 Camadas:
  1. Cache em Memória: CTkImage pronto para exibição instantânea.
  2. Cache em Disco Local:
     - Reaproveita cache nativo do TLauncher (%APPDATA%/.tlauncher/cache) se disponível.
     - Armazena imagens baixadas da web (CurseForge, Modrinth, TLauncher CDN) em disco local.
  3. Download Assíncrono com ThreadPool:
     - Nunca trava a interface gráfica.
     - Retorna no thread principal via `root.after()`.
"""

import hashlib
import io
import os
import tempfile
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional, Tuple

import customtkinter as ctk
from PIL import Image

# Headers para evitar bloqueio em CDNs
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

# Cache em disco próprio da aplicação
_APP_DISK_CACHE_DIR = os.path.join(tempfile.gettempdir(), "tl_mod_updater_img_cache")
os.makedirs(_APP_DISK_CACHE_DIR, exist_ok=True)

# Diretório base de cache do TLauncher
_TL_CACHE_DIR = os.path.expandvars(r"%APPDATA%\.tlauncher\cache")

# Cache em memória: key -> CTkImage
_memory_cache: Dict[str, Optional[ctk.CTkImage]] = {}
_cache_lock = threading.Lock()

# ThreadPool para downloads concorrentes
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ImgLoader")


def _get_disk_cache_path(url: str) -> str:
    """Gera o caminho seguro de cache em disco para uma URL arbitrária."""
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    # Tenta manter a extensão original
    ext = ".png"
    if ".jpg" in url.lower() or ".jpeg" in url.lower():
        ext = ".jpg"
    elif ".webp" in url.lower():
        ext = ".webp"
    return os.path.join(_APP_DISK_CACHE_DIR, f"{url_hash}{ext}")


def _find_in_tlauncher_cache(url: str) -> Optional[str]:
    """
    Verifica se a imagem já foi baixada anteriormente pelo TLauncher oficial
    em %APPDATA%/.tlauncher/cache.
    """
    if not os.path.exists(_TL_CACHE_DIR):
        return None

    try:
        parsed = urllib.parse.urlparse(url)
        rel_path = parsed.path.lstrip("/").replace("/", os.sep)
        netloc = parsed.netloc

        candidates = [
            os.path.join(_TL_CACHE_DIR, f"https_{netloc}", rel_path),
            os.path.join(_TL_CACHE_DIR, f"http_{netloc}", rel_path),
            os.path.join(_TL_CACHE_DIR, "https_rescl.tlauncher.org", rel_path),
            os.path.join(_TL_CACHE_DIR, "http_res.tlauncher.org", rel_path),
        ]

        # Se for pictures/compress, também verifica se existe na pasta max
        if "pictures" in rel_path:
            alt_path = rel_path.replace("pictures" + os.sep + "compress", "pictures" + os.sep + "max")
            candidates.append(os.path.join(_TL_CACHE_DIR, "http_res.tlauncher.org", alt_path))
            candidates.append(os.path.join(_TL_CACHE_DIR, "https_rescl.tlauncher.org", alt_path))

        for cand in candidates:
            if os.path.exists(cand) and os.path.getsize(cand) > 0:
                return cand
    except Exception:
        pass

    return None


def _load_raw_image_data(url: str) -> Optional[bytes]:
    """
    Carrega os bytes da imagem:
      1. Tenta cache nativo do TLauncher.
      2. Tenta cache em disco do aplicativo.
      3. Baixa da rede e salva no cache em disco do aplicativo.
    """
    # 1. TLauncher Cache
    tl_cached = _find_in_tlauncher_cache(url)
    if tl_cached:
        try:
            with open(tl_cached, "rb") as f:
                return f.read()
        except Exception:
            pass

    # 2. App Disk Cache
    disk_path = _get_disk_cache_path(url)
    if os.path.exists(disk_path) and os.path.getsize(disk_path) > 0:
        try:
            with open(disk_path, "rb") as f:
                return f.read()
        except Exception:
            pass

    # 3. Download via rede
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = resp.read()

        if data:
            try:
                with open(disk_path, "wb") as f:
                    f.write(data)
            except Exception:
                pass
            return data
    except Exception:
        pass

    return None


def _build_ctk_image(raw_bytes: bytes, target_size: Tuple[int, int]) -> Optional[ctk.CTkImage]:
    """Processa os bytes da imagem PIL e gera um CTkImage proporcional."""
    try:
        pil_img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        # Mantém proporção e escala com alta qualidade
        pil_img.thumbnail(target_size, Image.Resampling.LANCZOS)
        actual_size = (pil_img.width, pil_img.height)
        return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=actual_size)
    except Exception:
        return None


class ImageService:
    @staticmethod
    def get_sync(url: Optional[str], size: Tuple[int, int]) -> Optional[ctk.CTkImage]:
        """
        Retorna a imagem imediatamente se já estiver em cache na memória.
        Caso contrário, retorna None.
        """
        if not url:
            return None
        cache_key = f"{url}@{size[0]}x{size[1]}"
        with _cache_lock:
            return _memory_cache.get(cache_key)

    @staticmethod
    def get_async(
        url: Optional[str],
        size: Tuple[int, int],
        callback: Callable[[Optional[ctk.CTkImage]], None],
        root: any,
    ):
        """
        Busca e carrega uma imagem assincronamente.
        Chama `callback(ctk_image_or_none)` na thread principal do Tkinter via `root.after()`.
        """
        if not url:
            callback(None)
            return

        cache_key = f"{url}@{size[0]}x{size[1]}"

        # Se já estiver em memória, executa callback imediatamente
        with _cache_lock:
            if cache_key in _memory_cache:
                callback(_memory_cache[cache_key])
                return

        def _worker():
            raw = _load_raw_image_data(url)
            img = _build_ctk_image(raw, size) if raw else None

            with _cache_lock:
                _memory_cache[cache_key] = img

            # Envia de volta para a UI
            def _ui_dispatch():
                try:
                    if hasattr(root, "winfo_exists") and not root.winfo_exists():
                        return
                    callback(img)
                except Exception:
                    pass

            try:
                root.after(0, _ui_dispatch)
            except Exception:
                pass

        _executor.submit(_worker)

    @staticmethod
    def clear_cache():
        """Limpa o cache em memória."""
        with _cache_lock:
            _memory_cache.clear()
