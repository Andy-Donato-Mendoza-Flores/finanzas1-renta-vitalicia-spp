# Autor: Andy Donato Mendoza Flores
# Código de matrícula: 2024200509B
# Tema 25 del temario: Renta vitalicia frente a retiro programado en el SPP: valuación de una anualidad
# Fecha de extracción: 2026-09-25

"""
03_limpieza_datos.py
Depura los datos crudos del BCRP, la SBS y el Banco Mundial, los une por la
llave común (AFP + periodo mensual) y genera datos_procesados.
Ejecutar desde la carpeta raíz del proyecto:  python codigo/03_limpieza_datos.py
"""

# ---------------------------------------------------------------
# Bloque 1. Librerías
# ---------------------------------------------------------------
import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

# ---------------------------------------------------------------
# Bloque 2. Parámetros (se cambian aquí, no dentro del código)
# ---------------------------------------------------------------
CODIGO = "2024200509B"
ANIO_INICIO = 2010
ANIO_CORTE = 2025

# Habitat inició operaciones en junio de 2013: antes de esa fecha
# sus ceros en las series del BCRP son ausencia estructural, no valores reales.
INICIO_HABITAT = pd.Period("2013-06", freq="M")

# El BCRP solo publica series de las cuatro AFP vigentes. Horizonte, que operó
# hasta ser absorbida, aparece en el valor cuota de la SBS pero no en el BCRP.
AFP_SIN_SERIES_BCRP = ["Horizonte"]

CARPETA_CRUDOS = Path("datos_crudos")
CARPETA_PROC = Path("datos_procesados")
CARPETA_PROC.mkdir(exist_ok=True)
ARCHIVO_LOG = Path("log_ejecucion.txt")

