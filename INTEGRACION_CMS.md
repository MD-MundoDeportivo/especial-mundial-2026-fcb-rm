# Integracion en el especial

No hace falta ejecutar el script a mano.

## Como se actualiza

1. El codigo vive en el repositorio publico de GitHub (`MD-MundoDeportivo/especial-mundial-2026-fcb-rm`).
2. GitHub Actions ejecuta `.github/workflows/actualizar-mundial-2026.yml` cada 15 min en franja de partidos.
3. La accion descarga los CSV actualizados de `Bustami/efi-fifa-data-wc-2026`.
4. Regenera `data/mundial_2026_clubes.js` y hace commit en el repo.
5. Refresca la cache del CDN jsDelivr.
6. El CMS lee ese JS directamente del CDN. No hace falta FTP ni copia local del JSON.

## Archivo para el CMS

La web carga el JS directamente del repositorio publico via CDN jsDelivr (se actualiza solo):

```html
<script src="https://cdn.jsdelivr.net/gh/MD-MundoDeportivo/especial-mundial-2026-fcb-rm@main/data/mundial_2026_clubes.js"></script>
```

Dentro tendras:

```js
var MUNDIAL_2026_CLUBES = { ... };
```

## Datos que se actualizan solos

- Partidos jugados
- Goles
- Asistencias
- Minutos

Estos campos salen del CSV fuente.

En los totales de club, partidos, victorias, empates y derrotas se cuentan por partido unico de seleccion. Por ejemplo, si cinco jugadores del Barça juegan el mismo España-Cabo Verde, ese partido cuenta una sola vez en el total del club.

Los partidos futuros pendientes se exponen en `fixtures_pending`. No forman parte de `partidos jugados`, porque todavia no tienen aparicion de jugador en el CSV EFI.

## Datos que necesitan resultado de seleccion

- Victorias
- Empates
- Derrotas

Estos se cruzan desde `resultados_selecciones.csv`, porque el repositorio fuente no tiene marcadores. Si ese CSV tiene el resultado de la seleccion, tambien se actualizan en el JS final.

Mientras falten resultados, la comprobacion correcta es:

```txt
partidos = victorias + empates + derrotas + result_pending
```
