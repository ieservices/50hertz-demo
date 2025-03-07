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
origins = [
    "https://50hertzfastapireactapp.azurewebsites.net",  # React app URL
    "http://localhost:8000",  # for local development, if needed
    "http://localhost:3000",  # for local development, if needed
]

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
CHARGE_CURRENT_A = 500  # Ladestrom (Übertrieben, aber gut für die Demo)
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
STATE_FILE = "data/battery_state.json"
CSV_FILE = "data/battery_log.csv"

# Globaler Zustand
current_price = random.uniform(15, 40)  # Strompreis in ct/€
battery_capacity = None  # wird im Startup initialisiert
charging = False  # Gibt an, ob die Batterie gerade geladen wird
total_consumption = 0.0  # Kumulative Verbrauch in kWh

simulation_start = time.monotonic()


# Pydantic-Modell für die API-Antwort
class StatusResponse(BaseModel):
    current_price: float  # in ct (€)
    charging: str  # "Ein" wenn geladen, sonst "Aus"
    battery_capacity_kwh: float = Field(..., gt=0)  # Batteriekapazität in kWh
    battery_capacity_percent: float = Field(..., gt=0)  # Batteriekapazität in %
    facility_consumption_rate: float = Field(..., gt=0)  # Verbrauchsrate in kWh pro Sekunde
    total_consumption_kwh: float = Field(..., gt=0)  # Kumulierte Leistung in kWh


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


def save_battery_state(battery_capacity, current_price, charging, battery_percent, facility_rate, total_consumption):
    data = {
        "battery_capacity_kwh": round(battery_capacity, 3),
        "current_price": round(current_price, 3),
        "charging": "On" if charging else "Off",
        "battery_capacity_percent": round(battery_percent, 3),
        "facility_consumption_rate": round(facility_rate, 3),
        "total_consumption_kwh": round(total_consumption, 3),
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


# CSV-Logfile initialisieren (mit Header, falls nicht vorhanden)
if not os.path.exists(CSV_FILE):
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    with open(CSV_FILE, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "timestamp",
            "current_price",
            "charging",
            "battery_capacity_kwh",
            "battery_capacity_percent",
            "facility_consumption_rate",
            "total_consumption_kwh",
        ])


async def update_loop():
    global current_price, battery_capacity, charging, total_consumption
    while True:
        elapsed = time.monotonic() - simulation_start

        # Generator-Bedingung: Alle 10 Minuten für 3 Minuten wird der Preis auf 20 ct gesetzt
        if (elapsed % 600) < 180:
            current_price = 20
        else:
            # Preisaktualisierung: graduelle Änderung, maximal 100% pro Minute (ca. 1.0/60 pro Sekunde)
            delta_max = current_price * 1.0 / 60
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

        # Cumulative consumption update (every second)
        total_consumption += facility_consumption_rate

        await asyncio.sleep(1)


async def log_status_loop():
    global current_price, battery_capacity, charging, total_consumption
    while True:
        await asyncio.sleep(60)  # Alle 60 Sekunden protokollieren
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
        with open(CSV_FILE, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                timestamp,
                round(current_price, 3),
                "On" if charging else "Off",
                round(battery_capacity, 3),
                round(battery_percent, 3),
                round(facility_consumption_rate, 6),
                round(total_consumption, 3),
            ])
        # Persist the state to a JSON file
        save_battery_state(battery_capacity, current_price, charging, battery_percent, facility_consumption_rate,
                           total_consumption)


async def reset_battery_capacity_loop():
    """
    Setzt die Batteriekapazität jeden Tag um 0:15 Uhr zurück auf 10% der Gesamtkapazität und
    setzt den kumulativen Verbrauch zurück.
    """
    global battery_capacity, total_consumption
    while True:
        # Warte 10 Sekunden, bevor erneut geprüft wird
        await asyncio.sleep(10)
        now = time.localtime()
        reset_hour = 10
        reset_minute = 30
        if now.tm_hour == reset_hour and now.tm_min == reset_minute:
            battery_capacity = BESS_CAPACITY_KWH * 0.10
            total_consumption = 0.0
            battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
            save_battery_state(battery_capacity, current_price, charging, battery_percent, total_consumption,
                               facility_consumption_rate)
            print("Batteriekapazität wurde um %s:%s Uhr zurückgesetzt." % (reset_hour, reset_minute))
            # Warte mindestens 60 Sekunden, um zu verhindern, dass die Rücksetzung mehrmals innerhalb derselben Minute erfolgt.
            await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    global battery_capacity
    # Batteriezustand laden oder, falls nicht vorhanden, initial auf 10% setzen
    state = load_battery_state()
    if state is None:
        battery_capacity = BESS_CAPACITY_KWH * 0.10
    else:
        battery_capacity = state

    battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
    save_battery_state(battery_capacity, current_price, charging, battery_percent, facility_consumption_rate,
                       total_consumption)

    # Starte die Hintergrund-Tasks für Update-Loop und CSV-Logging
    asyncio.create_task(update_loop())
    asyncio.create_task(log_status_loop())
    asyncio.create_task(reset_battery_capacity_loop())


@app.get("/get_status", response_model=StatusResponse)
async def get_status():
    battery_percent = (battery_capacity / BESS_CAPACITY_KWH) * 100
    return StatusResponse(
        current_price=round(current_price, 3),
        charging="Ein" if charging else "Aus",
        battery_capacity_kwh=round(battery_capacity, 3),
        battery_capacity_percent=round(battery_percent, 3),
        facility_consumption_rate=round(facility_consumption_rate, 3),
        total_consumption_kwh=round(total_consumption, 3),
    )
