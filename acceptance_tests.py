import pytest
from main import app, PORT
import httpx
import json
import websockets
import xml.etree.ElementTree as ET
  

@pytest.mark.asyncio
async def test_make_request():
    async with websockets.connect(f"ws://localhost:{PORT}/ws") as ws:
        await ws.send(json.dumps({"type": "setup", "callSid": "CA_test_123"}))
        await ws.send(json.dumps({"type": "prompt", "voicePrompt": "My dog needs a rabies shot"}))
        response = json.loads(await ws.recv())
        assert len(response["token"].lower()) > 0

@pytest.mark.asyncio
async def test_two_connections_made_system_maintains_context():
    # Given a user is connected with the agent
    async with websockets.connect(f"ws://localhost:{PORT}/ws") as ws1:
        # And the clinic has a free line available
        # When another user connects with the agent
        async with websockets.connect(f"ws://localhost:{PORT}/ws") as ws2:
            await ws1.send(json.dumps({"type": "setup", "callSid": "CA_test_123"}))
            await ws2.send(json.dumps({"type": "setup", "callSid": "CA_test_124"}))
            DOG1 = 'George'
            DOG2 = 'Simba'
            await ws1.send(
                json.dumps(
                    {"type": "prompt", "voicePrompt": f"Can you check if my dog {DOG1} has an appointment today at 5pm?"}
                )
            )

            await ws2.send(
                json.dumps(
                    {"type": "prompt", "voicePrompt": f"Can you check if my dog {DOG2} has an appointment today at 5pm?"}
                )
            )

            response2 = json.loads(await ws2.recv())
            response1 = json.loads(await ws1.recv())

            # Then the system can maintain context on both calls
            # And treat each user independently

            assert DOG1.lower() in response1["token"].lower()
            assert DOG1.lower() not in response2["token"].lower()

            assert DOG2.lower() in response2["token"].lower()
            assert DOG2.lower() not in response1["token"].lower()

@pytest.mark.asyncio
async def test__after_redirect_receptionist_hears_summary():
    # Given the agent decided to redirect the call
    example_call_sid = "CA_test_123"
    async with websockets.connect(f"ws://localhost:{PORT}/ws") as ws:
        await ws.send(json.dumps({"type": "setup", "callSid": example_call_sid}))
        await ws.send(
            json.dumps(
                {"type": "prompt", "voicePrompt": f"Help, my dog just got hit by a car, it's an emergency"}
            )
        )
        await ws.recv()
    
    # When the receptionist picks up the phone
    async with httpx.AsyncClient() as client:
        response = await client.post(f'http://localhost:{PORT}/brief-reception', data={"ParentCallSid": example_call_sid})
        print(response.text)
        # Then they should hear a summary of the previous call
        
        root = ET.fromstring(response.text)
        say_nodes = root.findall('.//Say') # look recursively through
        assert any(["dog" in node.text for node in say_nodes])
        # And to ask them to press any key to continue talking with the user
        gather_nodes = root.findall('Gather')
        assert any([node.get('input','') == 'dtmf' for node in gather_nodes])
    
