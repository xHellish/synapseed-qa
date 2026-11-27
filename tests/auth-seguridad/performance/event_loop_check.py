# =============================================
# Diagnostico de PERF-01: los logins bloquean al backend
# ---------------------------------------------
# Mide el catalogo de cultivos (sin token ni bcrypt) solo y mientras 10 hilos
# hacen logins seguidos. Si la mediana sube cerca de 10 x el tiempo de un login,
# bcrypt corre de forma sincrona dentro del event loop y serializa todo el backend.
# Uso, desde la raiz del repo con el ambiente QA arriba:
#   synapseed\src\backend\.venv\Scripts\python tests/auth-seguridad/performance/event_loop_check.py

# =============================================
# Imports
# ---------------------------------------------
import json
import os
import random
import statistics
import threading
import time
import urllib.error
import urllib.request

# =============================================
# Constantes
# ---------------------------------------------
BASE_URL = os.environ.get("QA_API_URL", "http://127.0.0.1:8000/api/v1")
SAMPLES = 20
LOGIN_THREADS = 10
WARMUP_SECONDS = 1


# =============================================
# Funciones
# ---------------------------------------------
# Envia un POST JSON y devuelve el codigo HTTP
def post_json(path, body):
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


# Mide en milisegundos un GET al catalogo de cultivos
def timed_catalog_read():
    started = time.perf_counter()
    with urllib.request.urlopen(BASE_URL + "/catalogs/crops", timeout=60) as response:
        response.read()
    return (time.perf_counter() - started) * 1000


# Toma varias mediciones seguidas del catalogo
def sample_catalog_reads():
    durations = []
    for _ in range(SAMPLES):
        durations.append(timed_catalog_read())
    return durations


# Registra un usuario sintetico (cedula que empieza en 7) y devuelve sus credenciales
def create_user():
    identification = "7"
    for _ in range(8):
        identification = identification + str(random.randint(0, 9))
    password = "QaLoop-" + identification
    user = {
        "email": "qa.loop." + identification + "@example.com",
        "full_name": "Persona Diagnostico",
        "identification": identification,
        "phone": "88880000",
        "password": password,
    }
    status = post_json("/auth/register", user)
    if status != 201:
        raise RuntimeError("Could not register diagnostic user: " + str(status))
    return {"identification": identification, "password": password}


# Hace logins seguidos hasta que se pida parar
def login_loop(credentials, stop_event):
    while not stop_event.is_set():
        post_json("/auth/login", credentials)


# Ejecuta el diagnostico y muestra las tres mediciones
def main():
    credentials = create_user()

    # Linea base: catalogo sin carga
    baseline = sample_catalog_reads()
    print(
        "Catalog alone: median %.1f ms, max %.1f ms"
        % (statistics.median(baseline), max(baseline))
    )

    # Costo de un login aislado
    started = time.perf_counter()
    post_json("/auth/login", credentials)
    print("Single login: %.0f ms" % ((time.perf_counter() - started) * 1000))

    # Catalogo mientras varios hilos hacen logins
    stop_event = threading.Event()
    threads = []
    for _ in range(LOGIN_THREADS):
        thread = threading.Thread(target=login_loop, args=(credentials, stop_event))
        thread.start()
        threads.append(thread)
    time.sleep(WARMUP_SECONDS)
    under_load = sample_catalog_reads()
    stop_event.set()
    for thread in threads:
        thread.join()
    print(
        "Catalog during %d concurrent logins: median %.1f ms, max %.1f ms"
        % (LOGIN_THREADS, statistics.median(under_load), max(under_load))
    )


main()
