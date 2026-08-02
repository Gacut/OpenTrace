from app.models import BoardItemModel, ConnectionModel, ItemType


def test_item_roundtrip_and_copy():
    original = BoardItemModel(
        ItemType.NOTE, 10, 20,
        payload={"title": "A", "attachments": [{"filename": "source.txt"}]},
        tags=["ważne"],
    )
    restored = BoardItemModel.from_dict(original.to_dict())
    duplicate = original.copy()
    assert restored == original
    assert duplicate.id != original.id
    assert (duplicate.x, duplicate.y) == (34, 44)
    duplicate.payload["attachments"].append({"filename": "second.zip"})
    assert len(original.payload["attachments"]) == 1


def test_connection_defaults_are_analytically_neutral():
    connection = ConnectionModel("a", "b")
    assert connection.confidence == "nieznany"
    assert connection.relation_type == "jest powiązany z"
