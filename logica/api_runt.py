from fastapi import FastAPI
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timedelta
import os
import json
import re
import pdfplumber
import requests  

app = FastAPI()

BASE_PATH = os.getenv("BASE_PATH", "/home/backend/vehiculos")


@app.get("/validar/{placa}")
def validar_runt(placa: str):

    placa = placa.upper().replace(" ", "")

    # ================================
    # CARPETAS OK / PENDIENTE
    # ================================
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

    # ================================
    # 🔥 EJECUTAR OCR AUTOMÁTICAMENTE
    # ================================
    if not os.path.exists(ruta_ocr):
        print("OCR no encontrado. Ejecutando OCR primero...")

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

    # ================================
    # CARGAR DATOS
    # ================================
    with open(ruta_datos, "r", encoding="utf-8") as f:
        datos_guardados = json.load(f)

    documento = datos_guardados.get("propietario", {}).get("documento")

    if not documento:
        return {"error": "No hay documento del propietario"}

    with open(ruta_ocr, "r", encoding="utf-8") as f:
        ocr = json.load(f)

    tarjeta = ocr.get("tarjeta_propiedad", {})
    resultado = {}

    # ================================
    # RUNT (NO TOCADO)
    # ================================
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("Abriendo RUNT...")
        page.goto(
            "https://portalpublico.runt.gov.co/#/consulta-vehiculo/consulta/consulta-ciudadana",
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_selector("input", timeout=60000)

        placa_input = page.locator("input").first
        placa_input.fill(placa)
        placa_input.press("Tab")
        page.wait_for_timeout(2000)

        print("Esperando captcha manual...")

        try:
            page.wait_for_selector(
                "text=Información general del vehículo",
                timeout=180000
            )
        except PlaywrightTimeoutError:
            browser.close()
            return {"error": "No se completó captcha"}

        print("Captcha resuelto.")

        # =============================
        # EXTRAER DATOS GENERALES
        # =============================
        datos = {}
        bloques = page.locator("div").all_inner_texts()

        for bloque in bloques:
            lineas = bloque.split("\n")
            lineas = [l.strip() for l in lineas if l.strip()]

            for i in range(len(lineas) - 1):
                clave = lineas[i]
                valor = lineas[i + 1]

                if ":" in clave:
                    datos[clave] = valor

        # =============================
        # RTM – DESCARGAR Y LEER PDF
        # =============================
        print("Abriendo acordeón RTM...")

        acordeon_rtm = page.locator(
            "text=Certificado de revisión técnico mecánica"
        ).first

        rtm_actual = {}
        rtm_lista = []

        if acordeon_rtm.count() > 0:
            acordeon_rtm.click()
            page.wait_for_timeout(2000)

            boton_descarga = page.locator(
                "button[mattooltip='Descargar']"
            ).first

            if boton_descarga.count() > 0:

                with page.expect_download() as download_info:
                    boton_descarga.click()

                download = download_info.value

                ruta_pdf = os.path.join(
                    carpeta,
                    "revision_tecnomecanica.pdf"
                )

                download.save_as(ruta_pdf)

                with pdfplumber.open(ruta_pdf) as pdf:
                    texto = ""
                    for pagina in pdf.pages:
                        contenido = pagina.extract_text()
                        if contenido:
                            texto += contenido + "\n"

                cda = re.search(
                    r"Entidad\s+que\s+expide\s+el\s+certificado:\s*(.*)",
                    texto,
                    re.IGNORECASE
                )

                cert = re.search(
                    r"No\.\s*([0-9]+)",
                    texto,
                    re.IGNORECASE
                )

                exp = re.search(
                    r"Fecha\s*de\s*expedici[oó]n:\s*([0-9/]+)",
                    texto,
                    re.IGNORECASE
                )

                vig = re.search(
                    r"Fecha\s*de\s*vencimiento:\s*([0-9/]+)",
                    texto,
                    re.IGNORECASE
                )

                if cda:
                    rtm_actual["centro_diagnostico"] = cda.group(1).strip()

                if cert:
                    rtm_actual["numero_certificado"] = cert.group(1).strip()

                if exp:
                    rtm_actual["fecha_expedicion"] = exp.group(1)

                if vig:
                    rtm_actual["fecha_vencimiento"] = vig.group(1)

                rtm_lista = [rtm_actual] if rtm_actual else []

        resultado["runt"] = {
            "placa": datos.get("PLACA DEL VEHÍCULO:", ""),
            "marca": datos.get("MARCA:", ""),
            "linea": datos.get("LÍNEA:", ""),
            "modelo": datos.get("MODELO:", ""),
            "color": datos.get("COLOR:", ""),
            "clase": datos.get("CLASE DE VEHÍCULO:", ""),
            "servicio": datos.get("TIPO DE SERVICIO:", ""),
            "combustible": datos.get("TIPO COMBUSTIBLE:", ""),
            "cilindraje": datos.get("CILINDRAJE:", ""),
            "motor": datos.get("NÚMERO DE MOTOR:", ""),
            "chasis": datos.get("NÚMERO DE CHASIS:", ""),
            "vin": datos.get("NÚMERO DE VIN:", ""),
            "carroceria": datos.get("TIPO DE CARROCERÍA:", ""),
            "revision_tecnomecanica": {
                "actual": rtm_actual,
                "historial": rtm_lista
            }
        }

        browser.close()

    # =============================
    # DIFERENCIAS
    # =============================
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

    # =============================
    # GUARDAR RUNT
    # =============================
    ruta_runt = os.path.join(carpeta, "runt_resultado.json")

    with open(ruta_runt, "w", encoding="utf-8") as f:
        json.dump(resultado["runt"], f, ensure_ascii=False, indent=4)

    print("RUNT guardado correctamente")

    return resultado


@app.get("/")
def test():
    return {"runt": "funcionando"}