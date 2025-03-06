from fastapi import FastAPI
from pydantic import BaseModel
import random
import asyncio

app = FastAPI()

# Konstanten
GRID_MAX_POWER_KW = 15      # Netzleistung 15 kW
GRID_MAX_CURRENT_A = 30     # Netzstrom 30 A
BESS_CAPACITY_KWH = 230     # Batterie-Kapazität
BESS_MIN_KWH = BESS_CAPACITY_KWH * 0.10  # Mindestkapazität: 10% (23 kWh)

# Im ursprünglichen Text stand "kann mit 10A geladen werden", aber bei Preis <25 ct
# wird die Batterie mit maximal 25 A geladen. Wir simulieren hier den Fall mit 25 A.
CHARGE_CURRENT_A = 25       # Ladestrom bei günstigen Preisen
VOLTAGE = 230               # angenommene Betriebsspannung in Volt
# Berechnung der Leistung (P = U * I) in kW:
CHARGE_POWER_KW = (CHARGE_CURRENT_A * VOLTAGE) / 1000  # ca. 5,75 kW
# Umrechnung auf kWh pro Sekunde:
CHARGE_RATE_KWH_PER_SEC = CHARGE_POWER_KW / 3600

# Wir nehmen an, dass auch beim Entladen ein ähnlicher Leistungswert verwendet wird.
DISCHARGE_RATE_KWH_PER_SEC = CHARGE_RATE_KWH_PER_SEC

# Globaler Zustand (für diese Simulation)
current_price = random.uniform(15, 40)  # Aktueller Strompreis in ct/€
battery_capacity = BESS_CAPACITY_KWH * 0.5  # Starte z. B. bei 50% Kapazität
charging = False  # Zeigt an, ob die Batterie gerade geladen wird

# Pydantic Modell für die Status-Antwort
class StatusResponse(BaseModel):
    current_price: float             # in ct/€
    charging: str                    # "Ein" wenn geladen, sonst "Aus"
    battery_capacity_kwh: float      # Aktuelle Kapazität in kWh
    battery_capacity_percent: float  # Aktuelle Kapazität in %

async def update_loop():
    global current_price, battery_capacity, charging
    while True:
        # Aktualisierung des Strompreises: maximal 40% pro Minute ≙ ca. 0,4/60 pro Sekunde
        delta_max = current_price * 0.4 / 60
        price_change = random.uniform(-delta_max, delta_max)
        new_price = current_price + price_change
        # Begrenzen des Preises auf den Bereich [15, 40] ct/€
        current_price = max(15, min(new_price, 40))

        # Logik zum Batteriemanagement:
        if current_price < 25:
            # Günstiger Preis: Batterie laden, sofern noch nicht voll
            if battery_capacity < BESS_CAPACITY_KWH:
                charging = True
                battery_capacity = min(battery_capacity + CHARGE_RATE_KWH_PER_SEC, BESS_CAPACITY_KWH)
            else:
                charging = False
        else:
            # Teurer Preis: Batterie wird genutzt (entladen), aber nicht unter 10% Kapazität
            if battery_capacity > BESS_MIN_KWH:
                charging = False  # nicht im Lademodus
                battery_capacity = max(battery_capacity - DISCHARGE_RATE_KWH_PER_SEC, BESS_MIN_KWH)
            else:
                charging = False

        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_loop())

@app.get("/get_status", response_model=StatusResponse)
async def get_status():
    return StatusResponse(
        current_price=round(current_price, 2),
        charging="Ein" if charging else "Aus",
        battery_capacity_kwh=round(battery_capacity, 2),
        battery_capacity_percent=round((battery_capacity / BESS_CAPACITY_KWH) * 100, 2)
    )
