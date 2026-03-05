import requests
import time
from logica.api_runt import consultar_runt

VPS_URL = "http://159.89.44.99:8000/cola"

print("Worker iniciado...")

while True:
    try:
        r = requests.get(VPS_URL)
        data = r.json()

        placa = data.get("placa")

        if placa:
            print("Procesando placa:", placa)

            consultar_runt(placa)

        else:
            print("No hay tareas")

    except Exception as e:
        print("Error:", e)

    time.sleep(5)