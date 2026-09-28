# Autor: Andy Donato Mendoza Flores
# Código de matrícula: 2024200509B
# Tema 25 del temario: Renta vitalicia frente a retiro programado en el SPP: valuación de una anualidad
# Fecha de extracción: 2026-09-25

"""
02_scraping_web.py — Descarga programática de la SBS (dos rutas).
La SBS publica el valor cuota diario por AFP y tipo de fondo en dos lugares:
  (a) 2015 en adelante: reporte FP-1359 en archivos XLS sueltos.
  (b) Años anteriores: dentro del Boletín Informativo Mensual (FP-1231),
      un ZIP que contiene el boletín completo en Excel, con las hojas
      VC-Diario-FondoN.
El script descarga ambas rutas, guarda los archivos originales intactos y
parsea las hojas diarias con código.
Ejecutar desde la carpeta raíz del proyecto:  python codigo/02_scraping_web.py
"""

# ---------------------------------------------------------------
# Bloque 1. Librerías
# ---------------------------------------------------------------
import io
import time
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# ---------------------------------------------------------------
# Bloque 2. Parámetros congelados
# ---------------------------------------------------------------
CODIGO = "2024200509B"
ANIO_INICIO = 2010
ANIO_CORTE = 2025
ANIO_CAMBIO_RUTA = 2015  # desde este año se usa el reporte FP-1359 suelto

REPORTE_VC = "FP-1359"     # Valor Cuota por AFP y Tipo de Fondo (2015 en adelante)
REPORTE_BOL = "FP-1231"    # Boletín Informativo Mensual en ZIP (años anteriores)

BASE_FINANCIERA = "https://intranet2.sbs.gob.pe/estadistica/financiera"
BASE_SPP = "https://intranet2.sbs.gob.pe/estadistica/spp"

# Nombre de carpeta y abreviatura que usa la SBS para cada mes.
# Ojo: la SBS escribe "Setiembre" y la abrevia "se".
MESES = {
    1: ("Enero", "en"), 2: ("Febrero", "fe"), 3: ("Marzo", "ma"),
    4: ("Abril", "ab"), 5: ("Mayo", "my"), 6: ("Junio", "jn"),
    7: ("Julio", "jl"), 8: ("Agosto", "ag"), 9: ("Setiembre", "se"),
    10: ("Octubre", "oc"), 11: ("Noviembre", "no"), 12: ("Diciembre", "di"),
}

HEADERS = {"User-Agent": "Proyecto academico Finanzas I UNCP - e_2024200509B@uncp.edu.pe"}
PAUSA_SEG = 1.5  # pausa mínima entre solicitudes (numeral 2.4.8)

