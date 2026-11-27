# =============================================
# Imports
# ---------------------------------------------
import os
import sys
from pathlib import Path

import pytest

# =============================================
# Constantes
# ---------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent / "synapseed" / "src" / "backend"
MARKED_TYPES = ["unit", "integration", "security", "performance"]
# 127.0.0.1 y no localhost: en Windows localhost intenta IPv6 primero y agrega ~2 s por peticion
DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1"

# =============================================
# Ruta al codigo auditado
# ---------------------------------------------
# Se agrega el backend del submodulo al path para poder importar app.*
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =============================================
# Hooks
# ---------------------------------------------
# Marca cada prueba con su tipo segun la carpeta tests/<area>/<tipo>/
def pytest_collection_modifyitems(config, items):
    for item in items:
        # Se toma la ruta relativa a tests/ para leer el tipo
        relative_parts = Path(item.path).resolve().relative_to(TESTS_DIR).parts
        if len(relative_parts) < 3:
            continue
        test_type = relative_parts[1]
        if test_type in MARKED_TYPES:
            item.add_marker(getattr(pytest.mark, test_type))


# =============================================
# Fixtures compartidas
# ---------------------------------------------
# URL base de la API del ambiente bajo prueba, configurable con QA_API_URL
@pytest.fixture(scope="session")
def api_base_url():
    return os.environ.get("QA_API_URL", DEFAULT_API_URL)
