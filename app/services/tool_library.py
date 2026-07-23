from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QStandardPaths


@dataclass(slots=True)
class ToolCategory:
    name: str
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class OsintTool:
    name: str
    url: str
    description: str = ""
    category_id: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))


class ToolLibrary:
    """Globalna biblioteka użytkownika, niezależna od otwartej sprawy."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else self.default_path()
        self.categories: list[ToolCategory] = []
        self.tools: list[OsintTool] = []
        self.load()

    @staticmethod
    def default_path() -> Path:
        override = os.environ.get("OSINT_BOARD_CONFIG_DIR")
        root = Path(override) if override else Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        )
        return root / "osint_tools.json"

    def load(self) -> None:
        if not self.path.exists():
            self.categories = [ToolCategory("Bez kategorii")]
            self.tools = []
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.categories = [ToolCategory(**value) for value in raw.get("categories", [])]
            self.tools = [OsintTool(**value) for value in raw.get("tools", [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            backup = self.path.with_suffix(".broken.json")
            try:
                self.path.replace(backup)
            except OSError:
                pass
            self.categories = [ToolCategory("Bez kategorii")]
            self.tools = []
        if not self.categories:
            self.categories.append(ToolCategory("Bez kategorii"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "categories": [asdict(category) for category in self.categories],
            "tools": [asdict(tool) for tool in self.tools],
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def add_category(self, name: str) -> ToolCategory:
        clean = name.strip()
        if not clean:
            raise ValueError("Nazwa kategorii nie może być pusta.")
        if any(category.name.casefold() == clean.casefold() for category in self.categories):
            raise ValueError("Kategoria o tej nazwie już istnieje.")
        category = ToolCategory(clean)
        self.categories.append(category)
        self.save()
        return category

    def rename_category(self, category_id: str, name: str) -> None:
        clean = name.strip()
        if not clean:
            raise ValueError("Nazwa kategorii nie może być pusta.")
        if any(c.id != category_id and c.name.casefold() == clean.casefold() for c in self.categories):
            raise ValueError("Kategoria o tej nazwie już istnieje.")
        category = self.category(category_id)
        category.name = clean
        self.save()

    def delete_category(self, category_id: str) -> None:
        if len(self.categories) == 1:
            raise ValueError("Musi pozostać co najmniej jedna kategoria.")
        fallback = next(category for category in self.categories if category.id != category_id)
        self.categories = [category for category in self.categories if category.id != category_id]
        for tool in self.tools:
            if tool.category_id == category_id:
                tool.category_id = fallback.id
        self.save()

    def category(self, category_id: str) -> ToolCategory:
        category = next((value for value in self.categories if value.id == category_id), None)
        if not category:
            raise KeyError(category_id)
        return category

    def add_tool(self, name: str, url: str, description: str, category_id: str) -> OsintTool:
        tool = OsintTool(name.strip(), url.strip(), description.strip(), category_id)
        self._validate_tool(tool)
        self.tools.append(tool)
        self.save()
        return tool

    def update_tool(self, tool: OsintTool) -> None:
        self._validate_tool(tool)
        index = next((i for i, value in enumerate(self.tools) if value.id == tool.id), None)
        if index is None:
            raise KeyError(tool.id)
        self.tools[index] = tool
        self.save()

    def delete_tool(self, tool_id: str) -> None:
        self.tools = [tool for tool in self.tools if tool.id != tool_id]
        self.save()

    def _validate_tool(self, tool: OsintTool) -> None:
        if not tool.name:
            raise ValueError("Nazwa narzędzia nie może być pusta.")
        if not tool.url:
            raise ValueError("Link nie może być pusty.")
        self.category(tool.category_id)
