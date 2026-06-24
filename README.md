# Automatizacion datos Mundial 2026

Este flujo consume los CSV publicados por `Bustami/efi-fifa-data-wc-2026` y genera un archivo JS y un JSON pequeno para el interactivo con los jugadores de FC Barcelona y Real Madrid.

## Archivos

- `jugadores_clubes.json`: lista editable de jugadores por club. El repositorio de FIFA no incluye el club actual de cada jugador, asi que esta capa hay que mantenerla aqui.
- `resultados_selecciones.csv`: override manual OPCIONAL del resultado por seleccion y partido (`win`, `draw`, `loss`). Ya no hace falta rellenarlo: el resultado se deduce solo de los goles del dataset. Solo se usa para corregir algun partido puntual; si una fila existe, manda sobre el calculo automatico.
- `actualizar_mundial_2026.py`: descarga `wc2026_efi.csv` y `wc2026_matches.csv`, filtra los jugadores configurados y agrega PJ, goles, asistencias, minutos, victorias, empates y derrotas.
- `data/mundial_2026_clubes.js`: salida recomendada para CMS. Expone `var MUNDIAL_2026_CLUBES = ...`.
- `data/mundial_2026_clubes.json`: salida alternativa en JSON.
- `mundial_2026_preview.html`: vista HTML de comprobacion con celdas por jugador y totales. Carga el archivo JS.

## Despliegue: GitHub Actions como robot que publica en el FTP

La web NO se aloja en GitHub. El especial (HTML + carpeta `data/`) vive en el FTP de la empresa. GitHub solo actua de "robot" gratuito que cada 15 minutos regenera los datos y los sube a ese FTP. No hace falta tener ninguna maquina encendida.

Flujo (`.github/workflows/actualizar-mundial-2026.yml`):

1. `python3 actualizar_mundial_2026.py --compact` genera `data/mundial_2026_clubes.js` y `.json`.
2. `python3 subir_ftp.py` los sube al FTP.

Sondea cada 15 minutos en la franja de partidos (16:00-03:59 UTC) mas una pasada de seguridad a las 05:15 UTC. En la practica los datos aparecen en el FTP unos 15 minutos despues de que termine un partido de un jugador del FCB/RM y la fuente lo publique. Al sondear de forma continua, los retrasos, aplazamientos y prorrogas se cubren solos.

### Puesta en marcha (una sola vez)

1. Sube esta carpeta a un repositorio de GitHub (puede ser privado; solo es el robot, no la web).
2. En el repo: `Settings > Secrets and variables > Actions > New repository secret`, crea:
   - `FTP_HOST`: host del FTP.
   - `FTP_USER`: usuario.
   - `FTP_PASS`: contrasena.
   - `FTP_DIR`: carpeta destino en el FTP, la misma donde el HTML busca `data/` (por ejemplo `/especiales/mundial-2026/data`).
   - `FTP_TLS` (opcional): `1` para FTPS (recomendado) o `0` para FTP plano.
   - `FTP_PORT` (opcional): por defecto 21.
3. Sube al FTP, una sola vez, el `mundial_2026_preview.html` (o el HTML del CMS) y la carpeta `data/`. A partir de ahi el robot va sobrescribiendo solo los ficheros de `data/`.
4. Comprueba que funciona lanzando el workflow a mano desde la pestana `Actions > Actualizar datos Mundial 2026 > Run workflow`.

Para el CMS usa el archivo JS:

```html
<script src="data/mundial_2026_clubes.js"></script>
```

La variable disponible sera:

```js
MUNDIAL_2026_CLUBES
```

## Uso local opcional

```bash
python3 actualizar_mundial_2026.py
```

Si el interactivo necesita los archivos minificados:

```bash
python3 actualizar_mundial_2026.py --compact
```

## Salida

Cada jugador tiene:

- `matches_played`: suma de `matches_played`.
- `goals`: suma de `goals`.
- `assists`: suma de `assists`.
- `minutes`: suma redondeada de `time_played`.
- `minutes_raw`: suma con un decimal.
- `wins`: victorias de su seleccion en los partidos que jugo.
- `draws`: empates de su seleccion en los partidos que jugo.
- `losses`: derrotas de su seleccion en los partidos que jugo.
- `result_pending`: partidos jugados cuyo resultado de seleccion aun no esta informado.
- `fixtures_pending`: partidos futuros pendientes de disputar por su seleccion.
- `matches`: detalle por partido con fecha, fase, rival y datos del jugador.
- `fixtures`: detalle de partidos futuros pendientes de su seleccion.

En los totales de club, `matches_played`, `wins`, `draws`, `losses`, `result_pending` y `fixtures_pending` cuentan partidos unicos por seleccion. Si hay varios jugadores del mismo club en la misma seleccion, ese partido no se multiplica. `goals`, `assists` y `minutes` si se acumulan jugador por jugador.

Nota: `wc2026_matches.csv` no incluye marcadores, pero `victorias`, `empates` y `derrotas` se calculan automaticamente sumando los goles de los jugadores de cada seleccion en `wc2026_efi.csv` (mas los goles en propia del rival) y comparando ambos marcadores. Esta deduccion reproduce los resultados reales de los partidos ya disputados. `resultados_selecciones.csv` solo se consulta como override manual si quieres forzar el resultado de un partido concreto.
