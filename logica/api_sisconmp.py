from fastapi import FastAPI
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import json
import re

app = FastAPI()

BASE_PATH = r"C:\Users\chant\Desktop\vehiculos"


@app.get("/validar/{placa}")
def validar_sisconmp(placa: str):

    placa = placa.upper().replace(" ", "")

    carpeta_ok = os.path.join(BASE_PATH, f"{placa}_OK")
    carpeta_pendiente = os.path.join(BASE_PATH, f"{placa}_PENDIENTE")

    if os.path.exists(carpeta_ok):
        carpeta = carpeta_ok
    elif os.path.exists(carpeta_pendiente):
        carpeta = carpeta_pendiente
    else:
        return {"error": "No existe hoja de vida"}

    ruta_datos = os.path.join(carpeta, "datos.json")

    if not os.path.exists(ruta_datos):
        return {"error": "No existe datos.json"}

    with open(ruta_datos, "r", encoding="utf-8") as f:
        datos = json.load(f)

    documento = datos.get("documento") or datos.get("conductor", {}).get("documento")

    if not documento:
        return {"error": "No hay documento del conductor"}

    resultado = {
        "documento": documento,
        "entidad": "",
        "fecha_expedicion": "",
        "fecha_vencimiento": "",
        "curso": ""
    }

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Abriendo SISCONMP...")

        page.goto(
            "https://web.mintransporte.gov.co/sisconmp2/consultascapacitaciones/",
            timeout=60000
        )

        page.wait_for_selector("#txtNDI", timeout=60000)

        # Seleccionar tipo CC
        page.select_option("select", "CC")

        # Escribir documento
        page.fill("#txtNDI", documento)

        # Click consultar
        page.click("button:has-text('Consultar')")

        try:
            page.wait_for_selector("div.panel-info", timeout=60000)
        except PlaywrightTimeoutError:
            browser.close()
            return {"error": "No se encontraron resultados"}

        contenido = page.inner_text("div.panel-info")

        entidad = re.search(r"Razón Social Institución Educativa:\s*(.*)", contenido)
        exp = re.search(r"Fecha de Expedición:\s*(.*)", contenido)
        ven = re.search(r"Fecha de Vencimiento:\s*(.*)", contenido)
        curso = re.search(r"Curso Básico:\s*(.*)", contenido)

        if entidad:
            resultado["entidad"] = entidad.group(1).strip()

        if exp:
            resultado["fecha_expedicion"] = exp.group(1).strip()

        if ven:
            resultado["fecha_vencimiento"] = ven.group(1).strip()

        if curso:
            resultado["curso"] = curso.group(1).strip()

        browser.close()

    # ============================
    # GUARDAR RESULTADO
    # ============================

    ruta_guardado = os.path.join(carpeta, "sisconmp_resultado.json")

    with open(ruta_guardado, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=4)

    print("SISCONMP guardado correctamente")

    return resultado


@app.get("/")
def test():
    return {"sisconmp": "funcionando"}