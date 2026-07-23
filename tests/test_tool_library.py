import json

from app.services import ToolLibrary


def test_tool_library_persists_between_instances(tmp_path):
    path = tmp_path / "global" / "osint_tools.json"
    first = ToolLibrary(path)
    category = first.add_category("Analiza domen")
    tool = first.add_tool(
        "Przykładowe narzędzie", "https://example.org/tool",
        "Ręczna analiza domeny", category.id,
    )
    second = ToolLibrary(path)
    assert any(value.id == category.id and value.name == "Analiza domen" for value in second.categories)
    loaded = next(value for value in second.tools if value.id == tool.id)
    assert loaded.url == "https://example.org/tool"
    assert loaded.description == "Ręczna analiza domeny"
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_deleting_category_moves_tools_to_remaining_category(tmp_path):
    library = ToolLibrary(tmp_path / "tools.json")
    category = library.add_category("Usuwana")
    tool = library.add_tool("Narzędzie", "https://example.org", "", category.id)
    library.delete_category(category.id)
    assert library.tools[0].id == tool.id
    assert library.tools[0].category_id == library.categories[0].id
