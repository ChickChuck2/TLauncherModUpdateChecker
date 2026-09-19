"""
Serviço para gerenciamento persistente de preferências e configurações do usuário.
Armazena configurações em um arquivo JSON local com leitura e escrita segura.
"""

import os
import json
import tempfile
from typing import Any, Optional, Dict

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "settings.json")


class SettingsService:
    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    def _load(cls) -> Dict[str, Any]:
        if cls._cache is not None:
            return cls._cache

        if not os.path.exists(SETTINGS_FILE):
            cls._cache = {}
            return cls._cache

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cls._cache = data
                else:
                    cls._cache = {}
        except Exception:
            cls._cache = {}
        return cls._cache

    @classmethod
    def _save(cls) -> None:
        if cls._cache is None:
            return

        dir_name = os.path.dirname(SETTINGS_FILE)
        os.makedirs(dir_name, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
                json.dump(cls._cache, tmp, indent=2, ensure_ascii=False)
                temp_name = tmp.name

            if os.path.exists(SETTINGS_FILE):
                os.replace(temp_name, SETTINGS_FILE)
            else:
                os.rename(temp_name, SETTINGS_FILE)
        except Exception:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        data = cls._load()
        return data.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        data = cls._load()
        data[key] = value
        cls._save()

    @classmethod
    def get_last_modpack(cls) -> Optional[str]:
        """Retorna o folder_name do último modpack selecionado pelo usuário."""
        return cls.get("last_selected_modpack")

    @classmethod
    def set_last_modpack(cls, folder_name: str) -> None:
        """Salva o folder_name do último modpack selecionado."""
        if folder_name:
            cls.set("last_selected_modpack", folder_name)
