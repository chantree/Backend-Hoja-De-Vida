from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

cola = []

class Trabajo(BaseModel):
    placa: str

@router.post("/cola")
def agregar(data: Trabajo):
    cola.append(data.placa)
    return {"estado": "recibido"}

@router.get("/cola")
def obtener():
    if cola:
        return {"placa": cola.pop(0)}
    return {"placa": None}