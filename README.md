# Automatizacion datos Mundial 2026

Este flujo consume los CSV publicados por `Bustami/efi-fifa-data-wc-2026` y genera un archivo JS y un JSON pequeno para el interactivo con los jugadores de FC Barcelona y Real Madrid.

## Archivos

- `jugadores_clubes.json`: lista editable de jugadores por club. El repositorio de FIFA no incluye el club actual de cada jugador, asi que esta capa hay que mantenerla aqui.
- `resultados_selecciones.csv`: override manual OPCIONAL del resultado por seleccion y partido (`win`, `draw`, `loss`). Ya no hace falta rellenarlo: el resultado se deduce solo de los goles del dataset. Solo se usa para corregir algun partido puntual; si una fila existe, manda sobre el calculo automatico.
- `actualizar_mundial_2026.py`: descarga `wc2026_efi.csv` y `wc2026_matches.csv`, filtra los jugadores configurados y agrega PJ, goles, asistencias, minutos, victorias, empates y derrotas.
- `data/mundial_2026_clubes.js`: salida recomendada para CMS. Expone `var MUNDIAL_2026_CLUBES = ...`.
- `data/mundial_2026_clubes.json`: salida alternativa en JSON.
- `mundial_2026_preview.html`: vista HTML de comprobacion con celdas por jugador y totales. Carga el archivo JS.

## Despliegue: la web lee los datos del repositorio publico (sin FTP ni credenciales)

El codigo vive en el repositorio publico de GitHub (`MD-MundoDeportivo/especial-mundial-2026-fcb-rm`). GitHub Actions actua de "robot" gratuito que cada 15 minutos regenera los datos y los guarda en el repo. La web (donde quiera que este alojada: FTP, CMS, etc.) carga el JS directamente desde el CDN gratuito jsDelivr, que sirve los ficheros del repo. No hace falta ninguna maquina encendida, ningun FTP ni ninguna credencial.

Flujo (`.github/workflows/actualizar-mundial-2026.yml`):

1. `python3 actualizar_mundial_2026.py --compact` genera `data/mundial_2026_clubes.js` y `.json`.
2. Hace commit de esos ficheros en el repo.
3. Refresca la cache del CDN jsDelivr para que la nueva version se sirva enseguida.

Sondea cada 15 minutos en la franja de partidos (16:00-03:59 UTC) mas una pasada de seguridad a las 05:15 UTC. En la practica los datos quedan disponibles en el CDN unos 15 minutos despues de que termine un partido de un jugador del FCB/RM y la fuente lo publique. Al sondear de forma continua, los retrasos, aplazamientos y prorrogas se cubren solos.

### Puesta en marcha (una sola vez)

En el HTML del especial, carga el JS desde el CDN del repositorio:

```html
<script src="https://cdn.jsdelivr.net/gh/MD-MundoDeportivo/especial-mundial-2026-fcb-rm@main/data/mundial_2026_clubes.js"></script>
```

La variable disponible sera:

```js
MUNDIAL_2026_CLUBES
```

Sube ese HTML a tu FTP/CMS como hagas siempre. Ya no necesitas subir la carpeta `data/` al FTP: el JS viene del CDN y se actualiza solo. Para comprobar que el robot funciona, lanza el workflow a mano desde `Actions > Actualizar datos Mundial 2026 > Run workflow`.

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