CARPETA_CRUDOS = Path("datos_crudos")
CARPETA_XLS = CARPETA_CRUDOS / "sbs_xls"    # archivos FP-1359 originales
CARPETA_ZIP = CARPETA_CRUDOS / "sbs_zip"    # boletines ZIP originales
CARPETA_XLS.mkdir(parents=True, exist_ok=True)
CARPETA_ZIP.mkdir(parents=True, exist_ok=True)
ARCHIVO_LOG = Path("log_ejecucion.txt")


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora de Lima en el log y en pantalla."""
    linea = f"{datetime.now(ZoneInfo('America/Lima')):%Y-%m-%d %H:%M:%S} | {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def descargar(url, destino):
    """Descarga una URL a un archivo local. Devuelve la ruta o None."""
    if destino.exists():  # evita volver a pedir lo ya descargado
        return destino
    try:
        r = requests.get(url, headers=HEADERS, timeout=90)
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
# Bloque 3. Parseo de las hojas diarias
# Se recibe el contenido del Excel en memoria, venga de un XLS suelto
# o de dentro de un ZIP. Cada hoja VC-Diario-FondoN es un tipo de fondo.
# ---------------------------------------------------------------
def parsear_excel(contenido, nombre_origen):
    """Devuelve filas en formato largo: fecha, tipo de fondo, AFP, valor cuota."""
    registros = []

    # Algunos archivos tienen extensión .XLS pero por dentro son xlsx:
    # si falla el motor antiguo (xlrd), se reintenta con el moderno (openpyxl).
    motor, libro = None, None
    for intento_motor in ("xlrd", "openpyxl"):
        try:
            libro = pd.ExcelFile(io.BytesIO(contenido), engine=intento_motor)
            motor = intento_motor
            break
        except Exception:
            continue
    if motor is None:
        escribir_log(f"ERROR al abrir {nombre_origen} con ambos motores")
        return registros

    for hoja in libro.sheet_names:
        # Solo interesan las hojas diarias; se omite "VC-Promedio" y las demás
        if not hoja.strip().lower().startswith("vc-diario"):
            continue
        tipo_fondo = hoja.strip()[-1]  # VC-Diario-Fondo2 -> "2"
        crudo = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja,
                              header=None, engine=motor)

        # Se busca la fila de encabezado (la que dice "Día")
        fila_enc = None
        for i in range(len(crudo)):
            if str(crudo.iloc[i, 0]).strip().lower() == "día":
                fila_enc = i
                break
        if fila_enc is None:
            escribir_log(f"AVISO: sin fila 'Día' en {nombre_origen} hoja {hoja}")
            continue

        # Nombres de AFP leídos del propio encabezado: así el script funciona
        # aunque el mercado cambie (Horizonte en 2010-2013, Habitat desde 2013).
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
                    "archivo_origen": nombre_origen,
                })
    return registros


# ---------------------------------------------------------------
# Bloque 4. Ruta (a): reporte FP-1359 suelto, desde 2015
# ---------------------------------------------------------------
def procesar_fp1359(anio, mes):
    carpeta_mes, abrev = MESES[mes]
    url = f"{BASE_FINANCIERA}/{anio}/{carpeta_mes}/{REPORTE_VC}-{abrev}{anio}.XLS"
    destino = CARPETA_XLS / f"{REPORTE_VC}-{abrev}{anio}.XLS"
    ruta = descargar(url, destino)
    if ruta is None:
        return []
    return parsear_excel(ruta.read_bytes(), ruta.name)


# ---------------------------------------------------------------
# Bloque 5. Ruta (b): Boletín Informativo Mensual en ZIP, años previos
# El ZIP contiene el boletín completo (unas 63 hojas); se toma el Excel
# que trae dentro y se le aplica el mismo parseo.
# ---------------------------------------------------------------
def procesar_boletin(anio, mes):
    carpeta_mes, abrev = MESES[mes]
    url = f"{BASE_SPP}/{anio}/{carpeta_mes}/{REPORTE_BOL}-{abrev}{anio}.ZIP"
    destino = CARPETA_ZIP / f"{REPORTE_BOL}-{abrev}{anio}.ZIP"
    ruta = descargar(url, destino)
    if ruta is None:
        return []

    try:
        z = zipfile.ZipFile(ruta)
    except zipfile.BadZipFile:
        escribir_log(f"ERROR: {ruta.name} no es un ZIP válido")
        return []

    # Se busca el primer Excel dentro del ZIP (su nombre interno varía)
    internos = [n for n in z.namelist() if n.lower().endswith((".xls", ".xlsx"))]
    if not internos:
        escribir_log(f"AVISO: {ruta.name} no contiene ningún Excel")
        return []
    nombre_interno = internos[0]
    return parsear_excel(z.read(nombre_interno), f"{ruta.name}/{nombre_interno}")


# ---------------------------------------------------------------
# Bloque 6. Recorrido de todo el periodo, eligiendo la ruta por año
# ---------------------------------------------------------------
todo = []
for anio in range(ANIO_INICIO, ANIO_CORTE + 1):
    for mes in range(1, 13):
        if anio >= ANIO_CAMBIO_RUTA:
            filas = procesar_fp1359(anio, mes)
        else:
            filas = procesar_boletin(anio, mes)
        time.sleep(PAUSA_SEG)
        todo.extend(filas)

datos = pd.DataFrame(todo)
if not datos.empty:
    ruta_csv = CARPETA_CRUDOS / f"datos_crudos_sbs_{CODIGO}.csv"
    datos.to_csv(ruta_csv, index=False, encoding="utf-8")
    escribir_log(f"Guardado {ruta_csv} con {len(datos)} filas")
    escribir_log(f"Rango de fechas: {datos['fecha'].min()} a {datos['fecha'].max()}")
    escribir_log(f"AFP encontradas: {sorted(datos['afp'].unique())}")
    escribir_log(f"Tipos de fondo: {sorted(datos['tipo_fondo'].unique())}")
else:
    escribir_log("No se obtuvo ninguna fila de la SBS")

escribir_log("Fin de 02_scraping_web.py")
