from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton, QComboBox, QDockWidget, QLabel, QLineEdit, QMenu,
    QTabWidget, QTextEdit, QWidget,
)


_language = "pl"

EN = {
    "Plik": "File", "Edycja": "Edit", "Widok": "View", "O programie": "About",
    "Nowa sprawa…": "New case…", "Otwórz sprawę…": "Open case…", "Zapisz": "Save",
    "Eksport tablicy do PNG…": "Export board to PNG…",
    "Eksport strukturalny JSON…": "Export structured JSON…",
    "Spakuj sprawę do pliku ZIP…": "Pack case to ZIP…",
    "Rozpakuj sprawę z pliku ZIP…": "Unpack case from ZIP…",
    "Zamknij sprawę": "Close case", "Dodaj notatkę": "Add note",
    "Dodaj pinezkę": "Add pin", "Dodaj obraz…": "Add image…",
    "Nowa notatka": "New note", "Nowa pinezka": "New pin",
    "Dodaj obraz": "Add image",
    "Połącz zaznaczone": "Connect selected", "Usuń zaznaczone": "Delete selected",
    "Dopasuj wszystko": "Fit all", "Pokaż siatkę": "Show grid", "Szukaj…": "Search…",
    "Statystyki sprawy": "Case statistics", "Tylko odczyt": "Read-only",
    "Pokaż/ukryj warstwę…": "Show/hide layer…", "Górny pasek narzędzi": "Top toolbar",
    "Wyłącz animację na ekranie głównym": "Disable home screen animation",
    "Narzędzia": "Tools", "Zasobnik narzędzi OSINT": "OSINT tool library",
    "Organizacja analizy": "Analysis workspace", "Notatka": "Note",
    "Nowa Sprawa": "New Case", "Otwórz sprawę": "Open Case",
    "Rozpakuj sprawę z pliku ZIP": "Unpack case from ZIP",
    "Utwórz nową sprawę lub otwórz istniejący projekt lokalny.":
        "Create a new case or open an existing local project.",
    "Zadania": "Tasks", "Do weryfikacji": "To verify", "Źródła": "Sources",
    "Hipotezy": "Hypotheses", "Dziennik": "Journal", "Dodaj": "Add",
    "Edytuj": "Edit", "Edycja": "Edit", "Usuń": "Delete",
    "Pokaż element": "Show item", "Właściwości": "Properties",
    "Właściwości OSINT": "OSINT properties", "Zdjęcie": "Image",
    "Zapisz": "Save", "Anuluj": "Cancel", "Zamknij": "Close",
    "Nazwa / tytuł:": "Name / title:", "Status / kategoria:": "Status / category:",
    "Tagi:": "Tags:", "Powiązane UUID:": "Linked UUIDs:",
    "Opis / notatka:": "Description / note:", "Priorytet:": "Priority:",
    "Priorytet / powód:": "Priority / reason:", "URL / ścieżka:": "URL / path:",
    "Pewność 0–100:": "Confidence 0–100:", "Odblokuj edycję": "Unlock editing",
    "Zablokuj edycję": "Lock editing", "Wybierz z tablicy…": "Select from board…",
    "Wybierz elementy z tablicy": "Select board items",
    "Zaznacz jeden lub kilka elementów:": "Select one or more items:",
    "Tytuł / nazwa:": "Title / name:", "Treść / opis:": "Content / description:",
    "Tytuł / nazwa pliku:": "Title / filename:", "Status:": "Status:",
    "Klasyfikacja:": "Classification:", "Źródło:": "Source:",
    "URL źródła:": "Source URL:", "Aliasy:": "Aliases:",
    "Aliasy (po jednym wierszu):": "Aliases (one per line):",
    "Widoczność:": "Visibility:", "Widoczność w eksporcie:": "Export visibility:",
    "Warstwa:": "Layer:", "Typ relacji:": "Relationship type:",
    "SHA-256:": "SHA-256:", "Rozmiar pliku:": "File size:",
    "Pewność:": "Confidence:", "Etykieta:": "Label:",
    "Kierunek strzałek:": "Arrow direction:", "Przód": "Forward", "Tył": "Backward",
    "Tło": "Background", "Tytuł": "Title", "Treść": "Content",
    "Zmień kolory notatki": "Change note colors",
    "Kolor tła całej notatki": "Color of the entire note background",
    "Kolor czcionki tytułu": "Title font color", "Kolor czcionki treści": "Body font color",
    "Wpisz tytuł, treść, tag, źródło lub relację…":
        "Enter a title, content, tag, source, relationship or UUID…",
    "Szukaj w sprawie": "Search case", "Szukana fraza:": "Search phrase:",
    "Wpisz co najmniej 2 znaki.": "Enter at least 2 characters.",
    "Wystąpienia w sprawie:": "Occurrences in case:",
    "Nie przypisano do żadnego elementu": "No item has been assigned",
    "Nie wybrano notatki": "No note selected", "Wybierz notatkę na tablicy.":
        "Select a note on the board.",
    "Brak właściwości.": "No properties.", "UUID można zaznaczyć i skopiować.":
        "The UUID can be selected and copied.",
    "Pokaż w eksploratorze plików": "Show in File Explorer",
    "Podgląd obrazu": "Image preview", "Zmień kolor": "Change color",
    "Dodaj do weryfikacji": "Add for verification", "Duplikuj": "Duplicate",
    "Zablokuj": "Lock", "Odblokuj": "Unlock",
    "Zmień kolor linii": "Change line color", "Edytuj znaczenie relacji":
        "Edit relationship meaning", "Utwórz zadanie": "Create task",
    "Znaczenie relacji": "Relationship meaning",
    "zna": "knows", "jest powiązany z": "is connected to",
    "należy do": "belongs to", "pracuje dla": "works for",
    "jest właścicielem": "owns", "korzysta z": "uses",
    "kontaktował się z": "contacted", "mieszka w": "lives in",
    "przebywał w": "stayed in", "opublikował": "published",
    "udostępnił": "shared", "jest autorem": "is the author of",
    "jest kopią": "is a copy of",
    "może być tą samą osobą": "may be the same person as",
    "używa tego samego pseudonimu": "uses the same alias",
    "używa tego samego adresu e-mail": "uses the same email address",
    "używa tego samego numeru telefonu": "uses the same phone number",
    "używa tego samego urządzenia": "uses the same device",
    "wystąpił w tym samym miejscu": "appeared in the same place",
    "wydarzyło się przed": "happened before",
    "wydarzyło się po": "happened after",
    "potwierdza": "supports", "przeczy": "contradicts",
    "relacja nieznana": "unknown relationship",
    "Dodaj zdjęcie": "Add image", "Wyśrodkuj widok tutaj": "Center view here",
    "Polski": "Polish", "Angielski": "English", "Język": "Language",
    "Język:": "Language:",
    "Dodaj narzędzie OSINT": "Add OSINT tool", "Edytuj narzędzie": "Edit tool",
    "+ Kategoria": "+ Category", "Bez kategorii": "Uncategorized",
    "Opis zastosowania:": "Usage description:",
    "Wybierz narzędzie.": "Select a tool.", "Zmień nazwę": "Rename",
    "Usuń kategorię": "Delete category", "Otwórz link": "Open link",
    "Kategoria narzędzi:": "Tool category:", "Narzędzia:": "Tools:",
    "Brak opisu.": "No description.", "Nazwa:": "Name:", "Link:": "Link:",
    "Opis:": "Description:", "Kategoria:": "Category:",
    "Nowa kategoria": "New category", "Zmień nazwę kategorii": "Rename category",
    "Zmiana języka": "Language change",
    "Zmiana języka zostanie zastosowana po ponownym uruchomieniu OpenTrace.":
        "The language change will be applied after restarting OpenTrace.",
    "Dane pozostają lokalnie na tym komputerze.": "Data remains local on this computer.",
    "Zapisano": "Saved", "Spakowano sprawę:": "Case packed:",
    "Rozpakowano i otwarto sprawę:": "Case unpacked and opened:",
    "Sprawa została zapisana i zamknięta.": "The case has been saved and closed.",
    "Tryb tylko do odczytu — edycja jest zablokowana.":
        "Read-only mode — editing is disabled.",
    "Zaimportowano obrazów:": "Images imported:",
    "Tryb tylko do odczytu włączony.": "Read-only mode enabled.",
    "Edycja ponownie włączona.": "Editing enabled again.",
    "Wyeksportowano:": "Exported:", "Zapisano widok tablicy.": "Board view saved.",
    "Do zrobienia": "To do", "W trakcie": "In progress", "Zablokowane": "Blocked",
    "Do ponownej weryfikacji": "Recheck", "Ukończone": "Completed",
    "Odrzucone": "Rejected", "Nowe": "New", "Potwierdzone": "Confirmed",
    "Do sprawdzenia": "To review", "Ważne": "Important", "Zarchiwizowane": "Archived",
    "Niepotwierdzone": "Unconfirmed", "Brak wystarczających danych": "Insufficient data",
    "Dostępne": "Available", "Niedostępne": "Unavailable", "Usunięte": "Deleted",
    "Zmienione": "Changed", "Zarchiwizowane lokalnie": "Archived locally",
    "Nieznane": "Unknown", "Nowa": "New", "Analizowana": "Under analysis",
    "Prawdopodobna": "Likely", "Mało prawdopodobna": "Unlikely",
    "Potwierdzona": "Confirmed", "Odrzucona": "Rejected",
    "Wymaga dodatkowych danych": "Needs more data", "notatka": "note",
    "element": "item", "relacja": "relationship", "modyfikacja": "modification",
    "usunięcie": "deletion", "przywrócenie": "restoration", "eksport": "export",
    "decyzja": "decision", "publiczne": "public", "wewnętrzne": "internal",
    "poufne": "confidential", "wyłączone z eksportu": "excluded from export",
    "Materiały źródłowe": "Source materials", "Notatki analityczne": "Analytical notes",
    "Nieokreślona": "Unspecified", "nieznany": "unknown",
    "Fakt bezpośrednio wynikający ze źródła": "Fact directly supported by the source",
    "Interpretacja analityka": "Analyst interpretation", "Przypuszczenie": "Assumption",
    "Informacja niepotwierdzona": "Unconfirmed information",
    "Informacja sprzeczna": "Conflicting information", "Pytanie otwarte": "Open question",
    "przypuszczenie": "assumption", "prawdopodobne": "likely",
    "potwierdzone": "confirmed", "OK": "OK",
    "Wysuń zasobnik narzędzi OSINT": "Open OSINT tool library",
    "Schowaj zasobnik narzędzi OSINT": "Hide OSINT tool library",
    "Wysuń panel analizy": "Open analysis panel",
    "Schowaj panel analizy": "Hide analysis panel",
    "Wysuń panel notatki": "Open note panel",
    "Schowaj panel notatki": "Hide note panel",
    "Dwuklik: edycja • Prawy przycisk: opcje":
        "Double-click: edit • Right-click: options",
    "Nazwę można zaznaczyć i skopiować.":
        "The name can be selected and copied.",
    "Opis można zaznaczyć i skopiować.":
        "The description can be selected and copied.",
    "Tekst można zaznaczyć i skopiować skrótem Ctrl+C. Kliknięcie linku otwiera domyślną przeglądarkę.":
        "Text can be selected and copied with Ctrl+C. Clicking a link opens the default browser.",
    "Możesz zaznaczać i kopiować tekst. Kliknięcie podświetlonego linku otwiera domyślną przeglądarkę systemową.":
        "You can select and copy text. Clicking a highlighted link opens the system's default browser.",
    "Powiązany rekord analityczny": "Linked analysis record",
}

