# Autor: Andy Donato Mendoza Flores
# Código de matrícula: 2024200509B
# Tema 25 del temario: Renta vitalicia frente a retiro programado en el SPP: valuación de una anualidad
# Fecha de extracción: 2026-09-25

"""
04_analisis.py
Valúa la renta vitalicia y el retiro programado como anualidades, compara
ambas modalidades y determina el punto de indiferencia. Todas las tasas se
expresan en términos reales. Genera las tablas y figuras del artículo en /salidas.
Ejecutar desde la carpeta raíz del proyecto:  python codigo/04_analisis.py
"""

# ---------------------------------------------------------------
# Bloque 1. Librerías
# ---------------------------------------------------------------
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")  # backend sin ventana gráfica, para que corra en cualquier máquina
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------
# Bloque 2. Supuestos del caso base (declarados como constantes)
# ---------------------------------------------------------------
CODIGO = "2024200509B"
EDAD_JUBILACION = 65        # edad legal de jubilación en el SPP
SALDO_INICIAL = 100_000     # saldo acumulado de referencia, en soles
PAGOS_POR_ANIO = 12         # pensión mensual
FONDO_ANALISIS = 2          # Fondo tipo 2, el de mayor número de afiliados
HORIZONTE_BASE = 20         # años de pago en el escenario central
HORIZONTES_SENSIBILIDAD = [10, 15, 20, 25]  # análisis de robustez
MES_BASE_INDICE = "2013-06"  # mes común para indexar el valor cuota (entrada de Habitat)
MESES_MINIMOS_FIGURA = 24    # historia mínima para incluir una AFP en la figura indexada

CARPETA_PROC = Path("datos_procesados")
CARPETA_SALIDAS = Path("salidas")
CARPETA_SALIDAS.mkdir(exist_ok=True)
ARCHIVO_LOG = Path("log_ejecucion.txt")


def escribir_log(mensaje):
    """Escribe una línea con fecha y hora de Lima en el log y en pantalla."""
    linea = f"{datetime.now(ZoneInfo('America/Lima')):%Y-%m-%d %H:%M:%S} | {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


# ---------------------------------------------------------------
# Bloque 3. Carga de la base y cálculo de la tasa real
# La rentabilidad del fondo que publica la SBS ya es real (descuenta inflación),
# pero el rendimiento del bono es nominal. Para compararlos se aplica la
# ecuación de Fisher: (1 + nominal) / (1 + inflación) - 1.
# ---------------------------------------------------------------
base = pd.read_csv(CARPETA_PROC / f"datos_procesados_{CODIGO}.csv")
base = base[base["tipo_fondo"] == FONDO_ANALISIS].copy()

base["tasa_bono_real"] = ((1 + base["rend_bono_10a_soles"] / 100) /
                          (1 + base["inflacion_12m"] / 100) - 1) * 100

escribir_log(f"Base cargada: {len(base)} filas del Fondo {FONDO_ANALISIS}")
escribir_log(f"Bono nominal promedio: {base['rend_bono_10a_soles'].mean():.2f} % | "
             f"Inflación promedio: {base['inflacion_12m'].mean():.2f} % | "
             f"Bono real promedio: {base['tasa_bono_real'].mean():.2f} %")

# ---------------------------------------------------------------
# Bloque 4. Funciones financieras
# ---------------------------------------------------------------
def tasa_mensual(tasa_anual_pct):
    """Convierte una tasa anual en porcentaje a su equivalente mensual efectiva."""
    return (1 + tasa_anual_pct / 100) ** (1 / 12) - 1


def factor_anualidad(i, n):
    """Valor presente de recibir 1 unidad al final de cada uno de n periodos:
    a(n,i) = (1 - (1+i)^-n) / i."""
    if abs(i) < 1e-12:
        return float(n)
    return (1 - (1 + i) ** (-n)) / i


