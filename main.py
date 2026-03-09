from fastapi import FastAPI
from api import app as api_app
from logica.ocr import app as ocr_app
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from logica.api_runt import app as runt_app
from logica.api_sisconmp import app as sisconmp_app
from logica.cola import router as cola_router
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.include_router(cola_router)
BASE_PATH = os.getenv("BASE_PATH", "/home/backend/vehiculos")

# ✅ CORS (MUY IMPORTANTE)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/vehiculos",
    StaticFiles(directory=BASE_PATH),
    name="vehiculos",
)

app.mount("/api", api_app) # Montar API principal
app.mount("/ocr", ocr_app) # Montar API OCR
app.mount("/runt", runt_app)  # Montar API RUNT
app.mount("/sisconmp", sisconmp_app) # Montar API SISCONMP

@app.get("/")
def root():
    return {"status": "Servidor principal funcionando 🚀"}