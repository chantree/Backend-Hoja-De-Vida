import requests
import time

VPS_URL = "http://159.89.44.99:8000/cola"
RUNT_URL = "http://127.0.0.1:8000/runt/validar"

print("Worker iniciado...")

while True:

    try:

        # preguntar al VPS si hay placa en cola
        r = requests.get(VPS_URL, timeout=10)
        data = r.json()

        placa = data.get("placa")

        if placa:

            print("Procesando placa:", placa)

            # llamar al backend local que hace el scraping
            respuesta = requests.get(f"{RUNT_URL}/{placa}", timeout=600)

            print("Respuesta RUNT:", respuesta.json())

        else:

            print("No hay tareas")

    except Exception as e:

        print("Error:", e)

    time.sleep(5)