def pension_renta_vitalicia(saldo, tasa_anual_pct, anios):
    """Pensión mensual constante que puede pagarse durante 'anios' años,
    dado el saldo y la tasa técnica."""
    i = tasa_mensual(tasa_anual_pct)
    n = int(round(anios * PAGOS_POR_ANIO))
    if n <= 0:
        return np.nan
    return saldo / factor_anualidad(i, n)


def simular_retiro_programado(saldo, tasas_anuales_pct, anios):
    """Simula el retiro programado año por año.
    Cada año se recalcula la pensión con el saldo restante, los meses que faltan
    y la rentabilidad vigente de ese año. 'tasas_anuales_pct' es la secuencia de
    rentabilidades observadas; si se agota, se repite la última.
    Devuelve las pensiones anuales, el flujo mensual y el saldo remanente."""
    saldo_actual = float(saldo)
    n_anios = int(round(anios))
    pensiones, flujo = [], []

    for k in range(n_anios):
        # Rentabilidad de este año: la observada, o la última disponible
        tasa_k = tasas_anuales_pct[k] if k < len(tasas_anuales_pct) else tasas_anuales_pct[-1]
        i = tasa_mensual(tasa_k)
        meses_restantes = (n_anios - k) * PAGOS_POR_ANIO
        if saldo_actual <= 0:
            break
        pension = saldo_actual / factor_anualidad(i, meses_restantes)
        pensiones.append(pension)
        for _ in range(PAGOS_POR_ANIO):
            saldo_actual = saldo_actual * (1 + i) - pension
            flujo.append(pension)
    return pensiones, flujo, max(saldo_actual, 0.0)


def valor_presente(flujo, tasa_anual_pct):
    """Valor presente de un flujo mensual, descontado a la tasa indicada."""
    i = tasa_mensual(tasa_anual_pct)
    return sum(pago / (1 + i) ** (t + 1) for t, pago in enumerate(flujo))


# ---------------------------------------------------------------
# Bloque 5. Secuencia histórica de rentabilidad real (promedio anual del SPP)
# Es la trayectoria que alimenta la simulación del retiro programado.
# ---------------------------------------------------------------
rentab_anual = (base.groupby("anio")["rentab_real_12m"].mean().dropna())
secuencia_rentab = rentab_anual.tolist()
escribir_log(f"Secuencia de rentabilidad real: {len(secuencia_rentab)} años, "
             f"de {min(secuencia_rentab):.2f} % a {max(secuencia_rentab):.2f} %")

tasa_bono_real_prom = base["tasa_bono_real"].mean()
rentab_real_prom = base["rentab_real_12m"].mean()

# ---------------------------------------------------------------
# Bloque 6. Tabla 1: pensión según el mes de jubilación
# Responde a la pregunta: ¿cuánto cambia la pensión según cuándo te jubilas?
# ---------------------------------------------------------------
filas = []
for _, fila in base.iterrows():
    if pd.isna(fila["tasa_bono_real"]) or pd.isna(fila["rentab_real_12m"]):
        continue
    rv = pension_renta_vitalicia(SALDO_INICIAL, fila["tasa_bono_real"], HORIZONTE_BASE)
    filas.append({
        "mes": fila["mes"], "anio": fila["anio"], "afp": fila["afp"],
        "bono_nominal": fila["rend_bono_10a_soles"],
        "inflacion": fila["inflacion_12m"],
        "bono_real": fila["tasa_bono_real"],
        "rentab_real_fondo": fila["rentab_real_12m"],
        "pension_rv": rv,
    })

resultados = pd.DataFrame(filas)
resultados.to_csv(CARPETA_SALIDAS / "tabla1_pension_por_mes.csv", index=False, encoding="utf-8")
escribir_log(f"Tabla 1: {len(resultados)} filas")

# ---------------------------------------------------------------
# Bloque 7. Tabla 2: comparación de modalidades con trayectoria histórica
# ---------------------------------------------------------------
pensiones_rp, flujo_rp, herencia = simular_retiro_programado(
    SALDO_INICIAL, secuencia_rentab, HORIZONTE_BASE)