_EN_REVERSE = {value: key for key, value in EN.items()}
SOURCE_TEXT_ROLE = Qt.ItemDataRole.UserRole + 127


def set_language(language: str) -> None:
    global _language
    _language = language if language in {"pl", "en"} else "pl"


def language() -> str:
    return _language


def tr(text: str) -> str:
    if _language != "en":
        return text
    translated = EN.get(text)
    if translated is not None:
        return translated
    for source, target in (
        ("Podgląd obrazu — ", "Image preview — "),
        ("Edytuj: ", "Edit: "),
        ("Dodaj: ", "Add: "),
        ("UUID relacji: ", "Relationship UUID: "),
    ):
        if text.startswith(source):
            return target + tr(text[len(source):])
    return text


JOURNAL_TITLES_EN = {
    "Utworzono notatkę": "Created note",
    "Utworzono pinezkę": "Created pin",
    "Utworzono połączenie": "Created connection",
    "Edytowano notatkę": "Edited note",
    "Zmieniono kolory notatki": "Changed note colors",
    "Zmieniono właściwości notatki": "Changed note properties",
    "Zmieniono właściwości elementu": "Changed item properties",
    "Zmieniono znaczenie relacji": "Changed relationship meaning",
    "Edytowano nazwę lub opis zdjęcia": "Edited image name or description",
    "Zmieniono właściwości OSINT zdjęcia": "Changed image OSINT properties",
    "Wyeksportowano dane strukturalne JSON": "Exported structured JSON data",
}

