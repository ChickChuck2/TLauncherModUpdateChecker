"""
Serviço de scanning e verificação de atualizações para Resource Packs e Shader Packs.

Regra crítica de preservação de estado:
    O campo `stateGameElement` ("active" / "no_active") é SEMPRE preservado.
    A atualização altera apenas os metadados de versão, NUNCA o estado ativo.
"""

import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any, Callable

from src.core.config import CFWIDGET_API_BASE, TLAUNCHER_RES_BASE, DEFAULT_HEADERS, REQUEST_TIMEOUT
from src.core.models import AddonType, AddonUpdateStatus
from src.core.addon_models import AddonItem


def _http_get(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


class AddonScannerService:
    """Lê e parseia resource packs e shader packs do TLauncherAdditional.json."""

    @staticmethod
    def parse_addons(json_path: str, addon_type: AddonType) -> List[AddonItem]:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        raw_list = data.get("modpack", {}).get("version", {}).get(addon_type.json_key, [])
        items: List[AddonItem] = []

        for raw in raw_list:
            aid = raw.get("id")
            name = raw.get("name", "Sem Nome")
            slug = raw.get("lanName", "")
            link = raw.get("linkProject", "")
            state = raw.get("stateGameElement", "no_active")
            user_install = raw.get("userInstall", False)
            parser = raw.get("parser", False)
            popularity = raw.get("popularity", 0)
            total_dl = raw.get("downloadALL", 0)
            authors_raw = raw.get("author", "")
            authors = [authors_raw] if isinstance(authors_raw, str) and authors_raw else []
            cats_raw = raw.get("categories", [])
            cats = [c.get("shortName", "") for c in cats_raw if isinstance(c, dict)]

            ver = raw.get("version", {})
            file_id = ver.get("id")
            ver_name = ver.get("name", "")
            meta = ver.get("metadata", {})
            path = meta.get("path", "")
            url = meta.get("url", "")
            sha1 = meta.get("sha1", "")
            size = meta.get("size", 0)

            # Status inicial
            is_local = not parser or (aid is not None and aid < 0) or user_install
            status = AddonUpdateStatus.LOCAL_ONLY if is_local else AddonUpdateStatus.PENDING

            items.append(AddonItem(
                id=aid if aid is not None else -1,
                name=name,
                slug=slug,
                link=link,
                addon_type=addon_type,
                state_game_element=state,
                installed_file_id=file_id,
                installed_version_name=ver_name,
                installed_path=path,
                installed_url=url,
                installed_sha1=sha1,
                installed_size=size,
                user_install=user_install,
                parser=parser,
                popularity=popularity,
                total_downloads=total_dl,
                authors=authors,
                categories=cats,
                status=status,
            ))

        return items


class AddonUpdateService:
    """Verifica atualizações de resource packs e shader packs via API."""

    @staticmethod
    def check_tlauncher_availability(addon: AddonItem) -> bool:
        """Verifica se a nova versão está disponível no repositório do TLauncher."""
        if not addon.latest_file_id or not addon.latest_file_name:
            return False

        encoded_name = urllib.parse.quote(addon.latest_file_name, safe="")
        url = f"{TLAUNCHER_RES_BASE}/{addon.addon_type.folder}/{addon.id}/{addon.latest_file_id}/{encoded_name}"
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                return resp.status == 200
        except Exception:
            try:
                get_req = urllib.request.Request(
                    url, headers={**DEFAULT_HEADERS, "Range": "bytes=0-10"}
                )
                with urllib.request.urlopen(get_req, timeout=6) as resp:
                    return resp.status in (200, 206)
            except Exception:
                return False

    @staticmethod
    def fetch_cfwidget(addon_id: int) -> Optional[Dict[str, Any]]:
        """Busca metadados e lista de arquivos do CFWidget."""
        return _http_get(f"{CFWIDGET_API_BASE}/{addon_id}")

    @staticmethod
    def check_single_addon(addon: AddonItem, game_version: str) -> AddonItem:
        """
        Verifica atualização de um addon. Preserva state_game_element SEMPRE.
        """
        if addon.status == AddonUpdateStatus.LOCAL_ONLY or not addon.is_official:
            return addon

        addon.status = AddonUpdateStatus.CHECKING
        data = AddonUpdateService.fetch_cfwidget(addon.id)

        if not data:
            addon.status = AddonUpdateStatus.NOT_FOUND
            return addon

        # --- Metadados informativos ---
        addon.total_downloads = data.get("downloads", {}).get("total", addon.total_downloads) or addon.total_downloads
        author = data.get("authors", [])
        if author:
            addon.authors = [a if isinstance(a, str) else str(a) for a in author]
        cats = data.get("categories", [])
        if cats:
            addon.categories = [str(c) for c in cats]
        addon.icon_url = data.get("thumbnail") or addon.icon_url
        addon.description = data.get("description", "") or addon.description

        # --- Arquivo mais recente para a versão do jogo ---
        files = data.get("files", [])
        matching = []
        for f in files:
            versions = [str(v).lower() for v in f.get("versions", [])]
            fname = f.get("name", "").lower()
            if game_version.lower() in versions or game_version.lower() in fname:
                matching.append(f)

        if not matching:
            addon.status = AddonUpdateStatus.NOT_FOUND
            return addon

        latest = matching[0]
        latest_file_id = latest.get("id")
        latest_name = latest.get("name")

        # Extrai o nome do arquivo da URL do CFWidget
        latest_url_raw = latest.get("url") or ""
        latest_file_name = latest_name  # fallback

        addon.latest_file_id = latest_file_id
        addon.latest_version_name = latest_name
        addon.latest_file_name = latest_file_name
        addon.latest_update_timestamp = None

        # --- Comparação ---
        has_update = False
        if latest_file_id and addon.installed_file_id:
            has_update = latest_file_id > addon.installed_file_id
        elif latest_name:
            has_update = latest_name.lower() != addon.installed_version_name.lower()

        if not has_update:
            addon.status = AddonUpdateStatus.UP_TO_DATE
            return addon

        # Monta URL no padrão TLauncher e verifica disponibilidade
        encoded_name = urllib.parse.quote(latest_file_name, safe="")
        addon.latest_url = f"{addon.addon_type.url_prefix}/{addon.id}/{latest_file_id}/{encoded_name}"
        addon.tlauncher_available = AddonUpdateService.check_tlauncher_availability(addon)
        addon.status = (
            AddonUpdateStatus.TLAUNCHER_OK if addon.tlauncher_available
            else AddonUpdateStatus.UPDATE_AVAILABLE
        )
        return addon

    @staticmethod
    def check_all_addons(
        addons: List[AddonItem],
        game_version: str,
        progress_callback: Optional[Callable[[int, int, AddonItem], None]] = None,
        max_workers: int = 6,
    ):
        """Verificação em lote usando ThreadPoolExecutor."""
        total = len(addons)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(AddonUpdateService.check_single_addon, addon, game_version): addon
                for addon in addons
            }
            for future in as_completed(futures):
                completed += 1
                try:
                    updated = future.result()
                except Exception:
                    updated = futures[future]
                    updated.status = AddonUpdateStatus.ERROR

                if progress_callback:
                    progress_callback(completed, total, updated)
