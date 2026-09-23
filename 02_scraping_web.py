# Autor: Andy Donato Mendoza Flores
# Código de matrícula: 2024200509B
# Tema 25 del temario: Renta vitalicia frente a retiro programado en el SPP: valuación de una anualidad
# Fecha de extracción: 2026-09-23

"""
02_scraping_web.py — Descarga programática de la SBS.
Rastrea el índice del Boletín Estadístico de AFP, construye las URLs mensuales
del reporte FP-1359 (Valor Cuota por AFP y Tipo de Fondo), descarga cada archivo
XLS, lo guarda intacto y lo parsea con código.
Ejecutar desde la carpeta raíz del proyecto:  python codigo/02_scraping_web.py
"""

# ---------------------------------------------------------------
# Bloque 1. Librerías
# ---------------------------------------------------------------
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# ---------------------------------------------------------------
# Bloque 2. Parámetros congelados
# ---------------------------------------------------------------
CODIGO = "2024200509B"
ANIO_INICIO = 2015  # la SBS no publica el reporte FP-1359 antes de abril de 2015
ANIO_CORTE = 2025
REPORTE = "FP-1359"  # Valor Cuota por AFP y Tipo de Fondo

# Nombre de carpeta y abreviatura que usa la SBS para cada mes.
# Ojo: la SBS escribe "Setiembre" y la abrevia "se".
MESES = {
    1: ("Enero", "en"), 2: ("Febrero", "fe"), 3: ("Marzo", "ma"),
    4: ("Abril", "ab"), 5: ("Mayo", "my"), 6: ("Junio", "jn"),
    7: ("Julio", "jl"), 8: ("Agosto", "ag"), 9: ("Setiembre", "se"),
    10: ("Octubre", "oc"), 11: ("Noviembre", "no"), 12: ("Diciembre", "di"),
}

BASE = "https://intranet2.sbs.gob.pe/estadistica/financiera"
HEADERS = {"User-Agent": "Proyecto academico Finanzas I UNCP - e_2024200509B@uncp.edu.pe"}
PAUSA_SEG = 1.5  # pausa mínima entre solicitudes (numeral 2.4.8)

CARPETA_CRUDOS = Path("datos_crudos")
CARPETA_XLS = CARPETA_CRUDOS / "sbs_xls"   # archivos originales, sin editar
CARPETA_XLS.mkdir(parents=True, exist_ok=True)
ARCHIVO_LOG = Path("log_ejecucion.txt")


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora de Lima en el log y en pantalla."""
    linea = f"{datetime.now(ZoneInfo('America/Lima')):%Y-%m-%d %H:%M:%S} | {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# ---------------------------------------------------------------
# Bloque 3. Descarga de un archivo mensual
# ---------------------------------------------------------------
def descargar_mes(anio, mes):
    """Descarga el XLS de un mes y devuelve la ruta local, o None si no existe."""
    carpeta_mes, abrev = MESES[mes]
    url = f"{BASE}/{anio}/{carpeta_mes}/{REPORTE}-{abrev}{anio}.XLS"
    destino = CARPETA_XLS / f"{REPORTE}-{abrev}{anio}.XLS"

    if destino.exists():  # evita volver a pedir lo ya descargado
        return destino
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
    except requests.RequestException as e:
        escribir_log(f"SBS ERROR de conexión: {e} | {url}")
        return None

    if r.status_code != 200 or len(r.content) < 5000:
        escribir_log(f"SBS HTTP {r.status_code} | {len(r.content)} bytes | no disponible | {url}")
        return None

    destino.write_bytes(r.content)
    escribir_log(f"SBS HTTP {r.status_code} | {len(r.content)} bytes | {url}")
    return destino


# ---------------------------------------------------------------
# Bloque 4. Parseo de un archivo
# Cada hoja diaria es un tipo de fondo. El encabezado real es la fila "Día".
# Ojo: después del encabezado puede venir una fila en blanco.
# ---------------------------------------------------------------
def parsear_archivo(ruta):
    """Devuelve una lista de filas en formato largo: fecha, fondo, AFP, valor cuota."""
    registros = []
    try:
        libro = pd.ExcelFile(ruta, engine="xlrd")
    except Exception as e:
        escribir_log(f"ERROR al abrir {ruta.name}: {e}")
        return registros

    for hoja in libro.sheet_names:
        # Solo interesan las hojas diarias; se omite la hoja "VC-Promedio"
        if not hoja.strip().lower().startswith("vc-diario"):
            continue
        # El tipo de fondo es el último carácter del nombre de la hoja (VC-Diario-Fondo2)
        tipo_fondo = hoja.strip()[-1]
        crudo = pd.read_excel(ruta, sheet_name=hoja, header=None, engine="xlrd")

        # Se busca la fila de encabezado
        fila_enc = None
        for i in range(len(crudo)):
            if str(crudo.iloc[i, 0]).strip().lower() == "día":
                fila_enc = i
                break
        if fila_enc is None:
            escribir_log(f"AVISO: sin fila 'Día' en {ruta.name} hoja {hoja}")
            continue

        # Nombres de AFP, quitando las notas al pie del tipo "Habitat 2/"
        afps = [str(x).split(" ")[0].strip() for x in crudo.iloc[fila_enc, 1:]]

        for i in range(fila_enc + 1, len(crudo)):
            fecha = pd.to_datetime(crudo.iloc[i, 0], errors="coerce")
            if pd.isna(fecha):  # fila en blanco o nota al pie: se salta y sigue
                continue
            for j, afp in enumerate(afps, start=1):
                if afp in ("nan", ""):
                    continue
                registros.append({
                    "fecha": fecha.date(),
                    "tipo_fondo": tipo_fondo,
                    "afp": afp,
                    "valor_cuota": crudo.iloc[i, j],
                    "archivo_origen": ruta.name,
                })
    return registros


# ---------------------------------------------------------------
# Bloque 5. Recorrido de todos los meses del periodo
# ---------------------------------------------------------------
todo = []
descargados = 0
for anio in range(ANIO_INICIO, ANIO_CORTE + 1):
    for mes in range(1, 13):
        ruta = descargar_mes(anio, mes)
        time.sleep(PAUSA_SEG)
        if ruta is None:
            continue
        descargados += 1
        todo.extend(parsear_archivo(ruta))

escribir_log(f"Archivos disponibles y descargados: {descargados}")

datos = pd.DataFrame(todo)
if not datos.empty:
    ruta_csv = CARPETA_CRUDOS / f"datos_crudos_sbs_{CODIGO}.csv"
    datos.to_csv(ruta_csv, index=False, encoding="utf-8")
    escribir_log(f"Guardado {ruta_csv} con {len(datos)} filas")
    escribir_log(f"Rango de fechas: {datos['fecha'].min()} a {datos['fecha'].max()}")
else:
    escribir_log("No se obtuvo ninguna fila de la SBS")

escribir_log("Fin de 02_scraping_web.py")
