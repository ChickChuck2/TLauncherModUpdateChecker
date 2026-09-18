"""
Modelos de dados (Dataclasses) da aplicação.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class AddonType(Enum):
    RESOURCE_PACK = "resourcepack"
    SHADER_PACK   = "shaderpack"

    @property
    def json_key(self) -> str:
        return "resourcePacks" if self == AddonType.RESOURCE_PACK else "shaderpacks"

    @property
    def url_prefix(self) -> str:
        return "/resourcepacks" if self == AddonType.RESOURCE_PACK else "/shaderpacks"

    @property
    def folder(self) -> str:
        return "resourcepacks" if self == AddonType.RESOURCE_PACK else "shaderpacks"

    @property
    def label(self) -> str:
        return "Resource Pack" if self == AddonType.RESOURCE_PACK else "Shader Pack"


class AddonUpdateStatus(Enum):
    PENDING           = "PENDING"
    CHECKING          = "CHECKING"
    UP_TO_DATE        = "UP_TO_DATE"
    UPDATE_AVAILABLE  = "UPDATE_AVAILABLE"
    TLAUNCHER_OK      = "TLAUNCHER_OK"
    UPDATED           = "UPDATED"
    NOT_FOUND         = "NOT_FOUND"
    LOCAL_ONLY        = "LOCAL_ONLY"
    ERROR             = "ERROR"

    @property
    def label(self) -> str:
        return {
            AddonUpdateStatus.PENDING:          "Pendente",
            AddonUpdateStatus.CHECKING:         "Verificando...",
            AddonUpdateStatus.UP_TO_DATE:       "Em Dia ✓",
            AddonUpdateStatus.UPDATE_AVAILABLE: "Disponível",
            AddonUpdateStatus.TLAUNCHER_OK:     "✓ No TLauncher",
            AddonUpdateStatus.UPDATED:          "Aplicado!",
            AddonUpdateStatus.NOT_FOUND:        "Não encontrado",
            AddonUpdateStatus.LOCAL_ONLY:       "Local",
            AddonUpdateStatus.ERROR:            "Erro",
        }.get(self, self.value)

    @property
    def color(self) -> str:
        return {
            AddonUpdateStatus.PENDING:          "#4a4a4a",
            AddonUpdateStatus.CHECKING:         "#2980b9",
            AddonUpdateStatus.UP_TO_DATE:       "#1e8449",
            AddonUpdateStatus.UPDATE_AVAILABLE: "#d68910",
            AddonUpdateStatus.TLAUNCHER_OK:     "#117a65",
            AddonUpdateStatus.UPDATED:          "#0e6655",
            AddonUpdateStatus.NOT_FOUND:        "#566573",
            AddonUpdateStatus.LOCAL_ONLY:       "#4a4a4a",
            AddonUpdateStatus.ERROR:            "#922b21",
        }.get(self, "#4a4a4a")

class UpdateStatus(Enum):
    PENDING = "PENDING"
    CHECKING = "CHECKING"
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    TLAUNCHER_CONFIRMED = "TLAUNCHER_CONFIRMED"
    UPDATED = "UPDATED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"
    LOCAL_ONLY = "LOCAL_ONLY"

    @property
    def label(self) -> str:
        labels = {
            UpdateStatus.PENDING: "Pendente",
            UpdateStatus.CHECKING: "Verificando...",
            UpdateStatus.UP_TO_DATE: "Atualizado ✓",
            UpdateStatus.UPDATE_AVAILABLE: "Disponível",
            UpdateStatus.TLAUNCHER_CONFIRMED: "✓ No TLauncher",
            UpdateStatus.UPDATED: "Aplicado!",
            UpdateStatus.NOT_FOUND: "Não Encontrado",
            UpdateStatus.ERROR: "Erro",
            UpdateStatus.LOCAL_ONLY: "Interno",
        }
        return labels.get(self, self.value)

    @property
    def color(self) -> str:
        colors = {
            UpdateStatus.PENDING: "#4a4a4a",
            UpdateStatus.CHECKING: "#2980b9",
            UpdateStatus.UP_TO_DATE: "#1e8449",
            UpdateStatus.UPDATE_AVAILABLE: "#d68910",
            UpdateStatus.TLAUNCHER_CONFIRMED: "#117a65",
            UpdateStatus.UPDATED: "#0e6655",
            UpdateStatus.NOT_FOUND: "#566573",
            UpdateStatus.ERROR: "#922b21",
            UpdateStatus.LOCAL_ONLY: "#4a4a4a",
        }
        return colors.get(self, "#4a4a4a")

    @property
    def text_color(self) -> str:
        return "#ffffff"

@dataclass
class ModDependency:
    mod_id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None
    relation_type: str = "required"  # required, optional, incompatible

@dataclass
class ModItem:
    # --- Identificação ---
    id: int
    name: str
    slug: str
    link: str

    # --- Versão Instalada ---
    installed_file_id: Optional[int]
    installed_version_name: str
    installed_jar: str
    installed_sha1: str = ""
    installed_size: int = 0
    user_install: bool = False

    # --- Metadados do Mod (Informativos) ---
    description: str = ""
    icon_url: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    total_downloads: int = 0
    monthly_downloads: int = 0
    source_url: Optional[str] = None       # GitHub / GitLab
    issues_url: Optional[str] = None       # Issue Tracker
    mod_license: Optional[str] = None      # MIT, LGPL, etc.
    last_updated: Optional[str] = None     # Data de atualização do mod

    # --- Versão Mais Recente Encontrada ---
    latest_file_id: Optional[int] = None
    latest_version_name: Optional[str] = None
    latest_jar_name: Optional[str] = None
    latest_sha1: Optional[str] = None
    latest_size: Optional[int] = None
    latest_update_timestamp: Optional[int] = None
    latest_release_type: str = "release"   # release, beta, alpha
    latest_changelog: Optional[str] = None
    latest_dependencies: List[ModDependency] = field(default_factory=list)
    tlauncher_url: Optional[str] = None
    tlauncher_available: bool = False

    # --- Estado da UI ---
    status: UpdateStatus = UpdateStatus.PENDING
    selected: bool = False
    provider: str = ""

    @property
    def downloads_display(self) -> str:
        """Formata o número de downloads de forma legível."""
        n = self.total_downloads
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.0f}K"
        return str(n)

    @property
    def is_official(self) -> bool:
        return self.id > 0 and not self.user_install

@dataclass
class ModpackInfo:
    name: str
    folder_name: str
    json_path: str
    game_version: str
    loader: str
    mods: List[ModItem] = field(default_factory=list)

    @property
    def total_mods(self) -> int:
        return len(self.mods)

    @property
    def official_mods(self) -> List[ModItem]:
        return [m for m in self.mods if m.is_official]

    @property
    def update_available_count(self) -> int:
        return sum(
            1 for m in self.mods
            if m.status in (UpdateStatus.UPDATE_AVAILABLE, UpdateStatus.TLAUNCHER_CONFIRMED)
        )
