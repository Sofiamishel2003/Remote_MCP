import asyncio
import logging
import os
from datetime import datetime

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("MCP Server on Cloud Run", disable_sessions=True)

mcp_app = mcp.http_app(path='/')  

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

@mcp.tool()
def zodiac_sign(birthdate: str) -> str:
    dt = datetime.strptime(birthdate, "%Y-%m-%d")
    return _calc_zodiac(dt.month, dt.day)
@mcp.tool()
def add(a: int, b: int) -> int:
    """Use this to add two numbers together.
    
    Args:
        a: The first number.
        b: The second number.
    
    Returns:
        The sum of the two numbers.
    """
    logger.info(f">>> Tool: 'add' called with numbers '{a}' and '{b}'")
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Use this to subtract two numbers.
    
    Args:
        a: The first number.
        b: The second number.
    
    Returns:
        The difference of the two numbers.
    """
    logger.info(f">>> Tool: 'subtract' called with numbers '{a}' and '{b}'")
    return a - b
@app.route("/")
async def homepage(request):
    return PlainTextResponse(
        "Bienvenid@ a mi MCP Server en Cloud Run.\n\n"
        "Herramientas:\n"
        "- add(a, b)\n"
        "- subtract(a, b)\n"
        "- zodiac_sign(birthdate: 'YYYY-MM-DD')\n\n"
        "Usa /mcp para el protocolo MCP (streamable-http)."
    )

# Monta el MCP en /mcp  -> endpoints: /mcp  y /mcp/ (ambos deberían responder)
app.mount("/mcp", mcp_app)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"MCP server started on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
