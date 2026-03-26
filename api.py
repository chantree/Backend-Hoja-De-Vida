from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from docx import Document
from docx.shared import Inches
from datetime import datetime

import os
import json
import requests
import base64

app = FastAPI()

# =========================
# CORS (CORREGIDO)
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# CONFIG
# =========================

BASE_PATH = os.getenv("BASE_PATH", "/home/backend/vehiculos")

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
    direccion: str


class Conductor(BaseModel):
    placa: str
    nombres: str
    apellidos: str
    documento: str
    celular: str
    correo: str
    direccion: str

    foto_selfie: Optional[str] = None
    cedula_frontal: Optional[str] = None
    cedula_trasera: Optional[str] = None
    licencia_frontal: Optional[str] = None
    licencia_trasera: Optional[str] = None
    tarjeta_propiedad_frontal: Optional[str] = None
    tarjeta_propiedad_trasera: Optional[str] = None
    vehiculo_frontal: Optional[str] = None
    vehiculo_trasero: Optional[str] = None

    propietario: Propietario
    referencias: List[Referencia]


# =========================
# ROOT
# =========================

@app.get("/")
def root():
    return {"status": "API Transporte Nueva Colombia activa"}


# =========================
# UPLOAD
# =========================

@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    os.makedirs(BASE_PATH, exist_ok=True)

    file_path = os.path.join(BASE_PATH, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {
        "status": "ok",
        "archivo": file.filename
    }


# =========================
# GUARDAR IMAGEN
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
# REGISTRAR HOJA VIDA
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

    with open(os.path.join(carpeta_base, "datos.json"), "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, indent=4, ensure_ascii=False)

    estado_inicial = {
        "word_generado": False,
        "fecha_generacion": None
    }

    with open(os.path.join(carpeta_base, "estado.json"), "w", encoding="utf-8") as f:
        json.dump(estado_inicial, f, indent=4)

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
            estado = json.load(f)
            datos["word_generado"] = estado.get("word_generado", False)

    return datos


# =========================
# GENERAR WORD
# =========================

@app.get("/generar-word/{placa}")
def generar_word(placa: str):

    placa = placa.upper().replace(" ", "")

    carpeta_ok = os.path.join(BASE_PATH, f"{placa}_OK")
    carpeta_pendiente = os.path.join(BASE_PATH, f"{placa}_PENDIENTE")

    if os.path.exists(carpeta_ok):
        carpeta = carpeta_ok
    elif os.path.exists(carpeta_pendiente):
        carpeta = carpeta_pendiente
    else:
        return {"error": "Placa no encontrada"}

    # Generar Word con las imagenes
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

    for img in imagenes:
        if os.path.exists(img):
            doc.add_picture(img, width=Inches(5))
            doc.add_page_break()

    # Si estaba en PENDIENTE lo guardamos ahi temporalmente
    ruta_word = os.path.join(carpeta, f"Hoja_Vida_{placa}.docx")
    doc.save(ruta_word)

    # Actualizar estado
    ruta_estado = os.path.join(carpeta, "estado.json")
    estado = {
        "word_generado": True,
        "fecha_generacion": datetime.now().isoformat()
    }
    with open(ruta_estado, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4)

    # Renombrar carpeta de PENDIENTE a OK
    if carpeta == carpeta_pendiente:
        os.rename(carpeta_pendiente, carpeta_ok)
        ruta_word = os.path.join(carpeta_ok, f"Hoja_Vida_{placa}.docx")

    return FileResponse(
        ruta_word,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Hoja_Vida_{placa}.docx"
    )
