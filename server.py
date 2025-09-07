import asyncio
import json
import logging
import os
from datetime import datetime

from fastmcp import FastMCP 
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Herramientas -------------------------------
# Signo zodiacal basado en fecha
def _calc_zodiac(month: int, day: int) -> str:
    ranges = [
        ("Capricornio", (12, 22), (1, 19)),
        ("Acuario",     (1, 20),  (2, 18)),
        ("Piscis",      (2, 19),  (3, 20)),
        ("Aries",       (3, 21),  (4, 19)),
        ("Tauro",       (4, 20),  (5, 20)),
        ("Géminis",     (5, 21),  (6, 20)),
        ("Cáncer",      (6, 21),  (7, 22)),
        ("Leo",         (7, 23),  (8, 22)),
        ("Virgo",       (8, 23),  (9, 22)),
        ("Libra",       (9, 23),  (10, 22)),
        ("Escorpio",    (10, 23), (11, 21)),
        ("Sagitario",   (11, 22), (12, 21)),
    ]
    for name, (sm, sd), (em, ed) in ranges:
        if sm <= em:
            if (month > sm or (month == sm and day >= sd)) and \
               (month < em or (month == em and day <= ed)):
                return name
        else:
            if (month > sm or (month == sm and day >= sd)) or \
               (month < em or (month == em and day <= ed)):
                return name
    return "Desconocido"

def tool_zodiac_sign(birthdate: str) -> str:
    dt = datetime.strptime(birthdate, "%Y-%m-%d")
    return _calc_zodiac(dt.month, dt.day)
# Suma y resta del ejemplo básico
def tool_add(a: int, b: int) -> int:
    return a + b

def tool_subtract(a: int, b: int) -> int:
    return a - b

TOOLS = {
    "zodiac_sign": {
        "func": tool_zodiac_sign,
        "schema": {
            "type": "object",
            "properties": {
                "birthdate": {"type": "string", "description": "YYYY-MM-DD"}
            },
            "required": ["birthdate"],
            "additionalProperties": False
        },
        "description": "Calcula el signo zodiacal a partir de YYYY-MM-DD"
    },
    "add": {
        "func": tool_add,
        "schema": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            "required": ["a", "b"],
            "additionalProperties": False
        },
        "description": "Suma dos números"
    },
    "subtract": {
        "func": tool_subtract,
        "schema": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            "required": ["a", "b"],
            "additionalProperties": False
        },
        "description": "Resta dos números"
    },
}

# Shim sin sesiones -----------------------
# Acepta JSON-RPC con métodos: tools/list, tools/call
app = Starlette()

@app.route("/", methods=["GET"])
async def root(_request: Request):
    return PlainTextResponse(
        "Bienvenid@ a mi MCP Server en Cloud Run.\n\n"
        "Herramientas:\n"
        "- add(a, b)\n"
        "- subtract(a, b)\n"
        "- zodiac_sign(birthdate: 'YYYY-MM-DD')\n\n"
    )

@app.route("/mcp", methods=["POST"])
async def mcp_shim(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc":"2.0","id":"server-error",
                             "error":{"code":-32700,"message":"Parse error"}},
                            status_code=400)

    def error(id_, code, message):
        return JSONResponse({"jsonrpc":"2.0","id":id_,
                             "error":{"code":code,"message":message}}, status_code=400)

    if not isinstance(payload, dict):
        return error(None, -32600, "Invalid Request")

    jsonrpc = payload.get("jsonrpc")
    method  = payload.get("method")
    req_id  = payload.get("id")
    params  = payload.get("params", {})

    if jsonrpc != "2.0" or not isinstance(method, str):
        return error(req_id, -32600, "Invalid Request")

    # tools/list
    if method == "tools/list":
        tools_list = []
        for name, meta in TOOLS.items():
            tools_list.append({
                "name": name,
                "description": meta["description"],
                "inputSchema": meta["schema"],
            })
        return JSONResponse({"jsonrpc":"2.0","id":req_id,"result":{"tools": tools_list}})

    # tools/call
    if method == "tools/call":
        if not isinstance(params, dict):
            return error(req_id, -32602, "Invalid params")
        name = (params.get("name") or "").strip()
        args = params.get("arguments", {})
        meta = TOOLS.get(name)
        if not meta:
            return error(req_id, -32601, f"Method not found: {name}")

        try:
            # Convertimos a kwargs seguros
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            result = meta["func"](**args)
            # Formato similar a MCP content (texto)
            content = [{"type":"text","text": str(result)}]
            return JSONResponse({"jsonrpc":"2.0","id":req_id,"result": content})
        except TypeError as e:
            return error(req_id, -32602, f"Invalid params: {e}")
        except ValueError as e:
            return error(req_id, -32602, f"Invalid params: {e}")
        except Exception as e:
            # Error interno
            return JSONResponse({"jsonrpc":"2.0","id":req_id,
                                 "error":{"code":-32603,"message":f"Internal error: {e}"}},
                                status_code=500)

    # método desconocido
    return error(req_id, -32601, f"Method not found: {method}")

# Para clientes MCP (seguirán la spec de sesiones)
mcp = FastMCP("MCP Server on Cloud Run")  # sin flags: respeta sesiones

@mcp.tool()
def zodiac_sign(birthdate: str) -> str:
    dt = datetime.strptime(birthdate, "%Y-%m-%d")
    return _calc_zodiac(dt.month, dt.day)

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    return a - b

# Montamos el ASGI del MCP real en /mcp-stream
# (usamos path='/' dentro de la sub-app y pasamos su lifespan a Starlette)
mcp_app = mcp.http_app(path="/")
app.router.mount("/mcp-stream", mcp_app)

# Arranque con Uvicorn -----------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"MCP server started on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
