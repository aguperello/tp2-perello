# Datos

## Fuente real

| Campo | Valor |
|---|---|
| Dataset | *Precios en Surtidor - Resolución 314/2016*, recurso **Precios históricos** |
| Publica | Secretaría de Energía de la Nación (Subsecretaría de Eficiencia e Información Energética, Dirección Nacional de Escenarios y Evaluación de Proyectos) |
| Ficha | https://datos.gob.ar/dataset/precios-en-surtidor |
| Portal de origen | http://datos.energia.gob.ar/dataset/precios-en-surtidor |
| Descarga directa del recurso | http://datos.energia.gob.ar/dataset/1c181390-5045-475e-94dc-410429be4b17/resource/f8dda0d5-2a9f-4d34-b79b-4e63de3995df/download/precios-historicos.csv |
| Licencia | CC-BY-4.0 (según la ficha de datos.gob.ar) — requiere citar la fuente |
| Publicación original | 2018-03-21 · actualización declarada: cada hora |
| Fecha de consulta | 2026-10-23 |

**Contexto normativo.** Los datos se originaron en el régimen de la Resolución 314/2016
(informar cada cambio de precio en surtidor). Esa resolución fue abrogada por la Resolución
717/2025 del Ministerio de Economía (B.O. 02/06/2025). El dataset se sigue publicando, pero
el reporte actual puede ser menos completo que antes.

## Unidad de análisis

Cada fila es **un precio informado por una estación de servicio, para un combustible y un
tipo de horario, con una fecha desde la cual rige**. Una misma estación aparece en muchas filas
(una por cada actualización).

## Variables utilizadas

> Los nombres de la columna "En el archivo" se verificaron contra el encabezado real del CSV. Si el archivo
> cambia, se pueden agregar alias en `CAMPOS_ORIGEN` (`src/pipeline.py`). En el CSV oficial,
> `fecha_vigencia` viene como `DD/MM/AAAA HH:MM` y `preparar_muestra` la convierte a `AAAA-MM-DD HH:MM`.

| Variable interna | En el archivo | Descripción | Unidad / tipo |
|---|---|---|---|
| `estacion_id` | `idempresa` | Identificador de la empresa que opera la boca de expendio | texto |
| `empresa` | `empresa` | Razón social | texto |
| `direccion` | `direccion` | Dirección de la boca de expendio | texto |
| `localidad` | `localidad` | Localidad | texto |
| `provincia` | `provincia` | Provincia | texto |
| `producto` | `producto` | Combustible | texto |
| `tipo_horario` | `tipohorario` | Tipo de horario al que corresponde el precio | texto |
| `precio` | `precio` | Precio en surtidor | pesos por unidad de venta (a confirmar en la fuente; GNC se vende por m³) |
| `fecha_vigencia` | `fecha_vigencia` | Desde cuándo rige el precio | AAAA-MM-DD [HH:MM[:SS]] |

**Supuesto de diseño:** una empresa puede tener varias bocas de expendio, por eso una
estación se identifica por `idempresa` + `direccion`.

## Muestras incluidas

| Archivo | Contenido |
|---|---|
| `muestra_sintetica.csv` / `.json` | **Datos inventados** (71 filas, 8 estaciones ficticias, 2 combustibles, 3 localidades) generados por `python -m src.datos_sinteticos` con semilla fija. Incluyen filas inválidas, duplicadas y contradictorias a propósito. **No son precios reales.** Sirven para probar y demostrar la aplicación. |
| `muestra.csv` / `.json` | Recorte de **datos reales** de Rosario, vigencias del 2026-05-01 al 2026-10-20 (662 filas, 5 combustibles), generado con `python -m src.preparar_muestra`. Ambos archivos contienen las mismas filas. No tuvo filas rechazadas al limpiarla. |

El archivo histórico completo **no se versiona** (es grande). Para reproducir la muestra real:

```
python -m src.preparar_muestra --entrada precios-historicos.csv --localidad "Rosario" --desde 2026-05-01 --hasta 2026-10-20
```

## Limitaciones y sesgos

- Los precios son **declarados por las estaciones**; no están verificados en surtidor.
- Desde la abrogación de la Resolución 314/2016 el reporte no es obligatorio en el mismo sentido,
  por lo que pueden faltar estaciones o actualizaciones recientes (en especial de algunas redes).
- Una estación sin registros hasta la fecha consultada no aparece en el resultado: no significa
  que no venda ese combustible.
- El último precio informado puede no ser el vigente real si la estación no reportó un cambio.
- La muestra cubre una sola localidad y un período acotado: no representa al país.
- Puede haber filas con fechas mal formadas, precios inválidos, duplicados o contradicciones;
  la aplicación las rechaza y las registra (ver README principal).
