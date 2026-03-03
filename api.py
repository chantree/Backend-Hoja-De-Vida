from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
import requests
import base64
from fastapi.responses import FileResponse
from docx import Document
from docx.shared import Inches
from datetime import datetime  # 🔥 NUEVO

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MODELOS
# =========================

class Referencia(BaseModel):
    nombre: str
    telefono: str
    parentesco: str

class Propietario(BaseModel):
    nombre: str
    documento: str
    telefono: str
    correo: str

class Conductor(BaseModel):
    placa: str
    nombres: str
    apellidos: str
    documento: str
    celular: str
    correo: str

    foto_selfie: str
    cedula_frontal: str
    cedula_trasera: str
    licencia_frontal: str
    licencia_trasera: str
    tarjeta_propiedad_frontal: str
    tarjeta_propiedad_trasera: str
    vehiculo_frontal: str
    vehiculo_trasero: str

    propietario: Propietario
    referencias: List[Referencia]

# =========================
# CONFIG
# =========================

BASE_PATH = os.getenv("BASE_PATH", "vehiculos")

# =========================
# FUNCION GUARDAR IMAGEN
# =========================

def guardar_imagen(data, ruta):

    if not data:
        return

    if data.startswith("http"):
        try:
            r = requests.get(data)
            r.raise_for_status()
            with open(ruta, "wb") as f:
                f.write(r.content)
            return
        except:
            return

    try:
        if "," in data:
            data = data.split(",")[1]

        faltante = len(data) % 4
        if faltante:
            data += "=" * (4 - faltante)

        img_bytes = base64.b64decode(data)

        with open(ruta, "wb") as f:
            f.write(img_bytes)

    except:
        return

# =========================
# ROOT
# =========================

@app.get("/")
def root():
    return {"status": "API Transporte Nueva Colombia activa"}

# =========================
# CREAR HOJA VIDA
# =========================

@app.post("/hoja-vida")
def registrar_hoja_vida(data: Conductor):

    placa = data.placa.upper().replace(" ", "")
    carpeta_base = os.path.join(BASE_PATH, f"{placa}_PENDIENTE")

    os.makedirs(carpeta_base, exist_ok=True)
    os.makedirs(os.path.join(carpeta_base, "conductor"), exist_ok=True)
    os.makedirs(os.path.join(carpeta_base, "licencia"), exist_ok=True)
    os.makedirs(os.path.join(carpeta_base, "vehiculo"), exist_ok=True)
    os.makedirs(os.path.join(carpeta_base, "propietario"), exist_ok=True)

    # Guardar JSON
    with open(os.path.join(carpeta_base, "datos.json"), "w", encoding="utf-8") as f:
        json.dump(data.dict(), f, indent=4, ensure_ascii=False)

    # 🔥 Crear estado inicial
    estado_inicial = {
        "word_generado": False,
        "fecha_generacion": None
    }

    with open(os.path.join(carpeta_base, "estado.json"), "w", encoding="utf-8") as f:
        json.dump(estado_inicial, f, indent=4)

    # Guardar imágenes
    guardar_imagen(data.foto_selfie, os.path.join(carpeta_base,"conductor","selfie.jpg"))
    guardar_imagen(data.cedula_frontal, os.path.join(carpeta_base,"conductor","cedula_frontal.jpg"))
    guardar_imagen(data.cedula_trasera, os.path.join(carpeta_base,"conductor","cedula_trasera.jpg"))
    guardar_imagen(data.licencia_frontal, os.path.join(carpeta_base,"licencia","frontal.jpg"))
    guardar_imagen(data.licencia_trasera, os.path.join(carpeta_base,"licencia","trasera.jpg"))
    guardar_imagen(data.tarjeta_propiedad_frontal, os.path.join(carpeta_base,"vehiculo","tp_frontal.jpg"))
    guardar_imagen(data.tarjeta_propiedad_trasera, os.path.join(carpeta_base,"vehiculo","tp_trasera.jpg"))
    guardar_imagen(data.vehiculo_frontal, os.path.join(carpeta_base,"vehiculo","foto_frontal.jpg"))
    guardar_imagen(data.vehiculo_trasero, os.path.join(carpeta_base,"vehiculo","foto_trasero.jpg"))

    return {
        "status": "ok",
        "placa": placa,
        "carpeta": carpeta_base
    }