rv_base = pension_renta_vitalicia(SALDO_INICIAL, tasa_bono_real_prom, HORIZONTE_BASE)

comparacion = pd.DataFrame([{
    "modalidad": "Renta vitalicia",
    "pension_inicial": round(rv_base, 2),
    "pension_final": round(rv_base, 2),
    "pension_minima": round(rv_base, 2),
    "vp_descontado": round(valor_presente([rv_base] * HORIZONTE_BASE * PAGOS_POR_ANIO,
                                          tasa_bono_real_prom), 2),
    "saldo_heredable": 0.0,
}, {
    "modalidad": "Retiro programado",
    "pension_inicial": round(pensiones_rp[0], 2),
    "pension_final": round(pensiones_rp[-1], 2),
    "pension_minima": round(min(pensiones_rp), 2),
    "vp_descontado": round(valor_presente(flujo_rp, tasa_bono_real_prom), 2),
    "saldo_heredable": round(herencia, 2),
}])
comparacion.to_csv(CARPETA_SALIDAS / "tabla2_comparacion.csv", index=False, encoding="utf-8")
print("\n----- Tabla 2: comparación de modalidades -----")
print(comparacion.to_string(index=False))

# ---------------------------------------------------------------
# Bloque 8. Tabla 3: sensibilidad al horizonte de vida
# ---------------------------------------------------------------
filas_sens = []
for h in HORIZONTES_SENSIBILIDAD:
    rv = pension_renta_vitalicia(SALDO_INICIAL, tasa_bono_real_prom, h)
    p_rp, f_rp, _ = simular_retiro_programado(SALDO_INICIAL, secuencia_rentab, h)
    filas_sens.append({
        "horizonte_anios": h,
        "edad_final": EDAD_JUBILACION + h,
        "pension_rv": round(rv, 2),
        "pension_rp_inicial": round(p_rp[0], 2),
        "pension_rp_final": round(p_rp[-1], 2),
        "vp_rp": round(valor_presente(f_rp, tasa_bono_real_prom), 2),
    })
sensibilidad = pd.DataFrame(filas_sens)
sensibilidad.to_csv(CARPETA_SALIDAS / "tabla3_sensibilidad.csv", index=False, encoding="utf-8")
print("\n----- Tabla 3: sensibilidad al horizonte -----")
print(f"(bono real promedio {tasa_bono_real_prom:.2f} %, rentabilidad real promedio {rentab_real_prom:.2f} %)")
print(sensibilidad.to_string(index=False))

# ---------------------------------------------------------------
# Bloque 9. Punto de indiferencia
# Rentabilidad constante del fondo a la que el valor presente del retiro
# programado iguala el del flujo de la renta vitalicia.
# ---------------------------------------------------------------
vp_rv = valor_presente([rv_base] * HORIZONTE_BASE * PAGOS_POR_ANIO, tasa_bono_real_prom)
puntos = []
for g in np.arange(-2.0, 12.05, 0.05):
    _, flujo_g, _ = simular_retiro_programado(SALDO_INICIAL, [g], HORIZONTE_BASE)
    puntos.append({"rentab_fondo": round(g, 2),
                   "vp_rp": valor_presente(flujo_g, tasa_bono_real_prom)})
curva = pd.DataFrame(puntos)
curva["diferencia"] = curva["vp_rp"] - vp_rv
indiferencia = curva.iloc[curva["diferencia"].abs().idxmin()]
curva.to_csv(CARPETA_SALIDAS / "tabla4_punto_indiferencia.csv", index=False, encoding="utf-8")
escribir_log(f"Punto de indiferencia: {indiferencia['rentab_fondo']:.2f} % de rentabilidad real "
             f"frente a bono real de {tasa_bono_real_prom:.2f} %")

