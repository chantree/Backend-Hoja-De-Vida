from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import json
import re
import requests
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https://.*\\.vercel\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_PATH = os.getenv("BASE_PATH", "/home/backend/vehiculos")

playwright_lock = threading.Lock()


def extraer_campo(texto, *claves):
    for clave in claves:
        patron = re.search(
            rf"{re.escape(clave)}\s*[:\-]?\s*([^\n]+)",
            texto,
            re.IGNORECASE
        )
        if patron:
            valor = patron.group(1).strip()
            if len(valor) > 0 and not valor.endswith(":"):
                return valor
    return ""


@app.get("/validar/{placa}")
def validar_runt(placa: str):

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
    ruta_ocr = os.path.join(carpeta, "ocr_resultados.json")

    if not os.path.exists(ruta_datos):
        return {"error": "No existe datos.json"}

    if not os.path.exists(ruta_ocr):
        print("OCR no encontrado. Ejecutando OCR...")
        try:
            response = requests.get(
                f"http://127.0.0.1:8000/ocr/validar/{placa}",
                timeout=300
            )
            print("Respuesta OCR:", response.json())
        except Exception as e:
            return {"error": f"Error ejecutando OCR: {str(e)}"}

        if not os.path.exists(ruta_ocr):
            return {"error": "OCR no se generó correctamente"}

    with open(ruta_datos, "r", encoding="utf-8") as f:
        datos_guardados = json.load(f)

    documento = datos_guardados.get("propietario", {}).get("documento")

    if not documento:
        return {"error": "No hay documento del propietario"}

    with open(ruta_ocr, "r", encoding="utf-8") as f:
        ocr = json.load(f)

    tarjeta = ocr.get("tarjeta_propiedad", {})
    resultado = {}
    datos_vehiculo = {}
    rtm_actual = {}
    rtm_lista = []

    with playwright_lock:

        with sync_playwright() as p:

            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]

            if len(context.pages) == 0:
                page = context.new_page()
            else:
                page = context.pages[0]

            try:
                print("===================================")
                print("Abriendo RUNT...")
                print(f"Placa: {placa} | Documento: {documento}")
                print("Resuelve el captcha manualmente.")
                print("===================================")

                page.goto(
                    "https://portalpublico.runt.gov.co/#/consulta-vehiculo/consulta/consulta-ciudadana",
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(5000)
                page.wait_for_selector("input", timeout=60000)

                # Llenar placa
                placa_input = page.locator("input").first
                placa_input.fill(placa)
                placa_input.press("Tab")
                page.wait_for_timeout(1000)

                # Llenar documento del propietario
                try:
                    doc_input = page.locator("input[formcontrolname='documento']").first
                    if doc_input.count() > 0:
                        doc_input.fill(documento)
                        doc_input.press("Tab")
                        page.wait_for_timeout(1000)
                        print(f"Documento llenado: {documento}")
                    else:
                        print("Campo documento no encontrado, esperando captcha...")
                except Exception as e:
                    print(f"No se pudo llenar documento: {e}")

                try:
                    page.wait_for_selector(
                        "text=Información general del vehículo",
                        timeout=1800000
                    )
                except PlaywrightTimeoutError:
                    return {"error": "No se completó captcha"}

                print("Captcha resuelto.")
                page.wait_for_timeout(2000)

                acordeones = [
                    "Información general del vehículo",
                    "Certificado de revisión técnico mecánica y de emisiones contaminantes (RTM)",
                ]

                for texto_acordeon in acordeones:
                    try:
                        elem = page.locator(f"text={texto_acordeon}").first
                        if elem.count() > 0:
                            elem.click()
                            page.wait_for_timeout(2000)
                            print(f"Expandido: {texto_acordeon}")
                    except Exception as e:
                        print(f"No se pudo expandir '{texto_acordeon}': {e}")

                texto_pagina = page.inner_text("body")

                print(f"=== TEXTO PAGINA (primeros 2000 chars) ===")
                for linea in texto_pagina[:2000].split("\n"):
                    if linea.strip():
                        print(linea.strip())

                datos_vehiculo = {
                    "placa": extraer_campo(texto_pagina, "PLACA DEL VEHÍCULO", "PLACA DEL VEHICULO"),
                    "marca": extraer_campo(texto_pagina, "MARCA"),
                    "linea": extraer_campo(texto_pagina, "LÍNEA", "LINEA"),
                    "modelo": extraer_campo(texto_pagina, "MODELO"),
                    "color": extraer_campo(texto_pagina, "COLOR"),
                    "clase": extraer_campo(texto_pagina, "CLASE DE VEHÍCULO", "CLASE DE VEHICULO"),
                    "servicio": extraer_campo(texto_pagina, "TIPO DE SERVICIO"),
                    "combustible": extraer_campo(texto_pagina, "TIPO COMBUSTIBLE", "COMBUSTIBLE"),
                    "cilindraje": extraer_campo(texto_pagina, "CILINDRAJE"),
                    "motor": extraer_campo(texto_pagina, "NÚMERO DE MOTOR", "NUMERO DE MOTOR"),
                    "chasis": extraer_campo(texto_pagina, "NÚMERO DE CHASIS", "NUMERO DE CHASIS"),
                    "vin": extraer_campo(texto_pagina, "NÚMERO DE VIN", "NUMERO DE VIN"),
                    "carroceria": extraer_campo(texto_pagina, "TIPO DE CARROCERÍA", "TIPO DE CARROCERIA"),
                }

                print(f"Datos vehículo extraídos: {datos_vehiculo}")

                # =============================
                # RTM POR POSICION EN TABLA
                # =============================
                print("Extrayendo RTM de la página...")

                lineas_pagina = [l.strip() for l in texto_pagina.split("\n") if l.strip()]
                rtm_actual = {}
                rtm_lista = []

                try:
                    idx = lineas_pagina.index("REVISION TECNICO-MECANICO")
                    rtm_actual = {
                        "fecha_expedicion": lineas_pagina[idx + 1],
                        "fecha_vencimiento": lineas_pagina[idx + 2],
                        "centro_diagnostico": lineas_pagina[idx + 3],
                        "vigente": lineas_pagina[idx + 4],
                        "numero_certificado": lineas_pagina[idx + 5],
                    }
                    rtm_lista = [rtm_actual]
                    print(f"RTM extraído: {rtm_actual}")
                except (ValueError, IndexError) as e:
                    print(f"No se encontró RTM: {e}")

            except Exception as e:
                print(f"Error general Playwright: {e}")

            finally:
                pass

    resultado["runt"] = {
        "placa": datos_vehiculo.get("placa", placa),
        "marca": datos_vehiculo.get("marca", ""),
        "linea": datos_vehiculo.get("linea", ""),
        "modelo": datos_vehiculo.get("modelo", ""),
        "color": datos_vehiculo.get("color", ""),
        "clase": datos_vehiculo.get("clase", ""),
        "servicio": datos_vehiculo.get("servicio", ""),
        "combustible": datos_vehiculo.get("combustible", ""),
        "cilindraje": datos_vehiculo.get("cilindraje", ""),
        "motor": datos_vehiculo.get("motor", ""),
        "chasis": datos_vehiculo.get("chasis", ""),
        "vin": datos_vehiculo.get("vin", ""),
        "carroceria": datos_vehiculo.get("carroceria", ""),
        "revision_tecnomecanica": {
            "actual": rtm_actual,
            "historial": rtm_lista
        }
    }

    diferencias_rojas = []
    diferencias_amarillas = []

    if tarjeta.get("clase", "").upper() != resultado["runt"]["clase"].upper():
        diferencias_rojas.append("Clase no coincide")

    if tarjeta.get("servicio", "").upper() != resultado["runt"]["servicio"].upper():
        diferencias_rojas.append("Servicio no coincide")

    if tarjeta.get("vin", "").upper() != resultado["runt"]["vin"].upper():
        diferencias_amarillas.append("VIN no coincide")

    if tarjeta.get("motor", "").upper() != resultado["runt"]["motor"].upper():
        diferencias_amarillas.append("Motor no coincide")

    if tarjeta.get("tipo_carroceria", "").upper() != resultado["runt"]["carroceria"].upper():
        diferencias_rojas.append("Carrocería no coincide")

    resultado["alerta"] = len(diferencias_rojas) > 0
    resultado["diferencias_rojas"] = diferencias_rojas
    resultado["diferencias_amarillas"] = diferencias_amarillas

    ruta_runt = os.path.join(carpeta, "runt_resultado.json")

    with open(ruta_runt, "w", encoding="utf-8") as f:
        json.dump(resultado["runt"], f, ensure_ascii=False, indent=4)

    print("RUNT guardado correctamente")

    return resultado


@app.get("/")
def test():
    return {"runt": "funcionando"}
