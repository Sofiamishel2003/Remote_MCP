# MCP Zodiac Server (Cloud Run)

A minimal **Model Context Protocol (MCP)** server that exposes:

* `zodiac_sign(birthdate: "YYYY-MM-DD")` → returns your Western zodiac sign
* `add(a, b)` and `subtract(a, b)` (simple math demo tools)

This repo includes:

* A **sessionless JSON-RPC shim** on `/mcp` so you can test easily with Postman/cURL (no session headers needed).
* A **spec-compliant MCP endpoint with sessions** on `/mcp-stream` for MCP clients.

The root path `/` serves a friendly “Welcome” page.

---

## Endpoints

| Path          | Purpose                                                        |
| ------------- | -------------------------------------------------------------- |
| `/`           | Welcome page with a short description                          |
| `/mcp`        | **Stateless JSON-RPC shim**: `tools/list`, `tools/call`        |
| `/mcp-stream` | **MCP streamable-http** (spec-compliant, **requires session**) |

**Available tools**

* `zodiac_sign(birthdate: "YYYY-MM-DD")` → returns one of: Capricorn, Aquarius, Pisces, Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius (in Spanish labels by default)
* `add(a: int, b: int)`
* `subtract(a: int, b: int)`

---

## Quick Start (Local)

### Prerequisites

* Python 3.10+
* One of:

  * **uv** (recommended)
  * or `pip`

### Install & run (uv)

```bash
# install deps defined in pyproject.toml
uv sync
# run
uv run server.py
# server listens on PORT=8080 by default
```

### Install & run (pip)

```bash
pip install fastmcp starlette uvicorn
python server.py
```

Open:

* `http://localhost:8080/` → welcome page
* `POST http://localhost:8080/mcp` → stateless JSON-RPC shim

---

## Deploy to Cloud Run

### 1) Build & push image

```bash
# create a Docker repo once (choose your PROJECT_ID and region)
gcloud artifacts repositories create remote-mcp-servers \
  --repository-format=docker \
  --location=us-central1

# build & push with Cloud Build
gcloud builds submit --region=us-central1 \
  --tag us-central1-docker.pkg.dev/$PROJECT_ID/remote-mcp-servers/mcp-server:latest
```

### 2) Deploy to Cloud Run

```bash
gcloud run deploy mcp-server \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/remote-mcp-servers/mcp-server:latest \
  --region=us-central1 \
  --no-allow-unauthenticated   # recommended: keep private
```

(Optional) Make public for quick testing:

```bash
gcloud run services add-iam-policy-binding mcp-server \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

---

## Usage

### A) Stateless JSON-RPC shim (easy testing)

**POST** `https://<your-service>.run.app/mcp`
Headers:

```
Content-Type: application/json
Accept: application/json
```

**List tools**

```json
{
  "jsonrpc": "2.0",
  "id": "list-1",
  "method": "tools/list",
  "params": {}
}
```

**Call zodiac\_sign**

```json
{
  "jsonrpc": "2.0",
  "id": "z-1",
  "method": "tools/call",
  "params": {
    "name": "zodiac_sign",
    "arguments": { "birthdate": "2001-04-15" }
  }
}
```

**Call add / subtract**

```json
{
  "jsonrpc": "2.0",
  "id": "add-1",
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": { "a": 1, "b": 2 }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": "sub-1",
  "method": "tools/call",
  "params": {
    "name": "subtract",
    "arguments": { "a": 10, "b": 3 }
  }
}
```

## B) Spec-compliant MCP (sessions) on `/mcp-stream`

Use this for real MCP clients. The flow is:

1. **POST** `initialize` → server returns **Mcp-Session-Id** header
2. Include **`Mcp-Session-Id: <value>`** in all subsequent POSTs
3. (Optional) **GET** with `Accept: text/event-stream` to receive events

Example `initialize` body:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "tools": {} },
    "clientInfo": { "name": "sample-client", "version": "1.0.0" }
  }
}
```

Then call:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

…and:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": { "name": "zodiac_sign", "arguments": { "birthdate": "2001-04-15" } }
}
```

Make sure to include `Mcp-Session-Id` in request headers after `initialize`.

---

## Project Layout (example)

```
.
├─ server.py               # Starlette app + MCP shim + MCP stream
├─ Dockerfile              # Uses python:3.13-slim + uv
└─ pyproject.toml          # fastmcp, starlette, uvicorn, etc.
```


---

## Acknowledgments

* [Model Context Protocol](https://modelcontextprotocol.io/)
* Base Code on this: [Build and Deploy a Remote MCP Server to Google Cloud Run in Under 10 Minutes](https://cloud.google.com/blog/topics/developers-practitioners/build-and-deploy-a-remote-mcp-server-to-google-cloud-run-in-under-10-minutes)
* FastMCP
* Google Cloud Run
