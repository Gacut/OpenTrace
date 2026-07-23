from __future__ import annotations

import json

from app.models import AnalysisRecord, BoardItemModel, CaseMetadata, ConnectionModel
from app.models.entities import now_iso
from app.storage.database import Database


class CaseRepository:
    def __init__(self, database: Database):
        self.db = database

    def save_metadata(self, metadata: CaseMetadata) -> None:
        metadata.modified_at = now_iso()
        with self.db.connection:
            for key, value in metadata.to_dict().items():
                raw = json.dumps(value, ensure_ascii=False)
                self.db.connection.execute(
                    "INSERT INTO meta(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, raw)
                )

    def load_metadata(self) -> CaseMetadata:
        rows = self.db.connection.execute("SELECT key,value FROM meta").fetchall()
        values = {row["key"]: json.loads(row["value"]) for row in rows}
        if not values:
            raise ValueError("Brak metadanych sprawy.")
        allowed = CaseMetadata.__dataclass_fields__.keys()
        return CaseMetadata(**{key: value for key, value in values.items() if key in allowed})

    def save_all(self, items: list[BoardItemModel], connections: list[ConnectionModel]) -> None:
        with self.db.connection:
            self.db.connection.execute("DELETE FROM connections")
            self.db.connection.execute("DELETE FROM items")
            self.db.connection.executemany(
                """INSERT INTO items
                (id,type,x,y,width,height,rotation,z,created_at,modified_at,status,tags_json,locked,payload_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(
                    i.id, i.type.value, i.x, i.y, i.width, i.height, i.rotation, i.z,
                    i.created_at, i.modified_at, i.status,
                    json.dumps(i.tags, ensure_ascii=False), int(i.locked),
                    json.dumps(i.payload, ensure_ascii=False),
                ) for i in items],
            )
            self.db.connection.executemany(
                """INSERT INTO connections
                (id,source_id,target_id,color,width,style,label,direction,created_at,
                 relation_type,confidence,branch_from_id)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(
                    c.id, c.source_id, c.target_id, c.color, c.width, c.style,
                    c.label, c.direction, c.created_at, c.relation_type, c.confidence,
                    c.branch_from_id,
                ) for c in connections],
            )

    def load_items(self) -> list[BoardItemModel]:
        result = []
        for row in self.db.connection.execute("SELECT * FROM items ORDER BY z"):
            result.append(BoardItemModel.from_dict({
                "id": row["id"], "type": row["type"], "x": row["x"], "y": row["y"],
                "width": row["width"], "height": row["height"],
                "rotation": row["rotation"], "z": row["z"],
                "created_at": row["created_at"], "modified_at": row["modified_at"],
                "status": row["status"], "tags": json.loads(row["tags_json"]),
                "locked": bool(row["locked"]), "payload": json.loads(row["payload_json"]),
            }))
        return result

    def load_connections(self) -> list[ConnectionModel]:
        return [ConnectionModel(**dict(row)) for row in
                self.db.connection.execute("SELECT * FROM connections")]

    def search(self, query: str) -> list[str]:
        needle = f"%{query.lower()}%"
        rows = self.db.connection.execute(
            """SELECT id FROM items WHERE lower(payload_json) LIKE ?
               OR lower(tags_json) LIKE ? OR lower(status) LIKE ?
               UNION SELECT id FROM connections WHERE lower(label) LIKE ?
               OR lower(relation_type) LIKE ? LIMIT 200""",
            (needle, needle, needle, needle, needle),
        ).fetchall()
        return [row[0] for row in rows]

    def save_record(self, record: AnalysisRecord) -> None:
        record.modified_at = now_iso()
        with self.db.connection:
            self.db.connection.execute(
                """INSERT INTO analysis_records
                (id,kind,title,status,tags_json,item_ids_json,data_json,created_at,modified_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                kind=excluded.kind,title=excluded.title,status=excluded.status,
                tags_json=excluded.tags_json,item_ids_json=excluded.item_ids_json,
                data_json=excluded.data_json,modified_at=excluded.modified_at""",
                (record.id, record.kind, record.title, record.status,
                 json.dumps(record.tags, ensure_ascii=False),
                 json.dumps(record.item_ids, ensure_ascii=False),
                 json.dumps(record.data, ensure_ascii=False),
                 record.created_at, record.modified_at),
            )

    def delete_record(self, record_id: str) -> None:
        with self.db.connection:
            self.db.connection.execute("DELETE FROM analysis_records WHERE id=?", (record_id,))

    def load_records(self, kind: str | None = None) -> list[AnalysisRecord]:
        sql = "SELECT * FROM analysis_records"
        params: tuple = ()
        if kind:
            sql += " WHERE kind=?"
            params = (kind,)
        sql += " ORDER BY modified_at DESC"
        return [AnalysisRecord(
            id=row["id"], kind=row["kind"], title=row["title"], status=row["status"],
            tags=json.loads(row["tags_json"]), item_ids=json.loads(row["item_ids_json"]),
            data=json.loads(row["data_json"]), created_at=row["created_at"],
            modified_at=row["modified_at"],
        ) for row in self.db.connection.execute(sql, params)]

    def search_records(self, query: str) -> list[AnalysisRecord]:
        needle = f"%{query.lower()}%"
        rows = self.db.connection.execute(
            """SELECT * FROM analysis_records WHERE lower(title) LIKE ?
               OR lower(status) LIKE ? OR lower(tags_json) LIKE ?
               OR lower(data_json) LIKE ? OR lower(item_ids_json) LIKE ?
               ORDER BY modified_at DESC LIMIT 200""",
            (needle, needle, needle, needle, needle),
        )
        return [AnalysisRecord(
            id=row["id"], kind=row["kind"], title=row["title"], status=row["status"],
            tags=json.loads(row["tags_json"]), item_ids=json.loads(row["item_ids_json"]),
            data=json.loads(row["data_json"]), created_at=row["created_at"],
            modified_at=row["modified_at"],
        ) for row in rows]
