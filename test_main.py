import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from agent.mock_agent import MockAgent
from main import app, GREETING_TEXT, get_agent, get_websocket_handler
from unittest.mock import patch, AsyncMock

def get_test_agent():
    return MockAgent(None, None)

def get_test_websocket_handler():
    return mock_impl
async def mock_impl(websocket):
    data = await websocket.receive_json()
    await websocket.send_json({'type': 'expected', 'received': data})

# Initialize the FastAPI TestClient
@pytest.fixture(scope='function')
def client():
    app.dependency_overrides[get_agent] = get_test_agent
    app.dependency_overrides[get_websocket_handler] = get_test_websocket_handler
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

TEST_MESSAGE = "Hello computer, this is a local unit test."

def test_voice_endpoint_returns_twiml_gather(client):
    # Given the system can accept calls
    # When the user makes a call to the system
    response = client.post("/voice")
    
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    
    # Then the system should greet them
    root = ET.fromstring(response.text)
    assert root.tag == "Response"
    assert GREETING_TEXT in response.text
    # And listen to what they have to say
    CONVERSATION_TAGS = {"Gather", "Connect", "Redirect", "Record"}
    assert any(child.tag in CONVERSATION_TAGS for child in root)


def test_websocket_can_send_and_receive(client):
    # given the user has connected on the call
    # when the agent greets the user
    with client.websocket_connect('/ws') as websocket:
        # then the websocket connection is established
        assert websocket is not None
        # and client and server can send messages bidirectionally
        websocket.send_json({'type': 'test'})
        response = websocket.receive_json()
        assert response['type'] == 'expected'

    

def test_respond_endpoint_captures_speech_transcript(client):
    # Given a user is on a call with the agent
    # When the user says something
    
    mock_twilio_form_data = {
        "SpeechResult": TEST_MESSAGE,
        "Confidence": "0.98",
        "CallSid": "CA1234567890abcdef"
    }
    
    
    response = client.post("/respond", data=mock_twilio_form_data)
    
    # Then the system should get what the user said
    assert response.status_code == 200

def test_respond_endpoint_gets_agent_response(client):
    # Given a user is on a call with the agent
    # When the user says something
    
    mock_twilio_form_data = {
        "SpeechResult": TEST_MESSAGE,
        "Confidence": "0.98",
        "CallSid": "CA1234567890abcdef"
    }
    
    
    response = client.post("/respond", data=mock_twilio_form_data)
    print('response:', response.text)
    
    # Then the user should hear a response from the agent
    assert response.status_code == 200
    root = ET.fromstring(response.text)
    assert root.tag == "Response"
    
    say = next(root.iter('Say'), None)
    assert say is not None
    assert len(say.text) > 0

def test_respond_endpoint_gets_agent_response_and_stays_on_call(client):
    # Given the agent has greeted the user
    response = client.post("/voice")
    # When the user says something
    
    mock_twilio_form_data = {
        "SpeechResult": TEST_MESSAGE,
        "Confidence": "0.98",
        "CallSid": "CA1234567890abcdef"
    }
    
    
    response = client.post("/respond", data=mock_twilio_form_data)
    print('response:', response.text)
    
    # Then the system should greet them
    # And stay on the call
    root = ET.fromstring(response.text)
    assert root.tag == "Response"
    gather = root.find("Gather")
    assert gather is not None
    
    say = gather.find('Say')
    assert say is not None
    assert len(say.text) > 0