# ---------------------------------------------------------------
# Bloque 10. Figuras
# ---------------------------------------------------------------
# --- Figura 1: pensión de renta vitalicia según el mes de jubilación ---
# Se grafica solo la pensión (la tasa es su determinante directo) y se
# sombrea el periodo en que la tasa real fue negativa.
serie = (resultados.groupby("mes")
         .agg(tasa=("bono_real", "first"), rv=("pension_rv", "mean"))
         .reset_index())
x = pd.PeriodIndex(serie["mes"], freq="M").to_timestamp()

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(x, serie["rv"], color="tab:red", linewidth=1.8)
ax.fill_between(x, ax.get_ylim()[0], ax.get_ylim()[1],
                where=(serie["tasa"] < 0), color="grey", alpha=0.25,
                label="Tasa real negativa")
ax.axhline(serie["rv"].mean(), color="black", linestyle=":", linewidth=1,
           label=f"Promedio: S/ {serie['rv'].mean():.0f}")
ax.set_xlabel("Mes de jubilación")
ax.set_ylabel("Pensión mensual de renta vitalicia (S/)")
ax.set_title(f"Pensión según el mes de jubilación (saldo de S/ {SALDO_INICIAL:,}, "
             f"horizonte de {HORIZONTE_BASE} años)")
ax.legend()
fig.tight_layout()
fig.savefig(CARPETA_SALIDAS / "figura1_pension_por_mes.png", dpi=200)
plt.close(fig)
escribir_log(f"Figura 1: pensión entre S/ {serie['rv'].min():.0f} y S/ {serie['rv'].max():.0f} "
             f"según el mes de jubilación")

# --- Figura 2: valor cuota indexado en una fecha común ---
# Los niveles absolutos no son comparables entre AFP (cada una inició su cuota
# en un valor distinto), y indexar en fechas distintas tampoco lo permite.
# Por eso se indexa en un mes común donde todas las AFP vigentes ya operaban,
# y se omiten las que tienen muy poca historia desde ese mes.
completa = pd.read_csv(CARPETA_PROC / f"datos_procesados_{CODIGO}.csv")
completa = completa[completa["tipo_fondo"] == FONDO_ANALISIS].copy()
completa = completa[completa["valor_cuota"] > 0]          # descarta ceros
completa = completa[completa["mes"] >= MES_BASE_INDICE]   # desde el mes base
completa = completa.sort_values(["afp", "mes"])

fig, ax = plt.subplots(figsize=(10, 5))
for afp, g in completa.groupby("afp"):
    fila_base = g[g["mes"] == MES_BASE_INDICE]
    if fila_base.empty:                    # AFP que ya no operaba en el mes base
        continue
    if len(g) < MESES_MINIMOS_FIGURA:      # AFP en proceso de salida del mercado
        escribir_log(f"Figura 2: se omite {afp} por tener solo {len(g)} meses desde {MES_BASE_INDICE}")
        continue
    referencia = fila_base["valor_cuota"].iloc[0]
    indexado = g["valor_cuota"] / referencia * 100
    ejex = pd.PeriodIndex(g["mes"], freq="M").to_timestamp()
    crecimiento = indexado.iloc[-1] - 100
    ax.plot(ejex, indexado, label=f"{afp} (+{crecimiento:.0f} %)")

ax.axhline(100, color="black", linewidth=0.8, linestyle=":")
ax.set_xlabel("Periodo")
ax.set_ylabel(f"Valor cuota indexado ({MES_BASE_INDICE} = 100)")
ax.set_title(f"Crecimiento del valor cuota del Fondo {FONDO_ANALISIS} por AFP, "
             f"{MES_BASE_INDICE} a 2025-12")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(CARPETA_SALIDAS / "figura2_valor_cuota_indexado.png", dpi=200)
plt.close(fig)
escribir_log(f"Figura 2: valor cuota indexado con base {MES_BASE_INDICE}")

