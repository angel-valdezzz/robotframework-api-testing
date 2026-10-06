# Robot Framework API Testing

Flujos de negocio contra **Demo Users API**, con RequestsLibrary, **RequestReporter 0.6.0** y **RequestLogger 0.1.0**. Cada test genera un HTML independiente, sin conexión y adjuntable a Jira.

[Swagger de la API](https://angel-valdezzz.github.io/demo-users-api/) · [Proyecto de la API](https://github.com/angel-valdezzz/demo-users-api) · [Manual de RequestReporter](https://angel-valdezzz.github.io/robotframework-request-reporter/) · [Keywords](https://angel-valdezzz.github.io/robotframework-request-reporter/keywords/) · [Manual de RequestLogger](https://angel-valdezzz.github.io/robotframework-request-logger/)

## Ejecutar contra la API desplegada

Python 3.12+ y Poetry 2.5.1. Configura la URL y tu credencial **fuera del código**.

```powershell
poetry install --only main
$env:DEMO_BASE_URL = 'https://TU-SERVICIO.onrender.com'
$env:DEMO_API_KEY = 'TU_CREDENCIAL_PRIVADA'
poetry run python scripts/run_demo.py
```

En Bash usa `export DEMO_BASE_URL=...` y `export DEMO_API_KEY=...`. El servicio requiere una API key autorizada. No guardes estos valores en archivos versionados. La URL final se asigna al crear el servicio en Render; el despliegue inicial requiere configurar su cuenta.

En Windows también puedes ejecutar `scripts/run_demo.bat` después de configurar las variables; acepta argumentos como `--logger-mode full` o `--local`.

El Suite Setup consulta `/health`, que despierta Render automáticamente, y espera hasta aproximadamente dos minutos, con consultas cada cinco segundos y timeout de cinco segundos por intento. Si no arranca, los tests muestran el fallo del setup. Los requests de negocio conservan timeout de 15 segundos. El servicio gratuito reinicia sus datos después de suspenderse: los tests crean sus propios usuarios y los limpian en teardown, incluso si una assertion falla.

## Verificar sin credenciales externas

```bash
poetry install
poetry run python scripts/run_demo.py --local
```

`--local` inicia **el proyecto FastAPI independiente** instalado como dependencia de desarrollo y fijado a un commit en Poetry. No contiene una API inventada dentro del runner. Genera una credencial temporal para esa ejecución. CI usa esta opción para que una suspensión o caída de Render no bloquee un pull request.

## Escenarios

| Test | Resultado esperado | Cobertura |
|---|---|---|
| USR-001 | PASS | POST, GET por ID, GET con query params, PUT, PATCH, DELETE y GET 404 |
| USR-002 | PASS | Correo duplicado y HTTP 409 esperado |
| USR-003 | FAIL intencional | Rol sales comparado con admin; evidencia del fallo |
| USR-004 | SKIP | Escenario completo pendiente; no assertions SKIP |
| USR-005 | PASS | Activación, desactivación, conflictos 409 y estadísticas |
| USR-006 | PASS | Payload, UUID y paginación inválidos (422) |
| USR-007 | PASS | Credenciales ausentes o inválidas (401) |
| USR-008 | PASS | Filtros combinados, paginación y usuarios inactivos |
| USR-DDT Soporte / Ventas | PASS | DataDriver y roles de usuario |

El runner verifica estos resultados; un fallo diferente hace fallar la ejecución. Guarda ocho HTML en `results/cases/`, dos en `results-ddt/cases/`, logs de Robot y `console.log`. Regenera solamente esos dos directorios conocidos. Un HTTP 409/404 esperado no convierte una assertion en FAIL.

## Payloads con Paylo

Paylo 0.1.0 carga las plantillas JSON de `data/payloads/`. Los datos del escenario o DataDriver se pasan explícitamente como variables; los payloads de POST, PUT y PATCH no se construyen por concatenación de texto.

```json
{"name": "{{name}}", "email": "{{email}}", "role": "{{role}}"}
```

```robotframework
Library    Paylo

VAR    &{values}    name=Ana    email=ana@example.com    role=support
${body}=    Render JSON File    ${CURDIR}/data/payloads/create-user.json    ${values}
```

La desactivación usa `active=${FALSE}`: Paylo conserva el booleano JSON, no el texto `"False"`. Los parámetros de consulta siguen siendo diccionarios normales.

## Idioma de los reportes

La interfaz se genera en inglés por defecto. Para español:

```bash
poetry run python scripts/run_demo.py --local --language es
```

El idioma no traduce los datos de la API ni los nombres de los casos.

## Consola

```bash
poetry run python scripts/run_demo.py --logger-mode summary --console none
poetry run python scripts/run_demo.py --logger-mode failures --console none
poetry run python scripts/run_demo.py --logger-mode full --console none
```

Añade `--local` para la API de desarrollo. El modo predeterminado es summary con consola Robot quiet. Los errores nativos siguen visibles. `full` muestra los bodies completos; `failures` muestra los intercambios con assertions fallidas o errores registrados.

## Arquitectura y evidencia

- `tests/`: flujos completos y DataDriver.
- `resources/services/usuarios.resource`: RequestsLibrary, captura de una misma response en reporter/logger y limpieza.
- `resources/assertions/usuarios.resource`: assertions de negocio.
- `resources/config/http.resource`: URL, timeout y modo de consola.
- `resources/assertions/ConsoleAssertions.py`: vincula IDs independientes; cada assertion se ejecuta una sola vez.
- `data/usuarios.csv`: roles para DataDriver.
- `scripts/run_demo.py`: ejecución y verificación, sin implementar endpoints HTTP.
- `examples/report.html`: HTML real de la nueva demo.

Reporter y Logger ocultan `X-API-Key`. Además, el runner procesa la salida en un directorio temporal y reemplaza la credencial en **todos** los archivos publicados, incluyendo `output.xml`, `log.html` y la consola. Publica solo después de terminar Robot. Usa este runner con credenciales reales: ejecutar `robot` directamente conserva los logs propios de Robot/RequestsLibrary y no aplica esta protección adicional. Una interrupción forzada del proceso no garantiza limpieza del directorio temporal; no publiques esos archivos intermedios.

## GitHub Actions

CI ejecuta lint, formato, Robot y verificación local. **Live users API demo** es un workflow manual para el servicio desplegado. Configura en Settings → Secrets and variables → Actions:

| Tipo | Nombre | Valor |
|---|---|---|
| Variable | `DEMO_BASE_URL` | URL HTTPS del servicio |
| Secret | `DEMO_API_KEY` | Credencial autorizada para Actions |

El workflow usa el runner y sube únicamente resultados procesados. No se envían credenciales de Render a los tests. La integración externa queda lista para ejecutarse cuando el servicio esté desplegado y estos valores estén configurados.

## Última ejecución publicada

[Abrir últimos reportes](https://angel-valdezzz.github.io/robotframework-api-testing/) · [Descargar ZIP](https://angel-valdezzz.github.io/robotframework-api-testing/reports.zip)

El workflow de CI ejecuta el proyecto API real en local en push a main, pull request o ejecución manual. Las ejecuciones de main publican una página con fecha, commit, estado de validación, HTML por caso y logs Robot. Incluye el FAIL intencional descrito arriba.

Cada publicación válida sustituye la anterior en Pages. El ZIP permanece disponible en esa página; el artefacto de Actions de main caduca a los 7 días y los anteriores del mismo workflow se eliminan después de publicar el nuevo. Los PR conservan su artefacto durante 1 día y no publican en Pages. Si no hay reportes válidos, se conserva la publicación anterior. Los archivos generados no se añaden al historial Git.
