# Evidencias reales de preparación local

Fecha: 06/11/2026. Python 3.12.14, Linux.

| Comprobación | Resultado real | Evidencia |
|---|---|---|
| Suite pytest | 269 aprobadas, 1 omitida, 0 fallos | pytest.log y junit.xml |
| Cobertura de src, líneas y ramas | 97.39%, umbral 80% | coverage.json, coverage.xml, htmlcov/index.html |
| Líneas ejecutadas | 870/882 | coverage.json |
| Ramas ejecutadas | 211/228 | coverage.json |
| Casos CSV | 120 comparados, 0 diferencias | resultados_120_casos.csv |
| Transiciones CSV | 20 comparadas, 0 diferencias | resultados_20_transiciones.csv |
| API con Uvicorn y HTTP real | 20 peticiones, todas con código esperado | demo_http.json |
| Ruff check y format --check | PASS | ruff.log |
| Persistencia SQLite | commit, reapertura, rollback y CAS aprobados | pruebas y junit.xml |
| PostgreSQL | NO EJECUTADO: servicio no disponible | prueba marcada SKIP |
| Docker Compose | Configuración preparada, no ejecutada en este entorno | docker-compose.yml |
| GitHub Actions | Workflow preparado, sin ejecución remota del PIA | .github/workflows/ci.yml |
| URL pública | Pendiente de repositorio/plataforma | DESPLIEGUE.md |

Los 140 ensayos CSV forman parte de las 269 pruebas aprobadas; no se suman otra vez al total. La prueba de HTTP externo sí se ejecutó contra un servidor real. Las pruebas unitarias e integración usan además TestClient y SQLite. La advertencia de deprecación registrada procede de Starlette/AnyIO y no afectó el resultado.

La evidencia HTTP registra roles, rutas, códigos y datos ficticios. Excluye las cabeceras de autenticación. Se verificaron rechazo 409 por aceptación duplicada, 422 por adicional sin pago, 422 por cierre con saldo y cierre final correcto.

La cobertura no demuestra ejecución de todas las plataformas ni acredita mejoras comerciales. No hay capturas simuladas de Actions, Docker o producción.

## Ejecución remota de GitHub Actions

El 06/11/2026 se completó [Actions #1](https://github.com/OmarHub-star/PIA-Eventos-Nova/actions/runs/42314931852) sobre el commit `9fb4b061f4af1b2713ccfb8cfbe313578bf0368e`, con Python 3.12.16. Estos resultados posteriores complementan la preparación local anterior:

| Job | Resultado verificado en sus logs |
|---|---|
| quality | Ruff y formato aprobados; 269 pruebas aprobadas y 1 omitida porque no configura API externa; PostgreSQL ejecutado; cobertura 97.48%; evaluador CSV aprobado |
| containers | Docker Compose construyó App y Tests, conectó PostgreSQL 16 y ejecutó 270 pruebas, sin omisiones, con 97.48% de cobertura; salida 0 |
| deploy | Job completado; llamada de despliegue omitida por falta de RENDER_DEPLOY_HOOK; no acredita publicación |

La aplicación todavía no está publicada. Render pudo acceder al espacio confirmado por el usuario, pero rechazó la lectura del repositorio privado. Falta vincular GitHub a Render con permiso para PIA-Eventos-Nova. No se crearon servicios ni bases de datos durante ese intento.
