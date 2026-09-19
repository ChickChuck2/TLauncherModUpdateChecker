"""
AddonItem: representa um Resource Pack ou Shader Pack do TLauncherAdditional.json.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from src.core.models import AddonType, AddonUpdateStatus


@dataclass
class AddonItem:
    # --- Identificação ---
    id: int
    name: str
    slug: str                      # lanName
    link: str
    addon_type: AddonType

    # --- Estado Ativo no Jogo (CRÍTICO: preservado na atualização) ---
    state_game_element: str        # "active" ou "no_active"

    # --- Versão Instalada ---
    installed_file_id: Optional[int]
    installed_version_name: str
    installed_path: str            # ex: resourcepacks/Better+Lanterns.zip
    installed_url: str             # ex: /resourcepacks/618339/5296814/Better+Lanterns.zip
    installed_sha1: str = ""
    installed_size: int = 0
    user_install: bool = False
    parser: bool = False           # True = controlado pelo TLauncher, False = arquivo local

    # --- Metadados Informativos ---
    summary: str = ""
    description: str = ""
    icon_url: Optional[str] = None
    screenshot_urls: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    total_downloads: int = 0
    popularity: int = 0

    # --- Versão Mais Recente Encontrada ---
    latest_file_id: Optional[int] = None
    latest_version_name: Optional[str] = None
    latest_file_name: Optional[str] = None
    latest_url: Optional[str] = None
    latest_sha1: Optional[str] = None
    latest_size: Optional[int] = None
    latest_update_timestamp: Optional[int] = None
    tlauncher_available: bool = False

    # --- Estado da UI ---
    status: AddonUpdateStatus = AddonUpdateStatus.PENDING
    selected: bool = False

    @property
    def is_active(self) -> bool:
        return self.state_game_element == "active"

    @property
    def is_official(self) -> bool:
        """True se o addon é gerenciado pelo TLauncher (parser=True, id positivo)."""
        return self.parser and self.id > 0

    @property
    def active_label(self) -> str:
        return "🟢 Ativo" if self.is_active else "⚫ Inativo"

    @property
    def active_color(self) -> str:
        return "#1e8449" if self.is_active else "#4a4a4a"

    @property
    def downloads_display(self) -> str:
        n = self.total_downloads
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.0f}K"
        return str(n) if n > 0 else "—"
