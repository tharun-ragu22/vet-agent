import pytest
from main import app, PORT
import uvicorn
import time
import socket
import threading
import json
import websockets
  

@pytest.mark.asyncio
async def test_full_conversation_flow(live_server):
    async with websockets.connect(f"{live_server}/ws") as ws:
        await ws.send(json.dumps({"type": "setup", "callSid": "CA_test_123"}))
        await ws.send(json.dumps({"type": "prompt", "voicePrompt": "My dog needs a rabies shot"}))
        response = json.loads(await ws.recv())
        assert "appointment" in response["token"].lower()