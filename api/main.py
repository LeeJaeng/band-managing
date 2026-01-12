from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text(f"echo: {msg}")
    except WebSocketDisconnect:
        pass
