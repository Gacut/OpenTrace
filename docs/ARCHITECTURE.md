# Architektura

## Warstwy

- `models` — niezależne od Qt modele elementów, relacji i spraw;
- `storage` — wersjonowany schemat SQLite i repozytorium;
- `services` — katalogi spraw, import plików, kopie zapasowe i eksport;
- `graphics` — elementy `QGraphicsItem`, relacje i widok tablicy;
- `ui` — okno główne, dialogi i panel wyszukiwania;
- `commands` — odwracalne operacje pod `QUndoStack`.

UI nie zapisuje SQL bezpośrednio. `CaseController` jest granicą pomiędzy
widokiem a repozytorium i emituje sygnał zmian obsługiwany przez autosave.

## Schemat bazy

`meta(key, value)` przechowuje wersję schematu i dane sprawy.
`items` ma wspólne kolumny (UUID, typ, geometria, z, daty, status, tagi,
blokada) oraz `payload_json` dla pól właściwych danemu typowi.
`connections` odwołuje się kluczami obcymi do trwałych UUID elementów i
przechowuje styl, etykietę, kierunek, typ oraz pewność relacji. Opcjonalne
`branch_from_id` wskazuje UUID linii nadrzędnej, dzięki czemu rozgałęzienia
nie są zapisywane jako nietrwałe współrzędne.
`analysis_records` jest wspólnym, wersjonowanym magazynem zadań, źródeł,
hipotez, wpisów dziennika, kolejki weryfikacji i zapisanych widoków.
Indeksy obejmują typ, status, datę modyfikacji i oba końce relacji.
Migracje są wykonywane kolejno według `PRAGMA user_version`.

## Najważniejsze klasy

- `BoardItemModel`, `ConnectionModel`, `CaseMetadata`;
- `Database`, `CaseRepository`, `CaseManager`;
- `CaseController`;
- `BoardScene`, `BoardView`, `BaseNodeItem`, `NoteItem`, `ImageItem`,
  `PinItem`, `ConnectionItem`;
- `AddItemCommand`, `DeleteItemsCommand`, `MoveItemCommand`,
  `AddConnectionCommand`;
- `MainWindow`.

## Wydajność

Scena korzysta z indeksu BSP, obrazy są wczytywane z miniatur, zapis odbywa
się transakcyjnie i z opóźnieniem, a linie aktualizują tylko geometrię
połączonych węzłów. Eksport całej sceny sprawdza limit wymiarów. Dla spraw
rzędu dziesiątek tysięcy elementów kolejne etapy powinny dodać wirtualizację
paneli, poziomy szczegółowości oraz zapis przyrostowy.

## Etapy

1. MVP: sprawy, tablica, trzy typy elementów, relacje, SQLite, undo/redo,
   autosave, wyszukiwanie i PNG.
2. Organizacja: właściwości, grupy, rozbudowane tagi/statusy, zadania,
   inbox, zapisane widoki i warstwy.
3. OSINT: źródła, integralność, dziennik, chronologia, hipotezy i konflikty.
4. Analiza/raporty: graf, statystyki, porównanie, HTML/PDF/JSON i redakcja.
5. Odporność: migawki, walidacja, recovery, portable i bezpieczne rozszerzenia.

Zasada projektowa: analizatory mogą tylko proponować wynik; relacje, hipotezy
i klasyfikację faktów zawsze zatwierdza człowiek.
