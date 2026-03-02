import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="TransporteNuevaColombiaHV",
        user="postgres",
        password="posgres123",
        port=5432
    )
