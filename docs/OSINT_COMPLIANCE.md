# Audyt zgodności funkcji OSINT

Stan po rozszerzeniu wersji 0.2. Oznaczenia: **pełne**, **częściowe**, **planowane**.

## Zaimplementowane

- **pełne**: lokalność i brak automatycznych połączeń sieciowych;
- **pełne**: trwałe typy, kierunek i ręczna pewność relacji; typ relacji może
  być własnym tekstem, a przypuszczenie jest linią przerywaną;
- **pełne**: zadania, kolejka „Do weryfikacji”, biblioteka źródeł, hipotezy
  z ręczną pewnością 0–100 i lokalny dziennik;
- **pełne**: powiązanie powyższych rekordów z UUID elementów tablicy oraz
  przejście z rekordu do elementu;
- **pełne**: statusy, tagi, źródło, URL źródła, aliasy, klasyfikacja
  fakt/interpretacja/przypuszczenie i poziom widoczności elementu;
- **pełne**: SHA-256, rozmiar i data importu obrazów, wykrywanie identycznego
  skrótu oraz ręczny wybór użycia istniejącego pliku lub osobnej kopii;
- **pełne**: globalne wyszukiwanie w elementach i rekordach analitycznych;
- **pełne**: podstawowe statystyki bez automatycznych ocen analitycznych;
- **pełne**: eksport strukturalny JSON bez ścieżek absolutnych;
- **pełne**: walidacja UUID, brakujących/zmienionych plików, duplikatów SHA,
  zerwanych relacji i elementów położonych skrajnie daleko;
- **pełne**: tryb tylko do odczytu;
- **pełne**: warstwa przypisywana elementowi, pokazywanie/ukrywanie warstw
  oraz zapisane widoki kamery z ukrytymi warstwami.

## Zaimplementowane częściowo

- **częściowe**: hipotezy przechowują opis, status, pewność i przypisane
  materiały; rozdzielanie materiałów na wspierające/przeczące wymaga
  rozbudowanego selektora;
- **częściowe**: źródła mają podstawowe dane i powiązania, ale bez osobnych
  formularzy dla wszystkich dat oraz eksportu bibliografii;
- **częściowe**: dziennik rejestruje kluczowe zdarzenia i wpisy ręczne,
  ale nie ma jeszcze eksportu HTML/PDF/CSV;
- **częściowe**: warstwy mają nazwę i widoczność; blokada, kolejność i
  przezroczystość wymagają dedykowanego menedżera;
- **częściowe**: ochrona eksportu ma klasyfikację pól, lecz eksport PNG nie
  wykonuje jeszcze redakcji obrazu;
- **częściowe**: kopie bezpieczeństwa pełnią rolę technicznych migawek, ale
  brak porównania i przywracania z poziomu GUI.

## Planowane zgodnie z kolejnością załącznika

Grupy z członkostwem, elementy strukturalne osoba/podmiot/domena/lokalizacja,
scalanie z undo, chronologia dat nieprecyzyjnych, konflikty informacji,
automatyczny widok grafu, fokus relacji, porównanie elementów, raporty
HTML/PDF/CSV, redakcja obrazów, prezentacja, checklisty, pełne migawki i diff,
recovery po awarii, szablony, mapa offline, import CSV z mapowaniem,
GraphML/GEXF oraz bezpieczny interfejs rozszerzeń.

Funkcje planowane nie są oznaczane w interfejsie jako gotowe. Aplikacja nie
scala danych, nie potwierdza relacji i nie zmienia pewności hipotez bez
świadomej decyzji użytkownika.
