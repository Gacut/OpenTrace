from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from uuid import UUID

from app.models import AnalysisRecord, BoardItemModel, ConnectionModel, ItemType
from app.storage.database import SCHEMA_VERSION


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def structural_export(
    destination: Path,
    case_metadata: dict,
    items: list[BoardItemModel],
    connections: list[ConnectionModel],
    records: list[AnalysisRecord],
) -> None:
    safe_metadata = {key: value for key, value in case_metadata.items() if "path" not in key.lower()}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "case": safe_metadata,
        "items": [item.to_dict() for item in items],
        "connections": [connection.to_dict() for connection in connections],
        "analysis_records": [record.to_dict() for record in records],
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_project(
    case_root: Path,
    items: list[BoardItemModel],
    connections: list[ConnectionModel],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    item_ids = {item.id for item in items}
    hashes: dict[str, str] = {}
    for item in items:
        try:
            UUID(item.id)
        except ValueError:
            issues.append({"level": "błąd", "item_id": item.id, "message": "Nieprawidłowy UUID elementu."})
        if abs(item.x) > 40000 or abs(item.y) > 40000:
            issues.append({"level": "ostrzeżenie", "item_id": item.id,
                           "message": "Element znajduje się ekstremalnie daleko od środka tablicy."})
        if item.type == ItemType.IMAGE:
            relative = item.payload.get("path", "")
            path = case_root / relative
            if not path.is_file():
                issues.append({"level": "błąd", "item_id": item.id, "message": f"Brak pliku: {relative}"})
                continue
            expected = item.payload.get("sha256")
            if expected:
                current = sha256_file(path)
                if current != expected:
                    issues.append({"level": "błąd", "item_id": item.id,
                                   "message": "Plik różni się od wersji dodanej pierwotnie do sprawy."})
                if current in hashes:
                    issues.append({"level": "informacja", "item_id": item.id,
                                   "message": f"Identyczny SHA-256 jak element {hashes[current]}."})
                hashes[current] = item.id
    for connection in connections:
        if connection.source_id not in item_ids or connection.target_id not in item_ids:
            issues.append({"level": "błąd", "item_id": connection.id,
                           "message": "Połączenie wskazuje na nieistniejący element."})
        if connection.branch_from_id and connection.branch_from_id not in {
            edge.id for edge in connections
        }:
            issues.append({"level": "błąd", "item_id": connection.id,
                           "message": "Gałąź wskazuje na nieistniejącą linię nadrzędną."})
    return issues


def case_statistics(
    items: list[BoardItemModel],
    connections: list[ConnectionModel],
    records: list[AnalysisRecord],
) -> dict:
    degree = Counter()
    for edge in connections:
        degree[edge.source_id] += 1
        degree[edge.target_id] += 1
    tags = Counter(tag for item in items for tag in item.tags)
    return {
        "elements": len(items),
        "connections": len(connections),
        "sources": sum(record.kind == "source" for record in records),
        "hypotheses": sum(record.kind == "hypothesis" for record in records),
        "unverified": sum(item.status in {"Nowe", "Do sprawdzenia", "Niepotwierdzone"} for item in items),
        "open_tasks": sum(record.kind == "task" and record.status != "Ukończone" for record in records),
        "top_tags": tags.most_common(5),
        "top_connected": degree.most_common(5),
    }
