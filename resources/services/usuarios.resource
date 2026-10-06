*** Settings ***
Library     RequestsLibrary
Library     Paylo
Library     Collections
Library     RequestReporter    language=${REPORT_LANGUAGE}    brand_config=${REPORT_BRAND_CONFIG}
Library     RequestLogger    mode=${LOGGER_MODE}
Library     ../assertions/ConsoleAssertions.py
Resource    ../config/http.resource


*** Variables ***
${REPORT_LANGUAGE}        en
${REPORT_BRAND_CONFIG}    ${NONE}


*** Keywords ***
Esperar disponibilidad de la API
    Wait Until Keyword Succeeds    2 minutes    5 seconds    Verificar disponibilidad de la API

Verificar disponibilidad de la API
    ${response}=    GET    ${BASE_URL}/health    expected_status=200    timeout=5
    Should Be Equal    ${response.json()}[status]    ok

Enviar request de usuario
    [Arguments]    ${method}    ${path}    ${body}=${NONE}    ${params}=${NONE}
    VAR    &{headers}    X-API-Key=%{DEMO_API_KEY}    Accept=application/json
    ${response}=    Run Keyword    ${method}    ${BASE_URL}${path}
    ...    headers=${headers}    json=${body}    params=${params}
    ...    expected_status=anything    timeout=${HTTP_TIMEOUT}
    ${request_id}=    Capture And Log Response    ${method} ${path}    ${response}
    RETURN    ${response}    ${request_id}

Crear usuario
    [Arguments]    ${name}    ${email}    ${role}=support
    VAR    &{values}    name=${name}    email=${email}    role=${role}
    ${body}=    Render JSON File    ${CURDIR}/../../data/payloads/create-user.json    ${values}
    ${response}    ${request_id}=    Enviar request de usuario    POST    /users    ${body}
    IF    ${response.status_code} == 201
        Append To List    ${CREATED_USERS}    ${response.json()}[id]
    END
    RETURN    ${response}    ${request_id}

Consultar usuario
    [Arguments]    ${user_id}
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users/${user_id}
    RETURN    ${response}    ${request_id}

Buscar usuarios
    [Arguments]    ${role}    ${limit}=20
    VAR    &{params}    role=${role}    limit=${limit}
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users    params=${params}
    RETURN    ${response}    ${request_id}

Reemplazar usuario
    [Arguments]    ${user_id}    ${name}    ${email}
    VAR    &{values}    name=${name}    email=${email}
    ${body}=    Render JSON File    ${CURDIR}/../../data/payloads/replace-user.json    ${values}
    ${response}    ${request_id}=    Enviar request de usuario    PUT    /users/${user_id}    ${body}
    RETURN    ${response}    ${request_id}

Desactivar usuario
    [Arguments]    ${user_id}
    VAR    &{values}    active=${FALSE}
    ${body}=    Render JSON File    ${CURDIR}/../../data/payloads/deactivate-user.json    ${values}
    ${response}    ${request_id}=    Enviar request de usuario    PATCH    /users/${user_id}    ${body}
    RETURN    ${response}    ${request_id}

Eliminar usuario
    [Arguments]    ${user_id}
    ${response}    ${request_id}=    Enviar request de usuario    DELETE    /users/${user_id}
    RETURN    ${response}    ${request_id}

Preparar datos del test
    VAR    @{CREATED_USERS}    scope=TEST
    ${unique}=    Evaluate    uuid.uuid4().hex    modules=uuid
    VAR    ${TEST_EMAIL}    demo-${unique}@example.com    scope=TEST

Limpiar usuarios creados
    FOR    ${user_id}    IN    @{CREATED_USERS}
        VAR    &{headers}    X-API-Key=%{DEMO_API_KEY}
        ${response}=    DELETE    ${BASE_URL}/users/${user_id}
        ...    headers=${headers}
        ...    expected_status=anything    timeout=${HTTP_TIMEOUT}
        IF    ${response.status_code} not in [204, 404]
            Fail    No se pudo limpiar el usuario ${user_id}: HTTP ${response.status_code}
        END
    END

Consultar estadísticas
    ${response}    ${request_id}=    Enviar request de usuario    GET    /users/statistics
    RETURN    ${response}    ${request_id}

Cambiar estado de usuario
    [Arguments]    ${user_id}    ${operation}
    Should Be True    $operation in ('activate', 'deactivate')
    ${response}    ${request_id}=    Enviar request de usuario    POST    /users/${user_id}/${operation}
    RETURN    ${response}    ${request_id}
