# Diccionario de variables

**Archivo:** datos_procesados/datos_procesados_2024200509B.csv
**Autor:** Andy Donato Mendoza Flores - codigo 2024200509B
**Tema 25:** Renta vitalicia frente a retiro programado en el SPP
**Periodo:** enero 2010 - diciembre 2025 | **Filas:** 2781 | **Columnas:** 13
**Unidad de observacion:** AFP x tipo de fondo x mes

| Variable | Definicion | Unidad | Frecuencia | Fuente |
|---|---|---|---|---|
| mes | Periodo mensual (AAAA-MM) | - | Mensual | Construida |
| anio | Anio de la observacion | - | Anual | Construida |
| afp | Administradora de fondos de pensiones | - | - | SBS |
| tipo_fondo | Tipo de fondo: 0, 1, 2, 3 | - | - | SBS |
| valor_cuota | Valor cuota del ultimo dia habil del mes | Soles | Mensual | SBS |
| valor_fondo_mill_soles | Valor del fondo administrado | Millones S/ | Mensual | BCRP (SBS) |
| afiliados_miles | Numero de afiliados activos | Miles | Mensual | BCRP (SBS) |
| rentab_real_12m | Rentabilidad real de 12 meses | Porcentaje | Mensual | BCRP (SBS) |
| rend_bono_10a_soles | Rendimiento del bono a 10 anios en soles | Porcentaje | Mensual | BCRP (MEF) |
| inflacion_12m | Variacion del IPC de Lima en 12 meses | Porcentaje | Mensual | BCRP (INEI) |
| esperanza_vida | Esperanza de vida al nacer | Anios | Anual | Banco Mundial |
| dias_habiles | Dias habiles con valor cuota en el mes | Dias | Mensual | Construida |
| imputado | Si la fila tiene alguna celda imputada | Si/No | - | Construida |

## Codigos de serie del BCRP

Valor del fondo: PN01168MM (Habitat), PN01169MM (Integra), PN01170MM (Prima), PN01171MM (Profuturo)
Afiliados: PN01174MM, PN01175MM, PN01176MM, PN01177MM
Rentabilidad real: PN01179MM, PN01180MM, PN01181MM, PN01182MM
Bono a 10 anios: PD31895MM
IPC Lima: PN01273PM
Banco Mundial: SP.DYN.LE00.IN

## Endpoints utilizados

BCRP: https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{codigo}/json/2010-1/2025-12/esp
Banco Mundial: https://api.worldbank.org/v2/country/PER/indicator/SP.DYN.LE00.IN?format=json&date=2010:2025&per_page=100
SBS 2015-2025: https://intranet2.sbs.gob.pe/estadistica/financiera/{anio}/{Mes}/FP-1359-{mes}{anio}.XLS
SBS 2010-2014: https://intranet2.sbs.gob.pe/estadistica/spp/{anio}/{Mes}/FP-1231-{mes}{anio}.ZIP

## Variables calculadas en el analisis (script 04)

No forman parte del archivo procesado; se derivan en 04_analisis.py.

| Variable | Definicion |
|---|---|
| tasa_bono_real | Ecuacion de Fisher: (1 + nominal) / (1 + inflacion) - 1 |
| pension_rv | Saldo dividido entre el factor de anualidad |
| pension_rp | Pension recalculada cada anio segun el saldo restante |
| vp_descontado | Valor presente del flujo, descontado a la tasa real |

## Tratamiento de datos faltantes

| Caso | Tratamiento | Justificacion |
|---|---|---|
| Habitat antes de junio 2013 | Celda vacia | La AFP no operaba |
| Horizonte en series del BCRP | Celda vacia | El BCRP solo publica AFP vigentes |
| Esperanza de vida 2025 | Celda vacia | El Banco Mundial aun no lo publica |
| Huecos aislados | Interpolacion lineal, marcada en imputado | Solo entre datos reales |

Ninguna serie fue extendida hacia atras ni rellenada mas alla de lo que publica la fuente oficial.
