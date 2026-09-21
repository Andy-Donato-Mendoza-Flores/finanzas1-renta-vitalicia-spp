# Autor: Andy Donato Mendoza Flores
# Código de matrícula: 2024200509B
# Tema 25 del temario: Renta vitalicia frente a retiro programado en el SPP: valuación de una anualidad
# Fecha de extracción: 2026-09-20

"""
01_extraccion_api.py
Descarga por API las series del Sistema Privado de Pensiones (BCRPData)
y la esperanza de vida del Perú (Banco Mundial). Guarda los datos crudos
tal como llegan y registra cada consulta en log_ejecucion.txt.
Ejecutar desde la carpeta raíz del proyecto:  python codigo/01_extraccion_api.py
"""

# ---------------------------------------------------------------
# Bloque 1. Librerías
# ---------------------------------------------------------------
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------
# Bloque 2. Parámetros congelados (numeral 2.4.5 de la consigna)
# ---------------------------------------------------------------
FECHA_INICIO = "2010-1"   # enero de 2010 (formato año-mes del BCRP)
FECHA_CORTE = "2025-12"   # diciembre de 2025
CODIGO = "2024200509B"

# Series mensuales del BCRP (fuente original: SBS), una por AFP
SERIES_BCRP = {
    "PN01168MM": ("Habitat", "valor_fondo_mill_soles"),
    "PN01169MM": ("Integra", "valor_fondo_mill_soles"),
    "PN01170MM": ("Prima", "valor_fondo_mill_soles"),
    "PN01171MM": ("Profuturo", "valor_fondo_mill_soles"),
    "PN01174MM": ("Habitat", "afiliados_miles"),
    "PN01175MM": ("Integra", "afiliados_miles"),
    "PN01176MM": ("Prima", "afiliados_miles"),
    "PN01177MM": ("Profuturo", "afiliados_miles"),
    "PN01179MM": ("Habitat", "rentab_real_12m"),
    "PN01180MM": ("Integra", "rentab_real_12m"),
    "PN01181MM": ("Prima", "rentab_real_12m"),
    "PN01182MM": ("Profuturo", "rentab_real_12m"),
}

# Indicador del Banco Mundial: esperanza de vida al nacer, total (años)
INDICADOR_BM = "SP.DYN.LE00.IN"
ANIO_INICIO_BM = 2010
ANIO_CORTE_BM = 2025

# Encabezado identificable y pausa entre solicitudes (numeral 2.4.8)
HEADERS = {"User-Agent": "Proyecto academico Finanzas I UNCP - e_2024200509B@uncp.edu.pe"}
PAUSA_SEG = 1.5

# ---------------------------------------------------------------
# Bloque 3. Rutas relativas y log
# ---------------------------------------------------------------
CARPETA_CRUDOS = Path("datos_crudos")
CARPETA_CRUDOS.mkdir(exist_ok=True)
ARCHIVO_LOG = Path("log_ejecucion.txt")


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora en el log y la muestra en pantalla."""
    linea = f"{datetime.now(ZoneInfo('America/Lima')):%Y-%m-%d %H:%M:%S} | {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# ---------------------------------------------------------------
# Bloque 4. Extracción del BCRP (máximo 10 códigos por consulta)
# ---------------------------------------------------------------
def descargar_bcrp(codigos):
    url = (
        "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/"
        f"{'-'.join(codigos)}/json/{FECHA_INICIO}/{FECHA_CORTE}/esp"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
    except requests.RequestException as e:
        escribir_log(f"BCRP ERROR de conexión: {e}")
        return None
    if r.status_code != 200:
        escribir_log(f"BCRP HTTP {r.status_code} | {url}")
        return None
    datos = r.json()
    escribir_log(f"BCRP HTTP {r.status_code} | {len(datos.get('periods', []))} periodos | {url}")
    return datos


codigos = list(SERIES_BCRP.keys())
grupos = [codigos[i:i + 10] for i in range(0, len(codigos), 10)]

filas = []
for grupo in grupos:
    datos = descargar_bcrp(grupo)
    time.sleep(PAUSA_SEG)
    if datos is None:
        continue
    for periodo in datos["periods"]:
        for codigo, valor in zip(grupo, periodo["values"]):
            afp, variable = SERIES_BCRP[codigo]
            filas.append({
                "periodo": periodo["name"],
                "codigo_serie": codigo,
                "afp": afp,
                "variable": variable,
                "valor": valor,
            })

crudo_bcrp = pd.DataFrame(filas)
ruta_bcrp = CARPETA_CRUDOS / f"datos_crudos_bcrp_{CODIGO}.csv"
crudo_bcrp.to_csv(ruta_bcrp, index=False, encoding="utf-8")
escribir_log(f"Guardado {ruta_bcrp} con {len(crudo_bcrp)} filas")

# ---------------------------------------------------------------
# Bloque 5. Extracción del Banco Mundial (con reintentos)
# Esta API a veces tarda en responder, por eso se intenta
# hasta 3 veces, esperando 10 segundos entre cada intento.
# ---------------------------------------------------------------
url_bm = (
    f"https://api.worldbank.org/v2/country/PER/indicator/{INDICADOR_BM}"
    f"?format=json&date={ANIO_INICIO_BM}:{ANIO_CORTE_BM}&per_page=100"
)
respuesta = None
for intento in range(1, 4):
    try:
        r = requests.get(url_bm, headers=HEADERS, timeout=120)
        escribir_log(f"Banco Mundial intento {intento} HTTP {r.status_code} | {url_bm}")
        r.raise_for_status()
        respuesta = r.json()
        break  # si funcionó, sale del ciclo
    except (requests.RequestException, ValueError) as e:
        escribir_log(f"Banco Mundial intento {intento} ERROR: {e}")
        time.sleep(10)

if respuesta is not None:
    # Se guarda el JSON original como evidencia primaria
    with open(CARPETA_CRUDOS / f"datos_crudos_bm_{CODIGO}.json", "w", encoding="utf-8") as f:
        json.dump(respuesta, f, ensure_ascii=False, indent=2)
    registros = respuesta[1] if len(respuesta) > 1 and respuesta[1] else []
    crudo_bm = pd.DataFrame([
        {"anio": reg["date"], "indicador": reg["indicator"]["id"], "valor": reg["value"]}
        for reg in registros
    ])
    ruta_bm = CARPETA_CRUDOS / f"datos_crudos_bm_{CODIGO}.csv"
    crudo_bm.to_csv(ruta_bm, index=False, encoding="utf-8")
    escribir_log(f"Guardado {ruta_bm} con {len(crudo_bm)} filas")
else:
    escribir_log("Banco Mundial: no se pudo descargar tras 3 intentos")

escribir_log("Fin de 01_extraccion_api.py")
