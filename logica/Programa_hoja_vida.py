import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="TransporteNuevaColombiaHV",
        user="postgres",
        password="posgres123",
        port=5432
    )

def insertar_conductor(data):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    INSERT INTO conductores (
        nombres, apellidos, documento, celular,
        foto_conductor,
        cedula_frontal, cedula_trasera,
        licencia_frontal, licencia_trasera,
        tarjeta_vehiculo
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cur.execute(sql, (
        data["nombres"],
        data["apellidos"],
        data["documento"],
        data["celular"],
        data["foto_conductor"],
        data["cedula_frontal"],
        data["cedula_trasera"],
        data["licencia_frontal"],
        data["licencia_trasera"],
        data["tarjeta_vehiculo"]
    ))

    conn.commit()
    cur.close()
    conn.close()
