from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import BoardItemModel, ConnectionModel, ItemType
from app.services import CaseManager
from app.storage import CaseRepository


def main():
    root = PROJECT_ROOT / "demo" / "Demo OSINT"
    paths, db, _ = CaseManager.create(root, "Demo OSINT", "Lokalny projekt demonstracyjny")
    note = BoardItemModel(ItemType.NOTE, -300, -80, payload={
        "title": "Punkt startowy", "text": "To jest przykładowa notatka.\nhttps://example.org",
        "color": "#facc15",
    })
    pin = BoardItemModel(ItemType.PIN, 80, -30, 140, 110, payload={
        "name": "Obiekt A", "description": "Dane demonstracyjne",
        "color": "#8b5cf6", "icon": "●",
    })
    edge = ConnectionModel(note.id, pin.id, label="wymaga weryfikacji",
                           confidence="przypuszczenie")
    CaseRepository(db).save_all([note, pin], [edge])
    db.close()
    print(paths.root)


if __name__ == "__main__":
    main()