# --- Figura 3: perfil de las dos modalidades ---
fig, ax = plt.subplots(figsize=(10, 5))
edades = list(range(EDAD_JUBILACION, EDAD_JUBILACION + len(pensiones_rp)))
ax.plot(edades, pensiones_rp, marker="o", label="Retiro programado")
ax.axhline(rv_base, color="tab:red", linestyle="--",
           label=f"Renta vitalicia: S/ {rv_base:.0f} constantes")
ax.set_xlabel("Edad del jubilado")
ax.set_ylabel("Pensión mensual (S/)")
ax.set_title(f"Perfil de la pensión según modalidad (horizonte de {HORIZONTE_BASE} años)")
ax.legend()
fig.text(0.01, 0.01,
         "Nota: ejercicio retrospectivo. El retiro programado se simula aplicando la secuencia "
         "de rentabilidad real observada en 2010-2025; no es una proyección.",
         fontsize=7, style="italic")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(CARPETA_SALIDAS / "figura3_perfil_pensiones.png", dpi=200)
plt.close(fig)

escribir_log("Figuras 1, 2 y 3 guardadas en /salidas")

print("\n----- Resultado principal -----")
print(f"Bono nominal promedio:        {base['rend_bono_10a_soles'].mean():.2f} %")
print(f"Inflación promedio:           {base['inflacion_12m'].mean():.2f} %")
print(f"Bono REAL promedio:           {tasa_bono_real_prom:.2f} %")
print(f"Rentabilidad REAL del fondo:  {rentab_real_prom:.2f} %")
print(f"Punto de indiferencia:        {indiferencia['rentab_fondo']:.2f} %")
print(f"Pensión RV mínima y máxima:   S/ {serie['rv'].min():.0f} a S/ {serie['rv'].max():.0f}")

escribir_log("Fin de 04_analisis.py")


# ---------------------------------------------------------------
# Bloque 11. Tablas adicionales del artículo
# Estadística descriptiva, evolución anual, subperiodos, comparación por
# AFP y por tipo de fondo, y modelo econométrico de panel.
# ---------------------------------------------------------------
from linearmodels.panel import PanelOLS

completa = pd.read_csv(CARPETA_PROC / f"datos_procesados_{CODIGO}.csv")
f2 = completa[completa["tipo_fondo"] == FONDO_ANALISIS].copy()
f2.loc[f2["valor_cuota"] <= 0, "valor_cuota"] = np.nan   # valor nulo de Horizonte (2013-08)

# Estadística descriptiva del Fondo 2
columnas = ["valor_cuota", "valor_fondo_mill_soles", "afiliados_miles",
            "rentab_real_12m", "rend_bono_10a_soles", "inflacion_12m"]
descriptiva = (f2[columnas].describe()
               .loc[["count", "mean", "std", "min", "max"]].T.round(2))
descriptiva.to_csv(CARPETA_SALIDAS / "tabla_estadistica_descriptiva.csv", encoding="utf-8")
print("\n----- Estadística descriptiva -----")
print(descriptiva.to_string())

# Evolución anual y por subperiodo (a partir de la Tabla 1 en memoria)
mensual = (resultados.groupby("mes")
           .agg(anio=("anio", "first"), bono_nominal=("bono_nominal", "first"),
                inflacion=("inflacion", "first"), bono_real=("bono_real", "first"),
                rentab_fondo=("rentab_real_fondo", "mean"),
                pension_rv=("pension_rv", "first"))
           .reset_index())

anual = (mensual.groupby("anio")
         [["bono_nominal", "inflacion", "bono_real", "rentab_fondo", "pension_rv"]]
         .mean().round(2))
anual.to_csv(CARPETA_SALIDAS / "tabla_anual.csv", encoding="utf-8")
print("\n----- Evolución anual -----")
print(anual.to_string())


def etapa(a):
    if a <= 2015:
        return "2010-2015"
    if a <= 2019:
        return "2016-2019"
    if a <= 2022:
        return "2020-2022"
    return "2023-2025"


