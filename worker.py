import requests
import time

VPS_URL = "http://127.0.0.1:8000/api/cola"
RUNT_URL = "http://127.0.0.1:8000/runt/validar"

print("Worker iniciado...")

while True:
    try:
        r = requests.get(VPS_URL, timeout=10)
        data = r.json()
        placa = data.get("placa")
        if placa:
            print("Procesando placa:", placa)
            respuesta = requests.get(f"{RUNT_URL}/{placa}", timeout=1800)
            print("Respuesta RUNT:", respuesta.json())
        else:
            print("No hay tareas")
    except Exception as e:
        print("Error:", e)
    time.sleep(5)
