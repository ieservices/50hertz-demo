import os
import csv
import time
import json
import random
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI()

# CORS-Konfiguration: Erlaubt Anfragen von der React-App (http://localhost:3000)
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konstanten
GRID_MAX_POWER_KW = 15  # Netzleistung in kW
GRID_MAX_CURRENT_A = 30  # Netzstrom in A
BESS_CAPACITY_KWH = 230  # Gesamte Batteriekapazität in kWh
BESS_MIN_KWH = BESS_CAPACITY_KWH * 0.10  # Mindestkapazität: 10% (23 kWh)

# Ladeparameter (bei günstigen Preisen)
CHARGE_CURRENT_A = 1500  # Ladestrom (Übertrieben, aber gut für die Demo)
VOLTAGE = 230  # Betriebsspannung in Volt
CHARGE_POWER_KW = (CHARGE_CURRENT_A * VOLTAGE) / 1000  # ca. 5,75 kW
CHARGE_RATE_KWH_PER_SEC = CHARGE_POWER_KW / 3600  # kWh pro Sekunde

# Entladeparameter (bei teurem Strom)
DISCHARGE_RATE_KWH_PER_SEC = CHARGE_RATE_KWH_PER_SEC

# Betriebsverbrauch:
# Täglicher Verbrauch zwischen 800 und 1.400 kWh
daily_consumption_kwh = random.uniform(800, 1400)
facility_consumption_rate = daily_consumption_kwh / 86400  # kWh pro Sekunde

# Dateinamen für Persistenz und Logging
STATE_FILE = "battery_state.json"
CSV_FILE = "battery_log.csv"

# Globaler Zustand
current_price = random.uniform(15, 40)  # Strompreis in ct/€
battery_capacity = None  # wird im Startup initialisiert
charging = False  # Gibt an, ob die Batterie gerade geladen wird

simulation_start = time.monotonic()


# Pydantic-Modell für die API-Antwort
class StatusResponse(BaseModel):
    current_price: float  # in ct/€
    charging: str  # "Ein" wenn geladen, sonst "Aus"
    battery_capacity_kwh: float = Field(..., gt=0)  # Batteriekapazität in kWh
    battery_capacity_percent: float = Field(..., gt=0)  # Batteriekapazität in %


# Hilfsfunktionen zum Laden/Speichern des Batteriezustands im JSON-Format
def load_battery_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("battery_capacity_kwh", None)
            except Exception:
                return None
    return None


def save_battery_state(battery_capacity, current_price, charging, battery_percent):
    data = {
        "battery_capacity_kwh": round(battery_capacity, 3),
        "current_price": round(current_price, 3),
        "charging": "On" if charging else "Off",
        "battery_capacity_percent": round(battery_percent, 3)
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


# CSV-Logfile initialisieren (mit Header, falls nicht vorhanden)
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # CSV-Header gemäß gewünschter Reihenfolge
        writer.writerow(["timestamp", "current_price", "charging", "battery_capacity_kwh", "battery_capacity_percent"])


async def update_loop():
    global current_price, battery_capacity, charging
    while True:
        elapsed = time.monotonic() - simulation_start

        # Generator-Bedingung: Alle 10 Minuten für 3 Minuten wird der Preis auf 20 ct gesetzt
        if (elapsed % 600) < 180:
            current_price = 20
        else:
            # Preisaktualisierung: graduelle Änderung, maximal 40% pro Minute (ca. 0.4/60 pro Sekunde)
            delta_max = current_price * 0.4 / 60
            price_change = random.uniform(-delta_max, delta_max)
            new_price = current_price + price_change
            current_price = max(15, min(new_price, 40))

        # Batteriemanagement:
        if current_price < 25:
            # Bei günstigen Preisen wird geladen, gleichzeitig entlädt der Betrieb (Verbrauch)
            net_change = CHARGE_RATE_KWH_PER_SEC - facility_consumption_rate
            new_capacity = battery_capacity + net_change
            new_capacity = min(new_capacity, BESS_CAPACITY_KWH)
            new_capacity = max(new_capacity, BESS_MIN_KWH)
            battery_capacity = new_capacity
            charging = True
        else:
            # Bei teurem Strom wird die Batterie entladen, bis mindestens 10% erreicht sind
            new_capacity = battery_capacity - DISCHARGE_RATE_KWH_PER_SEC
            battery_capacity = max(new_capacity, BESS_MIN_KWH)
            charging = False

        await asyncio.sleep(1)


async def log_status_loop():
    global current_price, battery_capacity, charging
    while True:
        await asyncio.sleep(60)  # Alle 60 Sekunden protokollieren
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
        # Logge in die CSV-Datei (Rundung mit 3 Nachkommastellen, Reihenfolge wie gewünscht)
        with open(CSV_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                timestamp,
                round(current_price, 3),
                "On" if charging else "Off",
                round(battery_capacity, 3),
                round(battery_percent, 3)
            ])
        # Aktualisiere den persistenten Batteriezustand in battery_state.txt
        save_battery_state(battery_capacity, current_price, charging, battery_percent)


@app.on_event("startup")
async def startup_event():
    global battery_capacity
    # Batteriezustand laden oder, falls nicht vorhanden, initial auf 10% setzen
    state = load_battery_state()

    if state is None:
        battery_capacity = BESS_CAPACITY_KWH * 0.10
    else:
        battery_capacity = state

    # Initialer Save beim Start
    battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
    save_battery_state(battery_capacity, current_price, charging, battery_percent)

    # Starte die Hintergrund-Tasks für Update-Loop und CSV-Logging
    asyncio.create_task(update_loop())
    asyncio.create_task(log_status_loop())


@app.get("/get_status", response_model=StatusResponse)
async def get_status():
    battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
    return StatusResponse(
        current_price=round(current_price, 3),
        charging="Ein" if charging else "Aus",
        battery_capacity_kwh=round(battery_capacity, 3),
        battery_capacity_percent=round(battery_percent, 3)
    )
