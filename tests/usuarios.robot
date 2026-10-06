*** Settings ***
Documentation    Flujos de usuarios contra Demo Users API; un HTML por test.

Resource         ../resources/services/usuarios.resource
Resource         ../resources/assertions/usuarios.resource

Suite Setup      Esperar disponibilidad de la API
Test Setup       Preparar datos del test
Test Teardown    Limpiar usuarios creados


*** Test Cases ***
USR-001 Crear actualizar y eliminar usuario
    ${response}    ${request_id}=    Crear usuario    Angel Demo    ${TEST_EMAIL}    sales
    Verificar código HTTP    ${request_id}    ${response}    201
    VAR    ${user_id}    ${response.json()}[id]
    ${response}    ${request_id}=    Consultar usuario    ${user_id}
    Verificar código HTTP    ${request_id}    ${response}    200
    Verificar correo de usuario    ${request_id}    ${response}    ${TEST_EMAIL}
    ${response}    ${request_id}=    Buscar usuarios    sales    10
    Verificar código HTTP    ${request_id}    ${response}    200
    Assert And Log    ${request_id}    Verificar resultado de búsqueda
    ...    Should Not Be Empty    ${response.json()}[items]
    ${response}    ${request_id}=    Reemplazar usuario    ${user_id}    Angel Actualizado    ${TEST_EMAIL}
    Verificar código HTTP    ${request_id}    ${response}    200
    Verificar rol de usuario    ${request_id}    ${response}    support
    ${response}    ${request_id}=    Desactivar usuario    ${user_id}
    Verificar código HTTP    ${request_id}    ${response}    200
    Verificar usuario desactivado    ${request_id}    ${response}
    ${response}    ${request_id}=    Eliminar usuario    ${user_id}
    Verificar código HTTP    ${request_id}    ${response}    204
    ${response}    ${request_id}=    Consultar usuario    ${user_id}
    Verificar código HTTP    ${request_id}    ${response}    404

USR-002 Rechazar correo duplicado
    ${response}    ${request_id}=    Crear usuario    Demo Original    ${TEST_EMAIL}
    Verificar código HTTP    ${request_id}    ${response}    201
    ${response}    ${request_id}=    Crear usuario    Demo Duplicado    ${TEST_EMAIL}
    Verificar código HTTP    ${request_id}    ${response}    409

USR-003 Mostrar una assertion fallida
    [Tags]    expected-failure
    Set Case Metadata    test_id=USR-003    environment=demo
    ${response}    ${request_id}=    Crear usuario    Demo Fallido    ${TEST_EMAIL}    sales
    Verificar código HTTP    ${request_id}    ${response}    201
    Verificar rol de usuario    ${request_id}    ${response}    admin

USR-004 Escenario pendiente
    Skip    Carga de avatar fuera del alcance actual.

USR-005 Desactivar reactivar y comprobar estadísticas
    ${response}    ${request_id}=    Consultar estadísticas
    Verificar código HTTP    ${request_id}    ${response}    200
    VAR    ${initial_total}    ${response.json()}[total]
    VAR    ${initial_inactive}    ${response.json()}[inactive]
    ${response}    ${request_id}=    Crear usuario    Lifecycle Demo    ${TEST_EMAIL}    sales
    Verificar código HTTP    ${request_id}    ${response}    201
    VAR    ${user_id}    ${response.json()}[id]
    ${response}    ${request_id}=    Cambiar estado de usuario    ${user_id}    deactivate
    Verificar código HTTP    ${request_id}    ${response}    200
    Verificar usuario desactivado    ${request_id}    ${response}
    ${response}    ${request_id}=    Cambiar estado de usuario    ${user_id}    deactivate
    Verificar código HTTP    ${request_id}    ${response}    409
    ${response}    ${request_id}=    Consultar estadísticas
    Verificar código HTTP    ${request_id}    ${response}    200
    ${expected}=    Evaluate    int($initial_inactive) + 1
    Assert And Log    ${request_id}    Usuario incluido en estadísticas
    ...    Should Be Equal As Integers    ${response.json()}[inactive]    ${expected}
    ${response}    ${request_id}=    Cambiar estado de usuario    ${user_id}    activate
    Verificar código HTTP    ${request_id}    ${response}    200
    Assert And Log    ${request_id}    Usuario reactivado
    ...    Should Be Equal    ${response.json()}[active]    ${TRUE}
    ${response}    ${request_id}=    Cambiar estado de usuario    ${user_id}    activate
    Verificar código HTTP    ${request_id}    ${response}    409
    ${response}    ${request_id}=    Eliminar usuario    ${user_id}
    Verificar código HTTP    ${request_id}    ${response}    204
    ${response}    ${request_id}=    Consultar estadísticas
    Verificar código HTTP    ${request_id}    ${response}    200
    Assert And Log    ${request_id}    Estadísticas restauradas
    ...    Should Be Equal As Integers    ${response.json()}[total]    ${initial_total}

USR-006 Rechazar datos inválidos sin crear usuarios
    VAR    &{body}    name=${EMPTY}    email=not-an-email    role=unknown
    ${response}    ${request_id}=    Enviar request de usuario    POST    /users    ${body}
    Verificar código HTTP    ${request_id}    ${response}    422
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users/not-a-uuid
    Verificar código HTTP    ${request_id}    ${response}    422
    VAR    &{params}    limit=${0}
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users    params=${params}
    Verificar código HTTP    ${request_id}    ${response}    422

USR-007 Rechazar acceso sin credenciales
    ${response}=    GET    ${BASE_URL}/users/statistics    expected_status=anything    timeout=${HTTP_TIMEOUT}
    ${request_id}=    Capture And Log Response    Estadísticas sin credenciales    ${response}
    Verificar código HTTP    ${request_id}    ${response}    401
    VAR    &{headers}    X-API-Key=invalid-demo-credential
    ${response}=    GET    ${BASE_URL}/users    headers=${headers}
    ...    expected_status=anything    timeout=${HTTP_TIMEOUT}
    ${request_id}=    Capture And Log Response    Credencial inválida    ${response}
    Verificar código HTTP    ${request_id}    ${response}    401

USR-008 Comprobar paginación y filtros después de modificar usuarios
    ${response}    ${request_id}=    Crear usuario    Pagination A    a-${TEST_EMAIL}    sales
    Verificar código HTTP    ${request_id}    ${response}    201
    VAR    ${first_id}    ${response.json()}[id]
    ${response}    ${request_id}=    Crear usuario    Pagination B    b-${TEST_EMAIL}    sales
    Verificar código HTTP    ${request_id}    ${response}    201
    ${response}    ${request_id}=    Desactivar usuario    ${first_id}
    Verificar código HTTP    ${request_id}    ${response}    200
    VAR    &{params}    active=${FALSE}    role=sales    limit=${1}    offset=${0}
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users    params=${params}
    Verificar código HTTP    ${request_id}    ${response}    200
    Assert And Log    ${request_id}    Filtro devuelve el usuario desactivado
    ...    Should Be Equal    ${response.json()}[items][0][id]    ${first_id}
    VAR    &{params}    role=sales    limit=${1}    offset=${1}
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users    params=${params}
    Verificar código HTTP    ${request_id}    ${response}    200
    Assert And Log    ${request_id}    Paginación conserva el límite
    ...    Length Should Be    ${response.json()}[items]    1
