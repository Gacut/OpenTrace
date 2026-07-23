from __future__ import annotations

import json
from pathlib import Path

from .tool_library import ToolLibrary


class AppSettings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else ToolLibrary.default_path().parent / "settings.json"
        self.animation_disabled = False
        self.language = "pl"
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.animation_disabled = bool(payload.get("animation_disabled", False))
            self.language = payload.get("language", "pl")
            if self.language not in {"pl", "en"}:
                self.language = "pl"
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.animation_disabled = False
            self.language = "pl"

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"animation_disabled": self.animation_disabled, "language": self.language},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)
