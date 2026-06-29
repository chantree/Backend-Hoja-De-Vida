from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json
import os
import uuid
from bs4 import BeautifulSoup

router = APIRouter()

RECKITT_FILE = "/home/backend/gestion/reckitt.json"
FATECO_FILE = "/home/backend/gestion/fateco.json"

os.makedirs("/home/backend/gestion", exist_ok=True)

def leer(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class ReckittRecord(BaseModel):
    id: Optional[str] = None
    placa: str
    novedad: str = ""
    correo: str = ""
    papeles: str = ""
    fechaEntrega: Optional[str] = None
    enRuta: bool = False
    otros: str = ""
    telefono: str = ""        
    guiaEnviada: bool = False 

class FatecoRecord(BaseModel):
    id: Optional[str] = None
    rtTotal: str
    titRmTi: str = ""
    placa: str = ""
    novedad: str = ""
    correo: str = ""
    papeles: str = ""
    fechaEntrega: Optional[str] = None
    enRuta: bool = False
    otros: str = ""

@router.get("/reckitt")
def get_reckitt():
    return leer(RECKITT_FILE)

@router.post("/reckitt")
def add_reckitt(rec: ReckittRecord):
    data = leer(RECKITT_FILE)
    rec.id = str(uuid.uuid4())
    data.append(rec.dict())
    guardar(RECKITT_FILE, data)
    return rec

@router.put("/reckitt/{id}")
def update_reckitt(id: str, rec: ReckittRecord):
    data = leer(RECKITT_FILE)
    data = [r if r["id"] != id else {**rec.dict(), "id": id} for r in data]
    guardar(RECKITT_FILE, data)
    return rec

@router.delete("/reckitt/{id}")
def delete_reckitt(id: str):
    data = leer(RECKITT_FILE)
    data = [r for r in data if r["id"] != id]
    guardar(RECKITT_FILE, data)
    return {"ok": True}

@router.get("/fateco")
def get_fateco():
    return leer(FATECO_FILE)

@router.post("/fateco")
def add_fateco(rec: FatecoRecord):
    data = leer(FATECO_FILE)
    rec.id = str(uuid.uuid4())
    data.append(rec.dict())
    guardar(FATECO_FILE, data)
    return rec

@router.put("/fateco/{id}")
def update_fateco(id: str, rec: FatecoRecord):
    data = leer(FATECO_FILE)
    data = [r if r["id"] != id else {**rec.dict(), "id": id} for r in data]
    guardar(FATECO_FILE, data)
    return rec

@router.delete("/fateco/{id}")
def delete_fateco(id: str):
    data = leer(FATECO_FILE)
    data = [r for r in data if r["id"] != id]
    guardar(FATECO_FILE, data)
    return {"ok": True}

PLANTILLAS_FILE = "/home/backend/gestion/plantillas.json"

PLANTILLAS_DEFAULT = [
    "Prueba mensaje aviso 1",
    "Prueba mensaje aviso 2", 
    "Prueba mensaje aviso 3",
]

@router.get("/plantillas")
def get_plantillas():
    if not os.path.exists(PLANTILLAS_FILE):
        return PLANTILLAS_DEFAULT
    with open(PLANTILLAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/plantillas")
def save_plantillas(data: list[str]):
    with open(PLANTILLAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

import httpx


from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import threading

guia_lock = threading.Lock()

@router.get("/guia/{numero}")
def consultar_guia(numero: str):
    try:
        with guia_lock:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0]
                page = context.new_page()
                try:
                    page.goto(
                        f"https://www.servientrega.com/wps/portal/rastreo-envio",
                        wait_until="domcontentloaded",
                        timeout=30000
                    )
                    page.wait_for_timeout(2000)
                    
                    # Llenar número de guía
                    page.fill("input[type='text']", numero)
                    page.click("button[type='submit'], .btn-consultar, button:has-text('Consultar')")
                    page.wait_for_timeout(4000)
                    
                    texto = page.inner_text("body")
                    
                    estado = "No encontrado"
                    for keyword in ["ENTREGADO", "EN RUTA", "RECIBIDO", "EN DISTRIBUCIÓN", "DEVUELTO"]:
                        if keyword in texto.upper():
                            estado = keyword
                            break
                    
                    return {"estado": estado, "guia": numero}
                finally:
                    page.close()
    except Exception as e:
        return {"estado": "Error", "guia": numero, "error": str(e)}