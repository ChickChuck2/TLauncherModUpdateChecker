"""
Configurações globais e constantes da aplicação.
"""

import os
from pathlib import Path

# Possíveis caminhos do Minecraft / TLauncher
DEFAULT_MINECRAFT_DIRS = [
    r"D:\Games\.minecraft\versions",
    os.path.expandvars(r"%APPDATA%\.minecraft\versions"),
]

# Nome do arquivo de metadados gerenciado pelo TLauncher
TLAUNCHER_JSON_FILENAME = "TLauncherAdditional.json"

# URLs de APIs e Repositórios
TLAUNCHER_RES_BASE = "http://res.tlauncher.org/unb"
CFWIDGET_API_BASE = "https://api.cfwidget.com"
CURSE_TOOLS_API_BASE = "https://api.curse.tools/v1/cf"
MODRINTH_API_BASE = "https://api.modrinth.com/v2"

# Headers HTTP padrão
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
}

# Timeout de rede padrão (em segundos)
REQUEST_TIMEOUT = 12
