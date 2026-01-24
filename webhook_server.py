"""Minimal FastAPI webhook server for testing Digital FTE webhook actions."""

import json
from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receive and log webhook payload."""
    payload = await request.json()
    print("\n" + "=" * 50)
    print("📨 Webhook received:")
    print(json.dumps(payload, indent=2))
    print("=" * 50 + "\n")
    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
