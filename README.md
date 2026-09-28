# Renta vitalicia frente a retiro programado en el SPP: valuacion de una anualidad

**Autor:** Andy Donato Mendoza Flores
**Codigo de matricula:** 2024200509B
**Tema 25 del temario** - Semana S04: Valor del dinero en el tiempo II
**Curso:** Finanzas I (055D) - Ciclo V - Periodo 2026-II
**Docente:** Dr. Ciro Ivan Machacuay Meza
**Escuela Profesional de Economia - Facultad de Economia - UNCP**

**Repositorio:** https://github.com/Andy-Donato-Mendoza-Flores/finanzas1-renta-vitalicia-spp

## Objetivo

Valuar la renta vitalicia y el retiro programado como anualidades y determinar
el punto de indiferencia entre ambas modalidades de pension del Sistema Privado
de Pensiones peruano.

## Fuentes de datos

| Fuente | Via | Contenido |
|---|---|---|
| BCRPData | API REST | Valor del fondo, afiliados y rentabilidad real por AFP; bono a 10 anios; IPC |
| Banco Mundial | API REST | Esperanza de vida al nacer del Peru |
| SBS | Descarga programatica | Valor cuota diario por AFP y tipo de fondo |

Los codigos de serie y los endpoints completos estan en diccionario_variables.md.

## Periodo y fecha de corte

FECHA_INICIO = 2010-01 y FECHA_CORTE = 2025-12, declarados como constantes en los scripts.
Fecha de extraccion: 25 de septiembre de 2026.

## Orden de ejecucion

Ejecutar desde la carpeta raiz del proyecto, en este orden:

    python codigo/01_extraccion_api.py
    python codigo/02_scraping_web.py
    python codigo/03_limpieza_datos.py
    python codigo/04_analisis.py

El script 02 tarda entre 10 y 15 minutos la primera vez, porque descarga 192
archivos de la SBS con pausa de 1.5 segundos entre solicitudes. Los archivos ya
descargados no se vuelven a pedir.

## Versiones

Python 3.13.15 (Google Colab). Librerias en requirements.txt.

    pip install -r requirements.txt

## Archivo procesado y verificacion de integridad

Archivo: datos_procesados/datos_procesados_2024200509B.csv
Dimensiones: 2781 filas x 13 columnas
Periodo: 2010-01 a 2025-12
Unidad de observacion: AFP x tipo de fondo x mes

SHA-256: 186929024788f4f82c9ce20bae0fc7bb0a58e67e837b381b70da377304a91bbf

Para verificarlo:

    sha256sum datos_procesados/datos_procesados_2024200509B.csv

## Estructura del proyecto

    codigo/              01_extraccion_api.py, 02_scraping_web.py,
                         03_limpieza_datos.py, 04_analisis.py
    datos_crudos/        archivos tal como salen de cada fuente, sin editar
      sbs_xls/           192 reportes FP-1359 originales
      sbs_zip/           60 boletines FP-1231 originales
    datos_procesados/    datos_procesados_2024200509B.csv
    salidas/             tablas y figuras generadas por 04_analisis.py
    diccionario_variables.md
    requirements.txt
    .env.example
    log_ejecucion.txt
    README.md

Las carpetas sbs_xls y sbs_zip contienen cientos de archivos originales y no se
suben al repositorio; los scripts las regeneran al ejecutarse.

## Claves de acceso

Ninguna fuente empleada requiere clave: la API del BCRP, la del Banco Mundial y
los archivos de la SBS son de acceso publico. El archivo .env.example se incluye
como plantilla, segun el numeral 2.4.4 de la consigna.

## Etica del rastreo

Todas las solicitudes usan un User-Agent identificable con el correo
institucional del autor. Se aplica una pausa minima de 1.5 segundos entre
solicitudes. Se verifico el robots.txt del portal de la SBS, que no restringe
las rutas consultadas; se conserva copia en datos_crudos/sbs_robots.txt. Solo se
accedio a informacion publica agregada; no se extrajeron datos personales.

## Nota sobre la disponibilidad de las fuentes

El reporte FP-1359 de la SBS solo esta publicado desde 2015. Para cubrir
2010-2014 se identifico una segunda ruta: el Boletin Informativo Mensual
(FP-1231), un archivo ZIP que contiene el boletin completo, cuyas hojas
VC-Diario-FondoN incluyen el mismo dato. Ambas rutas estan implementadas en
02_scraping_web.py y el log registra cada solicitud con su codigo de respuesta.
