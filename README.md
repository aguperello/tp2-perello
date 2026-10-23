# Buscador de precios vigentes de combustibles

**Autor:** Augusto Perello · Programación Orientada a Datos · TP2 (individual)

## Problema, usuario y solución

**Problema.** Los precios de combustibles en surtidor cambian seguido. El archivo oficial acumula
cada actualización que informa cada estación, para varios combustibles y fechas. Si se comparan
registros sin elegir cuál está vigente, se miran precios desactualizados y se sacan conclusiones
equivocadas.

**Usuario.** Una persona que quiere saber dónde cargar más barato en su localidad (conductor
particular, transportista, quien presupuesta un viaje), o consultar cuánto costaba un combustible
en una fecha pasada.

**Solución.** Una aplicación de consola que recibe **localidad**, **combustible** y **fecha de
referencia**. Para cada estación elige el registro más reciente que no supere esa fecha y devuelve
las estaciones ordenadas de menor a mayor precio. Lee CSV o JSON con la misma estructura.

## Funcionalidades

- Consulta de precios vigentes por localidad, combustible y fecha (opcional: tipo de horario).
- Lectura de CSV y JSON mediante una interfaz común (`FuenteDatos`).
- Validación del esquema, limpieza y **archivo de registros rechazados con el motivo**.
- Exportación del resultado a CSV, con la fecha de vigencia de cada precio.
- `--listar localidades|combustibles` para ver qué valores existen en el archivo.

**Alcance de la primera versión.** *Incluye:* una localidad y un combustible por consulta,
selección por vigencia, orden por precio, validación de parámetros y registro de rechazos.
*Queda afuera:* mapas y geolocalización, distancias, comparación entre combustibles, interfaz web,
descarga automática de los datos y análisis de evolución histórica.

**Reglas de decisión.**
- Una estación sin ningún registro anterior o igual a la fecha de consulta **no aparece** en el resultado (se informa cuántas son).
- No se mezclan combustibles ni localidades en una misma consulta. La comparación ignora mayúsculas y acentos.
- Registros idénticos repetidos: se conserva el primero y los demás se rechazan como `duplicado`.
- Misma estación, combustible, horario y fecha con **precios distintos**: se rechazan todos como `contradictorio`.
- Una consulta sin resultados devuelve un mensaje explícito.

## Datos

Fuente: dataset *Precios en Surtidor - Resolución 314/2016* (Secretaría de Energía de la Nación),
recurso "Precios históricos", licencia CC-BY-4.0. **Unidad de análisis:** una fila es un precio
informado por una estación, para un combustible y un tipo de horario, con una fecha de vigencia.
Detalle de variables, procedencia, muestras y limitaciones en [`data/README.md`](data/README.md).

## Instalación

Requiere Python 3.10 o superior. No hay dependencias externas (ver `requirements.txt`).

```
git clone <URL-DEL-REPOSITORIO>
cd tp2-apellido
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
```

## Uso

Siempre desde la raíz del repositorio:

```
python -m src.main --entrada data/muestra.csv --localidad "Rosario" --combustible "Gas Oil Grado 2" --fecha 2026-10-14
```

| Parámetro | Descripción |
|---|---|
| `--entrada` | Archivo `.csv` o `.json` (obligatorio) |
| `--localidad`, `--combustible`, `--fecha` | Parámetros de la consulta; la fecha es `AAAA-MM-DD` |
| `--horario` | Filtro opcional por tipo de horario |
| `--salida` | CSV de resultado (por defecto `outputs/consulta.csv`) |
| `--rechazos` | CSV de rechazados (por defecto `outputs/rechazos.csv`) |
| `--top` | Filas a mostrar en pantalla (se guardan todas) |
| `--listar localidades\|combustibles` | Lista los valores disponibles y termina |

Para probar sin los datos reales, usá la muestra sintética incluida:

```
python -m src.main --entrada data/muestra_sintetica.csv --localidad Rosario --combustible "Nafta (súper) entre 92 y 95 Ron" --fecha 2026-10-14
```

**Generar la muestra real** (662 filas de Rosario) a partir del CSV histórico descargado (ver `data/README.md`):

```
python -m src.preparar_muestra --entrada precios-historicos.csv --localidad "Rosario" --desde 2026-05-01 --hasta 2026-10-20
```

## Pruebas

```
python -m unittest discover -s tests -t . -v
```

Cubren: caso normal, vigencia con varias actualizaciones, día de referencia incluido, localidad
sin resultados, fechas inválidas, precios inválidos, duplicados y contradictorios, errores de
lectura (archivo inexistente, JSON mal formado), y propiedades del resultado (orden por precio,
sin precios posteriores a la fecha, una fila por estación, **equivalencia entre CSV y JSON**).

## Organización del código

```
src/
  main.py            Interfaz de consola: argumentos, coordinación, salida
  fuentes.py         FuenteDatos (abstracta) -> FuenteCSV, FuenteJSON; fuente_para()
  modelo.py          ConsultaPrecio: valida parámetros y decide qué filas coinciden
  pipeline.py        normalizar -> validar esquema -> limpiar -> seleccionar -> verificar -> exportar
  errores.py         Excepciones con mensajes comprensibles
  preparar_muestra.py  Recorta el CSV histórico a una muestra CSV+JSON equivalente
  datos_sinteticos.py  Genera la muestra sintética de demostración
tests/               Pruebas unittest y fixtures con respuestas conocidas
data/                Muestras y README de datos
```