MESES_BCRP = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora de Lima en el log y en pantalla."""
    linea = f"{datetime.now(ZoneInfo('America/Lima')):%Y-%m-%d %H:%M:%S} | {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# ---------------------------------------------------------------
# Bloque 3. BCRP: de formato largo a ancho
# ---------------------------------------------------------------
def convertir_periodo(texto):
    """Convierte 'Ene.2010' en un periodo mensual de pandas."""
    try:
        mes_txt, anio = str(texto).split(".")
        mes = MESES_BCRP[mes_txt.strip().lower()[:3]]
        return pd.Period(year=int(anio), month=mes, freq="M")
    except (ValueError, KeyError):
        return pd.NaT


bcrp = pd.read_csv(CARPETA_CRUDOS / f"datos_crudos_bcrp_{CODIGO}.csv")
bcrp["mes"] = bcrp["periodo"].apply(convertir_periodo)
sin_fecha = bcrp["mes"].isna().sum()
if sin_fecha:
    escribir_log(f"AVISO: {sin_fecha} periodos del BCRP no se pudieron convertir")

# "n.d." significa dato no disponible en la fuente
bcrp["valor"] = pd.to_numeric(bcrp["valor"], errors="coerce")

# La tasa del bono es del mercado, no de una AFP: se separa para unirla solo por mes
tasa = bcrp[bcrp["afp"] == "Mercado"].copy()
bcrp = bcrp[bcrp["afp"] != "Mercado"].copy()

tasa_mensual = (tasa.pivot_table(index="mes", columns="variable",
                                 values="valor", aggfunc="first").reset_index())
tasa_mensual.columns.name = None
escribir_log(f"Tasa de descuento: {tasa_mensual.shape[0]} meses")

# Una fila por AFP y mes, una columna por variable
bcrp_ancho = bcrp.pivot_table(index=["mes", "afp"], columns="variable",
                              values="valor", aggfunc="first").reset_index()
bcrp_ancho.columns.name = None
escribir_log(f"BCRP en formato ancho: {bcrp_ancho.shape[0]} filas, {bcrp_ancho.shape[1]} columnas")

# Ausencia estructural: Habitat antes de junio de 2013
antes_habitat = (bcrp_ancho["afp"] == "Habitat") & (bcrp_ancho["mes"] < INICIO_HABITAT)
columnas_bcrp = [c for c in bcrp_ancho.columns if c not in ("mes", "afp")]
bcrp_ancho.loc[antes_habitat, columnas_bcrp] = np.nan
escribir_log(f"Marcadas como ausencia estructural (Habitat previo a 2013-06): {antes_habitat.sum()} filas")

# ---------------------------------------------------------------
# Bloque 4. SBS: de valor cuota diario a mensual (último día hábil)
# ---------------------------------------------------------------
sbs = pd.read_csv(CARPETA_CRUDOS / f"datos_crudos_sbs_{CODIGO}.csv", parse_dates=["fecha"])
sbs["valor_cuota"] = pd.to_numeric(sbs["valor_cuota"], errors="coerce")
sbs = sbs.dropna(subset=["valor_cuota"])
sbs["mes"] = sbs["fecha"].dt.to_period("M")

# Se toma la observación de la última fecha disponible de cada mes
sbs = sbs.sort_values("fecha")
sbs_mensual = (sbs.groupby(["mes", "afp", "tipo_fondo"], as_index=False)
                  .agg(valor_cuota=("valor_cuota", "last"),
                       dias_habiles=("valor_cuota", "size")))
escribir_log(f"SBS mensual: {sbs_mensual.shape[0]} filas ({sbs_mensual['mes'].nunique()} meses)")

# ---------------------------------------------------------------
# Bloque 5. Unión de las fuentes
# Llave AFP + mes para las series por AFP; solo mes para la tasa de mercado.
# ---------------------------------------------------------------
base = sbs_mensual.merge(bcrp_ancho, on=["mes", "afp"], how="left")
base = base.merge(tasa_mensual, on="mes", how="left")

# Banco Mundial: esperanza de vida anual, se asigna a cada mes del año
bm = pd.read_csv(CARPETA_CRUDOS / f"datos_crudos_bm_{CODIGO}.csv")
bm = bm.rename(columns={"valor": "esperanza_vida"})[["anio", "esperanza_vida"]]
base["anio"] = base["mes"].dt.year
base = base.merge(bm, on="anio", how="left")

# Filtro del periodo declarado
base = base[(base["anio"] >= ANIO_INICIO) & (base["anio"] <= ANIO_CORTE)].copy()
escribir_log(f"Base unida: {base.shape[0]} filas, {base.shape[1]} columnas")

# ---------------------------------------------------------------
# Bloque 6. Imputación de huecos aislados
# Solo se interpolan vacíos rodeados de datos reales, dentro de cada
# serie (AFP y tipo de fondo). Nunca se extiende una serie hacia atrás
# ni se rellenan las AFP que carecen de series en el BCRP.
# ---------------------------------------------------------------
vars_numericas = ["valor_cuota", "valor_fondo_mill_soles", "afiliados_miles",
                  "rentab_real_12m", "rend_bono_10a_soles", "esperanza_vida"]
vars_numericas = [v for v in vars_numericas if v in base.columns]

base = base.sort_values(["afp", "tipo_fondo", "mes"])
faltantes_antes = base[vars_numericas].isna()

base[vars_numericas] = (base.groupby(["afp", "tipo_fondo"])[vars_numericas]
                            .transform(lambda s: s.interpolate(method="linear",
                                                               limit_area="inside")))

# Columna de transparencia: marca las celdas que fueron imputadas
imputadas = faltantes_antes & base[vars_numericas].notna()
base["imputado"] = imputadas.any(axis=1).map({True: "Si", False: "No"})
escribir_log(f"Celdas imputadas por interpolación lineal: {int(imputadas.values.sum())}")
escribir_log(f"Celdas que siguen vacías (ausencia en la fuente): {int(base[vars_numericas].isna().values.sum())}")

# ---------------------------------------------------------------
# Bloque 7. Orden final, guardado y hash de verificación
# ---------------------------------------------------------------
base["mes"] = base["mes"].astype(str)   # formato AAAA-MM, legible en cualquier programa
orden = ["mes", "anio", "afp", "tipo_fondo"] + vars_numericas + ["dias_habiles", "imputado"]
base = base[[c for c in orden if c in base.columns]].reset_index(drop=True)

ruta_final = CARPETA_PROC / f"datos_procesados_{CODIGO}.csv"
base.to_csv(ruta_final, index=False, encoding="utf-8")

hash_sha = hashlib.sha256(ruta_final.read_bytes()).hexdigest()
escribir_log(f"Guardado {ruta_final} con {len(base)} filas y {base.shape[1]} columnas")
escribir_log(f"Periodo: {base['mes'].min()} a {base['mes'].max()}")
escribir_log(f"SHA-256 del archivo procesado: {hash_sha}")

# Cobertura por AFP: deja constancia de qué periodo cubre cada una
print("\n----- Cobertura por AFP -----")
print(base.groupby("afp").agg(filas=("mes", "size"),
                              desde=("mes", "min"),
                              hasta=("mes", "max")).to_string())
print("\n----- Valores faltantes por columna -----")
print(base.isna().sum().to_string())

escribir_log("Fin de 03_limpieza_datos.py")
