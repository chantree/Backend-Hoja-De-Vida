from fastapi import FastAPI
import os
import json
import base64
from openai import OpenAI

app = FastAPI()

BASE_PATH = os.getenv("BASE_PATH", "/home/backend/vehiculos")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ======================================
# PROMPTS
# ======================================

PROMPT_CEDULA = """
Esta imagen es una CÉDULA DE CIUDADANÍA colombiana.

Extrae SOLO estos campos si existen:

{
  "tipo_documento": "",
  "numero": "",
  "nombres": "",
  "apellidos": "",
  "fecha_nacimiento": "",
  "lugar_nacimiento": "",
  "estatura": "",
  "sexo": "",
  "fecha_expedicion": "",
  "grupo_sanguineo": ""
}

Devuelve null si no existe.
NO inventes datos.
Devuelve SOLO JSON válido.
"""

PROMPT_LICENCIA = """
Esta imagen es una LICENCIA DE CONDUCCIÓN colombiana.

Extrae SOLO:

{
  "tipo_documento": "",
  "numero": "",
  "nombres": "",
  "apellidos": "",
  "fecha_nacimiento": "",
  "fecha_expedicion": "",
  "vigencia": "",
  "grupo_sanguineo": "",
  "categoria": ""
}

Devuelve SOLO JSON válido.
"""

PROMPT_TP = """
Esta imagen es una TARJETA DE PROPIEDAD colombiana.

Extrae SOLO:

{
  "tipo_documento": "",
  "placa": "",
  "vin": "",
  "motor": "",
  "chasis": "",
  "marca": "",
  "linea": "",
  "modelo": "",
  "clase": "",
  "tipo_carroceria": "",
  "capacidad_Kg_Psj": "",
  "servicio": "",
  "cilindrada CC": "",
  "combustible": "",
  "color": ""
}

En Colombia VIN = número de chasis.
Devuelve SOLO JSON válido.
"""

# ======================================
# UTILIDADES
# ======================================

def leer_imagen_base64(ruta):
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode()


def analizar_imagen(path, prompt):
    img64 = leer_imagen_base64(path)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=800
    )

    return response.choices[0].message.content


def limpiar_json(texto):
    if not texto:
        return {}

    texto = texto.replace("```json", "")
    texto = texto.replace("```", "")
    texto = texto.strip()

    try:
        return json.loads(texto)
    except:
        return {}

# ======================================
# ENDPOINT
# ======================================

@app.get("/validar/{placa}")
def escanear_placa(placa: str):

    placa = placa.upper().replace(" ", "")

    carpeta_ok = os.path.join(BASE_PATH, f"{placa}_OK")
    carpeta_pendiente = os.path.join(BASE_PATH, f"{placa}_PENDIENTE")

    if os.path.exists(carpeta_ok):
        carpeta = carpeta_ok
    elif os.path.exists(carpeta_pendiente):
        carpeta = carpeta_pendiente
    else:
        return {"error": "Placa no existe"}

    resultados = {}

    # ===================== CEDULA =====================
    ruta_cedula = os.path.join(carpeta, "conductor", "cedula_frontal.jpg")
    if os.path.exists(ruta_cedula):
        raw = analizar_imagen(ruta_cedula, PROMPT_CEDULA)
        resultados["cedula"] = limpiar_json(raw)

    # ===================== LICENCIA =====================
    ruta_licencia = os.path.join(carpeta, "licencia", "frontal.jpg")
    if os.path.exists(ruta_licencia):
        raw = analizar_imagen(ruta_licencia, PROMPT_LICENCIA)
        resultados["licencia"] = limpiar_json(raw)

    # ===================== TARJETA PROPIEDAD =====================
    ruta_tp = os.path.join(carpeta, "vehiculo", "tp_frontal.jpg")
    if os.path.exists(ruta_tp):
        raw = analizar_imagen(ruta_tp, PROMPT_TP)
        resultados["tarjeta_propiedad"] = limpiar_json(raw)

    # Post procesamiento VIN
    tp = resultados.get("tarjeta_propiedad", {})
    if tp:
        vin = tp.get("vin")
        chasis = tp.get("chasis")

        if chasis and len(chasis) == 17:
            tp["vin"] = chasis
            tp["chasis"] = chasis

    with open(os.path.join(carpeta, "ocr_resultados.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    return {
        "status": "OCR generado",
        "placa": placa,
        "resultado": resultados
    }