**Decisiones de diseño.**
- *Clase base `FuenteDatos`:* la lógica (`pipeline.py`) solo recibe `list[dict]`; agregar un formato nuevo no la toca.
- *Clase `ConsultaPrecio`:* concentra la validación de parámetros y el criterio de coincidencia, así el pipeline no repite esas reglas.
- *Expresiones regulares:* `FECHA_REGISTRO_RE` (`pipeline.py`) valida que la fecha de cada registro tenga la forma `AAAA-MM-DD[ HH:MM[:SS]]`; `FECHA_CONSULTA_RE` (`modelo.py`) hace lo mismo con el parámetro `--fecha`. **No comprueban que la fecha exista:** eso lo hace `strptime`/`date()` (rechaza `2026-02-30` o `2026-02-29`).

## Ejemplo de resultado

> Ejecutado con la muestra **real** de Rosario (dataset de la Secretaría de Energía), con `--horario Diurno --top 5`.

```
python -m src.main --entrada data/muestra.csv --localidad "Rosario" --combustible "Nafta (súper) entre 92 y 95 Ron" --fecha 2026-10-14 --horario Diurno --top 5

Consulta: Nafta (súper) entre 92 y 95 Ron en Rosario, precios vigentes al 2026-10-14
Filas leídas: 662 | válidas: 662 | rechazadas: 0 (ver outputs/rechazos.csv)

Precio   Empresa                        Dirección                    Horario  Vigente desde
-------  -----------------------------  ---------------------------  -------  ----------------
2049.00  RICON SRL                      URIBURU 2010                 Diurno   2026-05-20 16:12
2159.00  MADEGAS SA                     AV. PTE PERON 6575           Diurno   2026-10-09 08:30
2169.00  CIRCUNVALACION SERVICIOS S.A.  BAIGORRIA 2630               Diurno   2026-10-01 00:00
2212.00  BRIBAL AGRO SRL                PUEYRREDON 1089              Diurno   2026-09-22 09:17
2212.00  ENERGÍA & SERVICIOS SA         AV CÓRDOBA Y CIRCUNVALACIÓN  Diurno   2026-09-23 06:00

17 estaciones con precio vigente; 0 sin precio vigente a esa fecha.
```

La muestra real de Rosario no tuvo filas rechazadas. Para mostrar la limpieza se usa la muestra
**sintética** (datos inventados, con casos sucios a propósito). Fragmento de su `outputs/rechazos.csv`:

```
fila,motivo,detalle,...
64,precio_fuera_de_rango,El precio -5.0 debe ser mayor que cero.,...
65,precio_no_numerico,El precio 'abc' no es un número.,...
66,fecha_formato_invalido,'14/06/2026' no tiene el formato AAAA-MM-DD [HH:MM[:SS]],...
```

## Decisiones de limpieza

| Motivo de rechazo | Cuándo ocurre |
|---|---|
| `campo_faltante:<campo>` | Falta un campo obligatorio (estación, localidad, combustible, precio o fecha) |
| `precio_no_numerico` | El precio no se puede convertir a número (se acepta coma decimal) |
| `precio_fuera_de_rango` | El precio es cero o negativo |
| `fecha_formato_invalido` | La fecha no respeta `AAAA-MM-DD[ HH:MM[:SS]]` |
| `fecha_inexistente` | Respeta el formato pero no existe en el calendario |
| `duplicado` | Registro idéntico a otro (se conserva el primero) |
| `contradictorio` | Mismo registro lógico con precios distintos (se rechazan todos) |

**Formato de fecha de la fuente.** El CSV oficial trae las fechas como `DD/MM/AAAA HH:MM`. Al generar la muestra,
`preparar_muestra` las convierte a `AAAA-MM-DD HH:MM`; si una fecha no existe en el calendario se deja
igual para que la limpieza la rechace y la registre.

Los valores faltantes **nunca se convierten en cero**: la fila se rechaza y se informa.
Cada rechazo queda en `outputs/rechazos.csv` con número de fila, motivo y detalle.

## Interpretación y limitaciones

- El resultado es "el último precio **informado** por cada estación hasta esa fecha", no el precio real garantizado en el surtidor.
- Un precio viejo puede seguir figurando como vigente si la estación no reportó un cambio; por eso se muestra siempre la fecha de vigencia.
- Si un registro contradictorio se rechaza, la estación puede quedar con su precio anterior como vigente.
- La identificación de estación (`idempresa` + `direccion`) y los nombres de las columnas son supuestos documentados; verificar contra la fuente (ver `data/README.md`).
- El archivo completo se carga en memoria: para el histórico completo conviene recortarlo antes con `preparar_muestra`.
- El precio se informa en la unidad de la fuente (pesos por litro; el GNC se vende por m³); la aplicación no convierte unidades ni compara combustibles entre sí.

## Versión evaluada

**[COMPLETAR]** Hash de commit o etiqueta entregada: `git rev-parse --short HEAD` / `git tag`.
