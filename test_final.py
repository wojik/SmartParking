import cv2
import pytesseract
import re
import time
import pigpio
import numpy as np
import sqlite3
import threading
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# Konfiguracja GPIO
GPIO.setmode(GPIO.BCM)

# Konfiguracja serwomechanizmów
SERVO_PIN_1 = 20  # Szlaban wjazdowy
SERVO_PIN_2 = 21  # Szlaban wyjazdowy
SERVO_OPEN_POS1 = 1750
SERVO_CLOSED_POS1 = 750
SERVO_OPEN_POS2 = 700
SERVO_CLOSED_POS2 = 1700
GATE_OPEN_TIME = 4

# Inicjalizacja pigpio
pi = pigpio.pi()
pi.set_servo_pulsewidth(SERVO_PIN_1, SERVO_CLOSED_POS1)
pi.set_servo_pulsewidth(SERVO_PIN_2, SERVO_CLOSED_POS2)

# Inicjalizacja czytnika RFID
rfid_reader = SimpleMFRC522()

# Inicjalizacja LCD
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8)
lcd_lock = threading.Lock()

# Porty GPIO dla czujników
PARKING_PINS = [1, 7, 26, 19, 13, 6, 5, 0, 15, 18]
for pin in PARKING_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


# Wzór tablicy rejestracyjnej
PLATE_PATTERN = re.compile(r'^P\d{3}$', re.IGNORECASE)


def check_database(query_type, value):
    """Sprawdza status pojazdu w bazie danych"""
    conn = sqlite3.connect('parking_database.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT parking_status FROM parking_records WHERE {query_type} = ?', (value,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def update_database_status(query_type, value, new_status):
    """Aktualizuje status parkingu w bazie danych"""
    conn = sqlite3.connect('parking_database.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE parking_records SET parking_status = ? WHERE {query_type} = ?',
                   (new_status, value))
    conn.commit()
    conn.close()
    print(f"[BAZA DANYCH] Zaktualizowano {query_type}={value} na status={new_status}")


def update_lcd(message):
    """Aktualizuje wyświetlacz LCD"""
    with lcd_lock:
        lcd.cursor_pos = (0, 0)
        lcd.write_string(message.ljust(16))


def parking_sensor_loop():
    """Monitorowanie wolnych miejsc parkingowych"""
    previous_active_count = -1
    while True:
        active_count = sum(GPIO.input(pin) for pin in PARKING_PINS)
        if active_count != previous_active_count:
            lcd.clear()
            lcd.write_string(f'Wolne miejsca:  {active_count}')
            previous_active_count = active_count

        time.sleep(0.2)  # Opóźnienie między próbkami (100ms)


def rfid_loop():
    """Obsługa systemu wyjazdowego RFID"""
    while True:
        try:
            rfid_id, _ = rfid_reader.read_no_block()
            if rfid_id:
                print(f"[RFID] Odczytano UID: {rfid_id}")
                status = check_database('rfid_uid', rfid_id)

                if status is not None:
                    if status:
                        print("[RFID] Otwieranie szlabanu wyjazdowego")
                        pi.set_servo_pulsewidth(SERVO_PIN_2, SERVO_OPEN_POS2)
                        update_database_status('rfid_uid', rfid_id, False)
                        time.sleep(GATE_OPEN_TIME)
                        pi.set_servo_pulsewidth(SERVO_PIN_2, SERVO_CLOSED_POS2)
                    else:
                        print("[RFID] Brak uprawnień: pojazd nie jest na parkingu")
                else:
                    print("[RFID] Nieznana karta RFID")
        except Exception as e:
            print(f"[RFID] Błąd: {str(e)}")
        time.sleep(0.1)


def process_license_plates():
    """Przetwarzanie obrazu dla systemu wjazdowego"""
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Przetwarzanie obrazu
            processed = cv2.resize(frame, (320, 240))
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Rozpoznawanie tekstu
            text = pytesseract.image_to_string(processed, config='--oem 3 --psm 7')
            text = re.sub(r'[^A-Z0-9]', '', text.upper())

            if text and PLATE_PATTERN.match(text):
                print(f"[KAMERA] Wykryto tablicę: {text}")
                status = check_database('plate_number', text)

                if status is not None:
                    if not status:
                        print("[KAMERA] Otwieranie szlabanu wjazdowego")
                        pi.set_servo_pulsewidth(SERVO_PIN_1, SERVO_OPEN_POS1)
                        update_database_status('plate_number', text, True)
                        time.sleep(GATE_OPEN_TIME)
                        pi.set_servo_pulsewidth(SERVO_PIN_1, SERVO_CLOSED_POS1)
                    else:
                        print("[KAMERA] Pojazd już jest na parkingu")
                else:
                    print("[KAMERA] Nieznana tablica rejestracyjna")

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()


if __name__ == "__main__":
    try:
        threading.Thread(target=parking_sensor_loop, daemon=True).start()
        threading.Thread(target=rfid_loop, daemon=True).start()
        process_license_plates()
    finally:
        pi.stop()
        GPIO.cleanup()
        lcd.clear()
        print("System zatrzymany")
