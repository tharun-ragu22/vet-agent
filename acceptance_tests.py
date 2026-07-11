import pytest
from main import app, PORT
import uvicorn
import time
import socket
import threading
import json
import websockets

@pytest.fixture(scope='module', autouse=True)
def setup_acceptance_tests():
    print('setup')
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning", ws='websockets-sansio')
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.1):
                break
        except OSError:
            time.sleep(0.1)
    yield
    server.should_exit = True
    thread.join(timeout=5)
    print('teardown')

@pytest.mark.asyncio
async def test_full_conversation_flow(live_server):
    async with websockets.connect(f"{live_server}/ws") as ws:
        await ws.send(json.dumps({"type": "setup", "callSid": "CA_test_123"}))
        await ws.send(json.dumps({"type": "prompt", "voicePrompt": "My dog needs a rabies shot"}))
        response = json.loads(await ws.recv())
        assert "appointment" in response["text"].lower()