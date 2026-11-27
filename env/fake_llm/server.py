# =============================================
# Imports
# ---------------------------------------------
import json
import logging
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# =============================================
# Configuracion
# ---------------------------------------------
# Servidor falso compatible con la API de chat de OpenRouter (formato OpenAI).
# Reemplaza al LLM real en el ambiente QA local: no gasta credito ni sale a internet.
PORT = int(os.environ.get("FAKE_LLM_PORT", "8080"))
DELAY_MS = int(os.environ.get("FAKE_LLM_DELAY_MS", "0"))
FORCE_ERROR_MARKER = "QA_FORCE_LLM_ERROR"
FORCE_INVALID_JSON_MARKER = "QA_FORCE_INVALID_JSON"
PROTECTION_BY_CATEGORY = {
    "fungus": "fungicida",
    "hongos": "fungicida",
    "pests": "insecticida",
    "plagas": "insecticida",
    "weeds": "herbicida",
    "malezas": "herbicida",
    "bacteria": "otro",
    "bacterias": "otro",
    "nematodes": "otro",
    "nematodos": "otro",
    "drought": "fertilizante",
    "sequía": "fertilizante",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fake_llm")


# =============================================
# Respuestas por agente
# ---------------------------------------------
# Lee un campo "- Nombre: valor" del prompt del analizador
def read_prompt_field(user_prompt, field_name):
    match = re.search(r"- " + re.escape(field_name) + r":\s*(.+)", user_prompt)
    if match is None:
        return "no especificado"
    return match.group(1).strip()


# Arma la salida del agente analizador a partir de los datos del formulario
def build_analyzer_response(user_prompt):
    crop = read_prompt_field(user_prompt, "Cultivo")
    problem = read_prompt_field(user_prompt, "Problema")
    category = read_prompt_field(user_prompt, "Categoría del problema").lower()
    protection = "otro"
    for key, value in PROTECTION_BY_CATEGORY.items():
        if key in category or key in problem.lower():
            protection = value
            break
    product_category = "plaguicida"
    if protection == "fertilizante":
        product_category = "fertilizante"
    summary = (
        "Cultivo de "
        + crop
        + " con problema de "
        + problem
        + " en etapa "
        + read_prompt_field(user_prompt, "Etapa")
        + ". Se buscan productos de tipo "
        + protection
        + " registrados y activos, compatibles con el cultivo, con banda toxicologica"
        + " baja cuando sea posible y respetando el intervalo de seguridad antes de la"
        + " cosecha. Respuesta generada por el LLM falso del ambiente QA local."
    )
    return {
        "cultivo": crop,
        "problema_detectado": problem,
        "condiciones_agronomicas": {
            "tipo_suelo": read_prompt_field(user_prompt, "Tipo de suelo"),
            "humedad": read_prompt_field(user_prompt, "Humedad"),
            "temperatura": read_prompt_field(user_prompt, "Temperatura"),
            "calidad_agua": read_prompt_field(user_prompt, "Calidad del agua"),
        },
        "severidad_estimada": "media",
        "restricciones_relevantes": [],
        "resumen_para_rag": summary,
        "advertencias": [],
        "datos_faltantes": [],
        "confianza": 0.8,
        "tipo_proteccion_necesaria": protection,
        "categoria_producto_sugerida": product_category,
    }


# Extrae los ids de producto que vienen en el JSON del prompt
def read_product_ids(user_prompt):
    product_ids = []
    for match in re.finditer(r'"product_id":\s*(\d+)', user_prompt):
        product_id = int(match.group(1))
        if product_id not in product_ids:
            product_ids.append(product_id)
    return product_ids


# Confirma como validos todos los candidatos que sobrevivieron a las reglas duras
def build_legal_response(user_prompt):
    return {
        "productos_validos_ids": read_product_ids(user_prompt),
        "descartes": [],
        "restricciones_detectadas": [],
        "nivel_riesgo_legal": "bajo",
        "advertencias_legales": [],
        "confianza": 0.8,
        "normativa_insuficiente": False,
    }


# Genera el texto de justificacion para cada producto recibido
def build_synthesizer_response(user_prompt):
    items = []
    for product_id in read_product_ids(user_prompt):
        items.append(
            {
                "product_id": product_id,
                "justificacion": "Producto compatible con el caso (texto del LLM falso).",
                "ventajas": ["Registrado y activo"],
                "riesgos": ["Respetar la dosis y el intervalo de seguridad"],
                "recomendacion_uso_general": "Aplicar segun la etiqueta del producto.",
            }
        )
    return {"items": items}


# Decide que agente hizo la llamada y devuelve su respuesta
def build_agent_response(system_prompt, user_prompt):
    if "ContextAnalysisOutput" in system_prompt:
        return "analyzer", build_analyzer_response(user_prompt)
    if "_LegalLLMReview" in system_prompt:
        return "legal_validator", build_legal_response(user_prompt)
    if "_SynthesisLLMResponse" in system_prompt:
        return "synthesizer", build_synthesizer_response(user_prompt)
    return "unknown", {"respuesta": "texto del LLM falso"}


# =============================================
# Servidor HTTP
# ---------------------------------------------
class FakeLLMHandler(BaseHTTPRequestHandler):
    # Responde el health check del contenedor
    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        self.send_json(404, {"error": "not found"})

    # Atiende POST /v1/chat/completions con el formato de OpenAI
    def do_POST(self):
        if not self.path.endswith("/chat/completions"):
            self.send_json(404, {"error": "not found"})
            return

        # Se lee el cuerpo y se separan los mensajes de sistema y de usuario
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        system_prompt = ""
        user_prompt = ""
        for message in body.get("messages", []):
            if message.get("role") == "system":
                system_prompt = system_prompt + str(message.get("content", ""))
            if message.get("role") == "user":
                user_prompt = user_prompt + str(message.get("content", ""))

        # Latencia simulada para aislar el tiempo propio del sistema en pruebas de carga
        if DELAY_MS > 0:
            time.sleep(DELAY_MS / 1000)

        # Fallas inducidas para las pruebas de fiabilidad
        if FORCE_ERROR_MARKER in user_prompt:
            logger.info("Forced error requested")
            self.send_json(500, {"error": {"message": "Forced error for QA"}})
            return
        agent_name, payload = build_agent_response(system_prompt, user_prompt)
        content = json.dumps(payload, ensure_ascii=False)
        if FORCE_INVALID_JSON_MARKER in user_prompt:
            content = "this is not valid JSON"

        logger.info("Answered agent=%s", agent_name)
        self.send_json(
            200,
            {
                "id": "chatcmpl-fake-" + str(int(time.time() * 1000)),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", "fake-llm"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            },
        )

    # Envia una respuesta JSON con el codigo indicado
    def send_json(self, status_code, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    # Redirige el log de cada peticion al logger del modulo
    def log_message(self, format, *args):
        logger.debug(format, *args)


# =============================================
# Punto de entrada
# ---------------------------------------------
# Levanta el servidor en el puerto configurado
def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), FakeLLMHandler)
    logger.info("Fake LLM listening on port %s (delay %s ms)", PORT, DELAY_MS)
    server.serve_forever()


if __name__ == "__main__":
    main()
