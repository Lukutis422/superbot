import copy
import logging
import os
from typing import Any, Dict

import yaml

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

class ConfigManager:
    def __init__(self, *, path: str, logger: logging.Logger):
        self.path = path
        self.log = logger
        self.data: Dict[str, Any] = {}

    def load_or_create_from_example(self, *, example_path: str) -> None:
        if os.path.exists(self.path):
            self.load()
            return
        if not os.path.exists(example_path):
            raise RuntimeError("Missing config.yml and config.example.yml not found.")
        with open(example_path, "r", encoding="utf-8") as f:
            example = f.read()
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(example)
        self.log.warning("Created %s from %s", self.path, example_path)
        self.load()

    def load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}
        self.data.setdefault("defaults", {})
        self.data.setdefault("guilds", {})
        self.log.info("Loaded config: %s", self.path)

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, sort_keys=False, allow_unicode=True)
        self.log.info("Saved config: %s", self.path)

    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        defaults = self.data.get("defaults", {}) or {}
        override = (self.data.get("guilds", {}) or {}).get(str(guild_id), {}) or {}
        return deep_merge(defaults, override)

    def _ensure_guild_section(self, guild_id: int) -> Dict[str, Any]:
        guilds = self.data.setdefault("guilds", {})
        key = str(guild_id)
        if key not in guilds or not isinstance(guilds[key], dict):
            guilds[key] = {}
        return guilds[key]

    def set_key(self, guild_id: int, dotted_key: str, raw_value: str) -> None:
        allowed_prefixes = ("moderation.", "welcome.", "tickets.", "xp.", "role_menu.")
        if not dotted_key.startswith(allowed_prefixes):
            raise ValueError("Unsupported config key prefix.")

        value: Any = raw_value
        if isinstance(raw_value, str):
            v = raw_value.strip()
            if v.lower() in ("null", "none"):
                value = None
            elif v.lower() in ("true", "false"):
                value = v.lower() == "true"
            else:
                if v.isdigit():
                    value = int(v)

        section = self._ensure_guild_section(guild_id)
        keys = dotted_key.split(".")
        cur = section
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict):
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value
        self.save()

    def dump_guild_yaml(self, guild_id: int) -> str:
        cfg = self.get_guild_config(guild_id)
        return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
