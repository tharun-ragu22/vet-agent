import pytest
from main import app, PORT

import json
import websockets
  

@pytest.mark.asyncio
async def test_make_request():
    async with websockets.connect(f"ws://localhost:{PORT}/ws") as ws:
        await ws.send(json.dumps({"type": "setup", "callSid": "CA_test_123"}))
        await ws.send(json.dumps({"type": "prompt", "voicePrompt": "My dog needs a rabies shot"}))
        response = json.loads(await ws.recv())
        assert len(response["token"].lower()) > 0