mensual["subperiodo"] = mensual["anio"].apply(etapa)
subperiodos = (mensual.groupby("subperiodo")
               .agg(meses=("mes", "count"), bono_real=("bono_real", "mean"),
                    rentab_fondo=("rentab_fondo", "mean"),
                    pension_rv=("pension_rv", "mean"),
                    pct_tasa_negativa=("bono_real", lambda s: (s < 0).mean() * 100))
               .round(2))
subperiodos.to_csv(CARPETA_SALIDAS / "tabla_subperiodos.csv", encoding="utf-8")
print("\n----- Subperiodos -----")
print(subperiodos.to_string())

# Comparación por AFP (Fondo 2, sin filas imputadas)
por_afp = (f2[f2["imputado"] == "No"].dropna(subset=["rentab_real_12m"])
           .groupby("afp")
           .agg(meses=("mes", "count"), rentab_prom=("rentab_real_12m", "mean"),
                rentab_desv=("rentab_real_12m", "std"),
                fondo_prom=("valor_fondo_mill_soles", "mean"),
                afiliados_prom=("afiliados_miles", "mean"))
           .round(2))
por_afp.to_csv(CARPETA_SALIDAS / "tabla_por_afp.csv", encoding="utf-8")
print("\n----- Por AFP -----")
print(por_afp.to_string())

# Comparación por tipo de fondo (retorno nominal mensual del valor cuota)
v = (completa[completa["valor_cuota"] > 0]
     .sort_values(["afp", "tipo_fondo", "mes"]).copy())
v["ret_mensual"] = v.groupby(["afp", "tipo_fondo"])["valor_cuota"].pct_change(fill_method=None)
r = v.dropna(subset=["ret_mensual"])
por_fondo = (r.groupby("tipo_fondo")
             .agg(observaciones=("ret_mensual", "count"), desde=("mes", "min"),
                  retorno_anual=("ret_mensual", lambda s: ((1 + s.mean()) ** 12 - 1) * 100),
                  volatilidad_anual=("ret_mensual", lambda s: s.std() * np.sqrt(12) * 100))
             .round(2))
por_fondo.to_csv(CARPETA_SALIDAS / "tabla_por_fondo.csv", encoding="utf-8")
print("\n----- Por tipo de fondo -----")
print(por_fondo.to_string())


# Modelo de panel con efectos fijos por AFP
def estimar_panel(datos):
    d = datos.copy()
    d["ln_fondo"] = np.log(d["valor_fondo_mill_soles"])
    d["ln_afiliados"] = np.log(d["afiliados_miles"])
    d["fecha"] = pd.PeriodIndex(d["mes"], freq="M").to_timestamp()
    variables = ["rend_bono_10a_soles", "ln_fondo", "ln_afiliados", "inflacion_12m"]
    d = d.dropna(subset=["rentab_real_12m"] + variables).set_index(["afp", "fecha"])
    return PanelOLS(d["rentab_real_12m"], d[variables], entity_effects=True).fit(cov_type="robust")


res1 = estimar_panel(f2)                                  # todas las observaciones
res2 = estimar_panel(f2[f2["imputado"] == "No"])          # sin filas imputadas
panel = pd.DataFrame({
    "coef_todas": res1.params, "ee_todas": res1.std_errors, "p_todas": res1.pvalues,
    "coef_sin_imputadas": res2.params, "ee_sin_imputadas": res2.std_errors,
    "p_sin_imputadas": res2.pvalues}).round(4)
panel.to_csv(CARPETA_SALIDAS / "tabla_panel.csv", encoding="utf-8")
print("\n----- Panel con efectos fijos -----")
print(panel.to_string())
escribir_log(f"Panel (todas): {res1.nobs} obs, R2 within {res1.rsquared_within:.4f}, "
             f"poolability F={res1.f_pooled.stat:.4f} (p={res1.f_pooled.pval:.4f})")
escribir_log(f"Panel (sin imputadas): {res2.nobs} obs, R2 within {res2.rsquared_within:.4f}")
escribir_log("Bloque 11: tablas adicionales guardadas en /salidas")