# =========================
# OBTENER FICHA
# =========================

@app.get("/ficha/{placa}")
def obtener_ficha(placa: str):

    placa = placa.upper().replace(" ", "")

    carpeta_pendiente = os.path.join(BASE_PATH, f"{placa}_PENDIENTE")
    carpeta_ok = os.path.join(BASE_PATH, f"{placa}_OK")

    if os.path.exists(carpeta_ok):
        carpeta = carpeta_ok
    elif os.path.exists(carpeta_pendiente):
        carpeta = carpeta_pendiente
    else:
        return {"error": "Placa no encontrada"}

    ruta_datos = os.path.join(carpeta, "datos.json")

    if not os.path.exists(ruta_datos):
        return {"error": "No hay datos registrados"}

    with open(ruta_datos, "r", encoding="utf-8") as f:
        datos = json.load(f)

    # 🔥 Agregamos OCR y RUNT sin cambiar estructura original

    ruta_ocr = os.path.join(carpeta, "ocr_resultados.json")
    if os.path.exists(ruta_ocr):
        with open(ruta_ocr, "r", encoding="utf-8") as f:
            datos["ocr"] = json.load(f)

    ruta_runt = os.path.join(carpeta, "runt_resultado.json")
    if os.path.exists(ruta_runt):
        with open(ruta_runt, "r", encoding="utf-8") as f:
            datos["runt"] = json.load(f)

    ruta_estado = os.path.join(carpeta, "estado.json")
    if os.path.exists(ruta_estado):
        with open(ruta_estado, "r", encoding="utf-8") as f:
            datos["estado"] = json.load(f)

    return datos

# =========================
# GENERAR WORD
# =========================

@app.get("/generar-word/{placa}")
def generar_word(placa: str):

    placa = placa.upper().replace(" ", "")

    carpeta_pendiente = os.path.join(BASE_PATH, f"{placa}_PENDIENTE")
    carpeta_ok = os.path.join(BASE_PATH, f"{placa}_OK")

    if os.path.exists(carpeta_ok):
        carpeta = carpeta_ok
    elif os.path.exists(carpeta_pendiente):
        carpeta = carpeta_pendiente
    else:
        return {"error": "Placa no encontrada"}

    doc = Document()

    imagenes = [
        os.path.join(carpeta, "conductor", "selfie.jpg"),
        os.path.join(carpeta, "conductor", "cedula_frontal.jpg"),
        os.path.join(carpeta, "conductor", "cedula_trasera.jpg"),
        os.path.join(carpeta, "licencia", "frontal.jpg"),
        os.path.join(carpeta, "licencia", "trasera.jpg"),
        os.path.join(carpeta, "vehiculo", "tp_frontal.jpg"),
        os.path.join(carpeta, "vehiculo", "tp_trasera.jpg"),
        os.path.join(carpeta, "vehiculo", "foto_frontal.jpg"),
        os.path.join(carpeta, "vehiculo", "foto_trasero.jpg"),
    ]

    imagen_encontrada = False

    for img in imagenes:
        if os.path.exists(img):
            doc.add_picture(img, width=Inches(5))
            doc.add_page_break()
            imagen_encontrada = True

    if not imagen_encontrada:
        return {"error": "No hay imágenes para esta placa"}

    ruta_word = os.path.join(carpeta, f"Hoja_Vida_{placa}.docx")
    doc.save(ruta_word)

    # 🔥 Actualizar estado
    estado = {
        "word_generado": True,
        "fecha_generacion": datetime.now().isoformat()
    }

    with open(os.path.join(carpeta, "estado.json"), "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4)

    # 🔥 Renombrar carpeta si estaba pendiente
    if os.path.exists(carpeta_pendiente):
        os.rename(carpeta_pendiente, carpeta_ok)
        carpeta = carpeta_ok

    return FileResponse(
        os.path.join(carpeta, f"Hoja_Vida_{placa}.docx"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Hoja_Vida_{placa}.docx"
    )