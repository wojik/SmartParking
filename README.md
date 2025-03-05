# Inteligentny Parking System

System sterowania inteligentnym parkingiem opartym na Raspberry Pi 4. W projekcie wykorzystano technologię rozpoznawania tablic rejestracyjnych przy użyciu OpenCV i pytesseract, obsługę kart RFID (czytnik MFRC522), wyświetlacz LCD oraz czujniki parkowania podłączone do GPIO. Dodatkowo system steruje serwomechanizmami, które otwierają lub zamykają szlabany wjazdowe i wyjazdowe.

## Wymagania

- **Sprzęt:**
  - Raspberry Pi 4
  - Kamera kompatybilna z Raspberry Pi
  - Czytnik RFID MFRC522
  - Wyświetlacz LCD z interfejsem I2C (np. PCF8574, adres: 0x27)
  - Serwomechanizmy (2 sztuki: wjazdowy i wyjazdowy)
  - Czujniki parkowania - fototranzystory (podłączone do pinów GPIO: 1, 7, 26, 19, 13, 6, 5, 0, 15, 18)

- **Oprogramowanie:**
  - Python 3
  - Biblioteki:
    - `opencv-python`
    - `pytesseract` (wraz z zainstalowanym Tesseract OCR)
    - `pigpio`
    - `numpy`
    - `sqlite3` (moduł wbudowany w Pythona)
    - `mfrc522`
    - `RPi.GPIO`
    - `RPLCD`
    - `threading` (moduł wbudowany)

## Instalacja

1. **Instalacja bibliotek Pythona:**

   ```bash
   pip install opencv-python pytesseract pigpio numpy mfrc522 RPi.GPIO RPLCD
   ```

2. **Instalacja Tesseract OCR:**

   - Na systemie Debian/Ubuntu:
     ```bash
     sudo apt-get install tesseract-ocr
     ```

3. **Konfiguracja pigpio:**

   Uruchom demona `pigpiod`:
   ```bash
   sudo pigpiod
   ```

## Konfiguracja Sprzętu

- **Serwomechanizmy:**  
  Podłącz serwa do pinów GPIO 20 (szlaban wjazdowy) oraz 21 (szlaban wyjazdowy). Skrypt ustawia wartości impulsów, które odpowiadają otwarciu i zamknięciu szlabanów.

- **Czytnik RFID:**  
  Podłącz moduł MFRC522 zgodnie z dokumentacją sprzętową.

- **Wyświetlacz LCD:**  
  Skonfiguruj wyświetlacz LCD przez interfejs I2C.

- **Czujniki parkowania:**  
  Podłącz czujniki do pinów GPIO: 1, 7, 26, 19, 13, 6, 5, 0, 15, 18.

## Baza Danych

Skrypt korzysta z bazy danych SQLite o nazwie `parking_database.db` z tabelą `parking_records`. Tabela powinna zawierać co najmniej następujące kolumny:

- `rfid_uid` – identyfikator karty RFID
- `plate_number` – numer rejestracyjny pojazdu
- `parking_status` – status pojazdu (True/False) określający, czy pojazd znajduje się na parkingu

Przykład polecenia SQL do utworzenia tabeli:

```sql
CREATE TABLE parking_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfid_uid INTEGER,
    plate_number TEXT,
    parking_status BOOLEAN
);
```

## Uruchomienie

Aby uruchomić system, wykonaj poniższe kroki:

1. Upewnij się, że demon `pigpiod` działa:
   ```bash
   sudo pigpiod
   ```

2. Uruchom skrypt:
   ```bash
   python3 parking_system.py
   ```

Podczas działania system:
- **Wejście pojazdu:**  
  System przetwarza obraz z kamery, rozpoznaje tablicę rejestracyjną i sprawdza jej status w bazie danych. Jeśli pojazd nie znajduje się jeszcze na parkingu, otwiera szlaban wjazdowy.

- **Wyjście pojazdu:**  
  Użytkownik zbliża kartę RFID, system odczytuje UID, sprawdza bazę danych i, jeśli pojazd jest zarejestrowany jako znajdujący się na parkingu, otwiera szlaban wyjazdowy.

- **Monitorowanie miejsca parkingowe:**  
  Czujniki monitorują liczbę wolnych miejsc, a wynik jest wyświetlany na LCD.

## Działanie Systemu

System składa się z trzech głównych wątków:
- **parking_sensor_loop()** – ciągłe monitorowanie i aktualizacja liczby wolnych miejsc parkingowych.
- **rfid_loop()** – obsługa wyjazdu pojazdu przy użyciu czytnika RFID.
- **process_license_plates()** – przetwarzanie obrazu z kamery, rozpoznawanie tablic rejestracyjnych i sterowanie szlabanem wjazdowym.

Wszystkie wątki działają równolegle, dzięki czemu system może obsługiwać wiele zadań jednocześnie.

## Zatrzymywanie Systemu

Po zakończeniu działania systemu wykonywane są procedury czyszczenia:
- Zatrzymanie demona `pigpio`
- Czyszczenie ustawień GPIO
- Czyszczenie wyświetlacza LCD

## Uwagi

- Upewnij się, że wszystkie elementy sprzętowe są prawidłowo podłączone.
- Przed uruchomieniem systemu zweryfikuj konfigurację bazy danych.
- System wykorzystuje wielowątkowość, dlatego zwróć uwagę na potencjalne problemy synchronizacji (np. przy aktualizacji wyświetlacza LCD).



