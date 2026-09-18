"""
Serviço de consulta de atualizações via APIs e validação no repositório do TLauncher.
Busca também metadados ricos: ícone, categorias, autores, downloads, links, changelog.
"""

import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, Callable, List
from src.core.config import (
    CFWIDGET_API_BASE,
    MODRINTH_API_BASE,
    TLAUNCHER_RES_BASE,
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT
)
from src.core.models import ModItem, ModDependency, UpdateStatus


def _http_get(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[Dict[str, Any]]:
    """Executa uma requisição HTTP GET e retorna o JSON parseado."""
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


class UpdateService:

    @staticmethod
    def check_tlauncher_availability(project_id: int, file_id: int, jar_name: str) -> bool:
        """
        Verifica se o arquivo está disponível no repositório oficial do TLauncher.
        """
        url = f"{TLAUNCHER_RES_BASE}/mods/{project_id}/{file_id}/{jar_name}"
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
    def fetch_cfwidget_full(mod_id: int, game_version: str, loader: str = "forge") -> Optional[Dict[str, Any]]:
        """
        Busca dados completos do mod via CFWidget API (informações gerais + versão recente).
        """
        data = _http_get(f"{CFWIDGET_API_BASE}/{mod_id}")
        if not data:
            return None

        # ---- Metadados gerais do Mod ----
        meta = {
            "description": data.get("description", ""),
            "icon_url": data.get("thumbnail", None),
            "categories": [str(c) for c in data.get("categories", [])],
            "authors": [a if isinstance(a, str) else str(a) for a in data.get("authors", [])],
            "total_downloads": data.get("downloads", {}).get("total", 0) if isinstance(data.get("downloads"), dict) else data.get("download_count", 0),
            "monthly_downloads": data.get("downloads", {}).get("monthly", 0) if isinstance(data.get("downloads"), dict) else 0,
            "last_updated": data.get("last_fetch", None),
            "source_url": None,
            "issues_url": None,
            "mod_license": None,
        }

        # Links opcionais (nem sempre presentes no CFWidget)
        for link in data.get("links", []):
            if isinstance(link, dict):
                rel = link.get("rel", "").lower()
                if "source" in rel or "github" in rel:
                    meta["source_url"] = link.get("href")
                elif "issue" in rel or "bug" in rel:
                    meta["issues_url"] = link.get("href")

        # ---- Arquivo mais recente para a versão alvo ----
        files = data.get("files", [])
        target_files, fallback_files = [], []

        for f in files:
            versions = [str(v).lower() for v in f.get("versions", [])]
            fname = f.get("name", "").lower()

            has_ver = (game_version.lower() in versions) or (game_version.lower() in fname)
            is_loader = (loader.lower() in versions) or (loader.lower() in fname) or (
                "neoforge" in versions and loader.lower() == "forge"
            )
            is_fabric_only = ("fabric" in versions or "-fabric" in fname) and loader.lower() == "forge"

            if has_ver:
                if is_loader and not is_fabric_only:
                    target_files.append(f)
                elif not is_fabric_only:
                    fallback_files.append(f)

        selected = target_files or fallback_files
        if not selected:
            return {**meta, "provider": "CurseForge", "file": None}

        latest = selected[0]
        file_data = {
            "provider": "CurseForge",
            "file_id": latest.get("id"),
            "name": latest.get("name"),
            "jar_name": latest.get("name"),
            "upload_date": latest.get("uploaded_at"),
            "release_type": latest.get("type", "release").lower(),
            "sha1": None,
            "size": None,
            "changelog": None,
            "dependencies": [],
        }
        return {**meta, **file_data}

    @staticmethod
    def fetch_modrinth_full(slug: str, game_version: str, loader: str = "forge") -> Optional[Dict[str, Any]]:
        """
        Busca dados completos via Modrinth API (fallback).
        """
        if not slug:
            return None

        # Informações gerais do projeto
        proj_data = _http_get(f"{MODRINTH_API_BASE}/project/{slug}")
        if not proj_data:
            return None

        meta = {
            "description": proj_data.get("description", ""),
            "icon_url": proj_data.get("icon_url", None),
            "categories": proj_data.get("categories", []),
            "authors": [],
            "total_downloads": proj_data.get("downloads", 0),
            "monthly_downloads": 0,
            "source_url": proj_data.get("source_url", None),
            "issues_url": proj_data.get("issues_url", None),
            "mod_license": proj_data.get("license", {}).get("id") if isinstance(proj_data.get("license"), dict) else None,
            "last_updated": proj_data.get("updated", None),
        }

        # Versões
        encoded_ver = urllib.parse.quote(f'["{game_version}"]') if hasattr(urllib, 'parse') else f'%5B%22{game_version}%22%5D'
        encoded_loader = urllib.parse.quote(f'["{loader}"]') if hasattr(urllib, 'parse') else f'%5B%22{loader}%22%5D'

        import urllib.parse
        ver_url = f"{MODRINTH_API_BASE}/project/{slug}/version?game_versions={urllib.parse.quote(json.dumps([game_version]))}&loaders={urllib.parse.quote(json.dumps([loader]))}"
        ver_list = _http_get(ver_url)

        if not ver_list:
            return {**meta, "provider": "Modrinth", "file": None}

        latest = ver_list[0]
        files = latest.get("files", [])
        primary = next((f for f in files if f.get("primary")), files[0] if files else {})

        deps = []
        for d in latest.get("dependencies", []):
            deps.append(ModDependency(
                slug=d.get("project_id"),
                relation_type=d.get("dependency_type", "required")
            ))

        file_data = {
            "provider": "Modrinth",
            "file_id": None,
            "name": latest.get("name") or latest.get("version_number"),
            "jar_name": primary.get("filename"),
            "upload_date": latest.get("date_published"),
            "release_type": latest.get("version_type", "release").lower(),
            "sha1": primary.get("hashes", {}).get("sha1"),
            "size": primary.get("size"),
            "changelog": latest.get("changelog", None),
            "dependencies": deps,
        }
        return {**meta, **file_data}

    @staticmethod
    def check_single_mod(mod: ModItem, game_version: str, loader: str = "forge") -> ModItem:
        """
        Verifica a atualização e metadados completos de um mod específico.
        """
        if mod.status == UpdateStatus.LOCAL_ONLY or mod.id <= 0:
            return mod

        mod.status = UpdateStatus.CHECKING

        # 1. Tenta CurseForge via CFWidget
        data = UpdateService.fetch_cfwidget_full(mod.id, game_version, loader)

        # 2. Fallback Modrinth
        if not data and mod.slug:
            data = UpdateService.fetch_modrinth_full(mod.slug, game_version, loader)

        if not data:
            mod.status = UpdateStatus.NOT_FOUND
            return mod

        # ---- Preenche metadados do mod ----
        mod.provider = data.get("provider", "")
        mod.description = data.get("description", "") or mod.description
        mod.icon_url = data.get("icon_url") or mod.icon_url
        mod.categories = data.get("categories") or mod.categories
        mod.authors = data.get("authors") or mod.authors
        mod.total_downloads = data.get("total_downloads", 0) or mod.total_downloads
        mod.monthly_downloads = data.get("monthly_downloads", 0) or mod.monthly_downloads
        mod.source_url = data.get("source_url") or mod.source_url
        mod.issues_url = data.get("issues_url") or mod.issues_url
        mod.mod_license = data.get("mod_license") or mod.mod_license
        mod.last_updated = data.get("last_updated") or mod.last_updated

        # ---- Preenche dados da nova versão ----
        mod.latest_file_id = data.get("file_id")
        mod.latest_version_name = data.get("name")
        mod.latest_jar_name = data.get("jar_name")
        mod.latest_sha1 = data.get("sha1")
        mod.latest_size = data.get("size")
        mod.latest_release_type = data.get("release_type", "release")
        mod.latest_changelog = data.get("changelog")
        mod.latest_dependencies = data.get("dependencies", [])

        if not mod.latest_file_id and not mod.latest_jar_name:
            mod.status = UpdateStatus.NOT_FOUND
            return mod

        # ---- Comparação de versão ----
        has_update = False
        if mod.latest_file_id and mod.installed_file_id:
            has_update = mod.latest_file_id > mod.installed_file_id
        elif mod.latest_jar_name:
            has_update = mod.latest_jar_name.lower() != mod.installed_jar.lower()

        if has_update:
            if mod.latest_file_id and mod.latest_jar_name:
                mod.tlauncher_url = f"/mods/{mod.id}/{mod.latest_file_id}/{mod.latest_jar_name}"
                mod.tlauncher_available = UpdateService.check_tlauncher_availability(
                    project_id=mod.id,
                    file_id=mod.latest_file_id,
                    jar_name=mod.latest_jar_name
                )
                mod.status = UpdateStatus.TLAUNCHER_CONFIRMED if mod.tlauncher_available else UpdateStatus.UPDATE_AVAILABLE
            else:
                mod.status = UpdateStatus.UPDATE_AVAILABLE
        else:
            mod.status = UpdateStatus.UP_TO_DATE

        return mod

    @staticmethod
    def check_all_mods(
        mods: List[ModItem],
        game_version: str,
        loader: str,
        progress_callback: Optional[Callable[[int, int, ModItem], None]] = None,
        max_workers: int = 8
    ):
        """Executa a verificação em lote com pool de threads."""
        total = len(mods)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_mod = {
                executor.submit(UpdateService.check_single_mod, mod, game_version, loader): mod
                for mod in mods
            }
            for future in as_completed(future_to_mod):
                completed += 1
                try:
                    updated_mod = future.result()
                except Exception:
                    updated_mod = future_to_mod[future]
                    updated_mod.status = UpdateStatus.ERROR

                if progress_callback:
                    progress_callback(completed, total, updated_mod)