JOURNAL_PREFIXES_EN = (
    ("Zaimportowano plik: ", "Imported file: "),
    ("Usunięto notatkę: ", "Deleted note: "),
    ("Usunięto zdjęcie: ", "Deleted image: "),
    ("Usunięto pinezkę: ", "Deleted pin: "),
    ("Usunięto tekst: ", "Deleted text: "),
    ("Usunięto grupę: ", "Deleted group: "),
    ("Usunięto element: ", "Deleted item: "),
    ("Usunięto połączenie: ", "Deleted connection: "),
    ("Przywrócono usunięty element (CTRL + Z): ", "Restored deleted item (CTRL + Z): "),
    ("Przywrócono usunięte połączenie (CTRL + Z): ", "Restored deleted connection (CTRL + Z): "),
    ("Zmieniono UUID: ", "Changed UUID: "),
    ("Zmieniono: ", "Changed: "),
)


def journal_title(text: str) -> str:
    if _language != "en":
        return text
    if text in JOURNAL_TITLES_EN:
        return JOURNAL_TITLES_EN[text]
    for source, target in JOURNAL_PREFIXES_EN:
        if text.startswith(source):
            return target + text[len(source):]
    return text


def source_text(text: str) -> str:
    return _EN_REVERSE.get(text, text) if _language == "en" else text


