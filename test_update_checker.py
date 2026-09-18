"""
TLauncher Mod Update Checker - Script de Teste
Lê o arquivo TLauncherAdditional.json de um modpack do TLauncher,
extrai as versões locais e consulta a web (CFWidget API / CurseForge / Modrinth)
para comparar as versões instaladas com as versões mais recentes disponíveis.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

JSON_PATH = r"D:\Games\.minecraft\versions\UltimateMinePack\TLauncherAdditional.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def load_tlauncher_mods(json_path: str) -> tuple[str, str, List[Dict[str, Any]]]:
    """
    Carrega o arquivo JSON do TLauncher e extrai os dados do modpack e dos mods.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    modpack = data.get("modpack", {})
    pack_name = modpack.get("name", "Desconhecido")
    version_info = modpack.get("version", {})
    
    # Versão do jogo e loader
    game_version = version_info.get("gameVersionDTO", {}).get("name", "1.20.1")
    loader_types = [t.get("name", "").lower() for t in version_info.get("minecraftVersionTypes", [])]
    loader = loader_types[0] if loader_types else "forge"

    raw_mods = version_info.get("mods", [])
    parsed_mods = []

    for item in raw_mods:
        mod_id = item.get("id")
        name = item.get("name")
        slug = item.get("lanName")
        link = item.get("linkProject", "")
        user_install = item.get("userInstall", False)
        
        ver_obj = item.get("version", {})
        file_id = ver_obj.get("id")
        ver_name = ver_obj.get("name")
        meta = ver_obj.get("metadata", {})
        file_path = meta.get("path", "")
        sha1 = meta.get("sha1", "")

        # Ignorar mods internos de compilação sem link ou com ID negativo gerados pelo Sinytra Connector
        if not mod_id or mod_id < 0 or user_install:
            continue

        parsed_mods.append({
            "id": mod_id,
            "name": name,
            "slug": slug,
            "link": link,
            "installed_file_id": file_id,
            "installed_version_name": ver_name,
            "installed_jar": os.path.basename(file_path),
            "sha1": sha1
        })

    return pack_name, game_version, parsed_mods

def fetch_latest_cfwidget(mod_id: int, game_version: str, loader: str = "forge") -> Optional[Dict[str, Any]]:
    """
    Consulta o CFWidget API para obter os arquivos mais recentes do CurseForge
    filtrados pela versão do Minecraft e loader estrito (ex: Forge).
    """
    url = f"https://api.cfwidget.com/{mod_id}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
            files = data.get("files", [])
            
            strict_matching_files = []
            fallback_matching_files = []

            for f in files:
                versions = [str(v).lower() for v in f.get("versions", [])]
                fname = f.get("name", "").lower()
                
                has_game_ver = (game_version.lower() in versions) or (game_version.lower() in fname)
                is_target_loader = (loader.lower() in versions) or (loader.lower() in fname) or ("neoforge" in versions and loader.lower() == "forge")
                is_rival_loader = ("fabric" in versions or "-fabric" in fname) and loader.lower() == "forge"

                if has_game_ver:
                    if is_target_loader and not is_rival_loader:
                        strict_matching_files.append(f)
                    elif not is_rival_loader:
                        fallback_matching_files.append(f)

            best_files = strict_matching_files or fallback_matching_files
            if best_files:
                latest = best_files[0]
                return {
                    "provider": "CurseForge (via CFWidget)",
                    "latest_file_id": latest.get("id"),
                    "latest_name": latest.get("name"),
                    "upload_date": latest.get("uploaded_at"),
                    "download_url": latest.get("url")
                }
    except Exception:
        return None

    return None

def fetch_latest_modrinth(slug: str, game_version: str, loader: str = "forge") -> Optional[Dict[str, Any]]:
    """
    Fallback usando a API oficial do Modrinth para verificar atualizações.
    """
    if not slug:
        return None
    url = f"https://api.modrinth.com/v2/project/{slug}/version?game_versions=%5B%22{game_version}%22%5D&loaders=%5B%22{loader}%22%5D"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            versions = json.loads(response.read().decode("utf-8"))
            if versions:
                latest = versions[0]
                return {
                    "provider": "Modrinth API",
                    "latest_file_id": latest.get("id"),
                    "latest_name": latest.get("name") or latest.get("version_number"),
                    "upload_date": latest.get("date_published")
                }
    except Exception:
        return None

    return None

def check_mod_update(mod: Dict[str, Any], game_version: str = "1.20.1", loader: str = "forge") -> Dict[str, Any]:
    """
    Compara a versão local do mod com a versão da web.
    """
    mod_id = mod["id"]
    slug = mod["slug"]
    
    # 1. Tenta CFWidget (CurseForge)
    web_data = fetch_latest_cfwidget(mod_id, game_version, loader)
    
    # 2. Se falhar, tenta Modrinth
    if not web_data and slug:
        web_data = fetch_latest_modrinth(slug, game_version, loader)

    status = "UNKNOWN"
    latest_id = None
    latest_name = "N/A"
    provider = "Nenhum"

    if web_data:
        provider = web_data["provider"]
        latest_id = web_data.get("latest_file_id")
        latest_name = web_data.get("latest_name")

        if latest_id and mod["installed_file_id"]:
            if str(latest_id) == str(mod["installed_file_id"]):
                status = "UP_TO_DATE"
            elif latest_id > mod["installed_file_id"]:
                status = "UPDATE_AVAILABLE"
            else:
                status = "UP_TO_DATE"
        else:
            if latest_name.lower() in mod["installed_jar"].lower():
                status = "UP_TO_DATE"
            else:
                status = "UPDATE_AVAILABLE"

    return {
        "name": mod["name"],
        "installed_file_id": mod["installed_file_id"],
        "installed_version": mod["installed_version_name"],
        "installed_jar": mod["installed_jar"],
        "latest_file_id": latest_id,
        "latest_name": latest_name,
        "provider": provider,
        "status": status
    }

def run_test(limit: int = 5):
    print("=" * 80)
    print("      TLAUNCHER MOD UPDATE CHECKER - SCRIPT DE TESTE")
    print("=" * 80)
    
    print(f"\n[1] Lendo arquivo JSON: {JSON_PATH}")
    pack_name, game_ver, mods = load_tlauncher_mods(JSON_PATH)
    
    print(f"    * Modpack: {pack_name}")
    print(f"    * Versão do Minecraft: {game_ver}")
    print(f"    * Total de mods válidos encontrados: {len(mods)}")
    
    print(f"\n[2] Executando teste de comparação na web para os primeiros {limit} mods...\n")
    
    for idx, mod in enumerate(mods[:limit], 1):
        print(f"[{idx}/{limit}] Consultando: {mod['name']} (CF ID: {mod['id']})...")
        res = check_mod_update(mod, game_ver, "forge")
        
        status_symbol = "[OK] Atualizado" if res["status"] == "UP_TO_DATE" else ("[!] ATUALIZAÇÃO DISPONÍVEL" if res["status"] == "UPDATE_AVAILABLE" else "[?] Indisponível")
        print(f"      -> Status: {status_symbol}")
        print(f"      -> Versão Local: {res['installed_version']} (File ID: {res['installed_file_id']})")
        print(f"      -> Versão Web:   {res['latest_name']} (File ID: {res['latest_file_id']}) [{res['provider']}]")
        print("-" * 80)

if __name__ == "__main__":
    count = 5
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass
    run_test(count)