def set_combo_source(combo: QComboBox, value: str) -> None:
    for index in range(combo.count()):
        original = combo.itemData(index, SOURCE_TEXT_ROLE)
        if (original if original is not None else combo.itemText(index)) == value:
            combo.setCurrentIndex(index)
            return
    combo.setCurrentText(value)


def combo_source_text(combo: QComboBox) -> str:
    if combo.isEditable() and (
        combo.currentIndex() < 0 or combo.currentText() != combo.itemText(combo.currentIndex())
    ):
        return source_text(combo.currentText())
    original = combo.currentData(SOURCE_TEXT_ROLE)
    return original if original is not None else source_text(combo.currentText())


class TranslationEventFilter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._translating = False

    def eventFilter(self, watched, event):
        if (
            not self._translating and _language == "en"
            and event.type() == QEvent.Type.Show and isinstance(watched, QWidget)
        ):
            self._translating = True
            try:
                self.translate_tree(watched)
            finally:
                self._translating = False
        return False

    def translate_tree(self, root: QWidget) -> None:
        widgets = [root, *root.findChildren(QWidget)]
        for widget in widgets:
            try:
                if widget.windowTitle():
                    widget.setWindowTitle(tr(widget.windowTitle()))
                if widget.toolTip():
                    widget.setToolTip(tr(widget.toolTip()))
                if isinstance(widget, QLabel):
                    widget.setText(tr(widget.text()))
                elif isinstance(widget, QAbstractButton):
                    widget.setText(tr(widget.text()))
                elif isinstance(widget, QLineEdit):
                    widget.setPlaceholderText(tr(widget.placeholderText()))
                elif isinstance(widget, QTextEdit):
                    widget.setPlaceholderText(tr(widget.placeholderText()))
                elif isinstance(widget, QTabWidget):
                    for index in range(widget.count()):
                        widget.setTabText(index, tr(widget.tabText(index)))
                elif isinstance(widget, QComboBox):
                    for index in range(widget.count()):
                        if widget.itemData(index, SOURCE_TEXT_ROLE) is None:
                            widget.setItemData(index, widget.itemText(index), SOURCE_TEXT_ROLE)
                        widget.setItemText(index, tr(widget.itemText(index)))
                if isinstance(widget, QDockWidget):
                    widget.setWindowTitle(tr(widget.windowTitle()))
                if isinstance(widget, QMenu):
                    self._translate_actions(widget.actions())
            except RuntimeError:
                continue
        menu_bar = getattr(root, "menuBar", lambda: None)()
        if menu_bar:
            self._translate_actions(menu_bar.actions())

    def _translate_actions(self, actions: list[QAction]) -> None:
        for action in actions:
            action.setText(tr(action.text()))
            action.setToolTip(tr(action.toolTip()))


def install_translation_filter(application) -> TranslationEventFilter:
    current = getattr(application, "_opentrace_translation_filter", None)
    if current is None:
        current = TranslationEventFilter(application)
        application.installEventFilter(current)
        application._opentrace_translation_filter = current
    return current
