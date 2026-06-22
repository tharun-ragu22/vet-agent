import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from agent.mock_agent import MockAgent
from main import app, GREETING_TEXT, get_agent

def get_test_agent():
    return MockAgent()

# Initialize the FastAPI TestClient
@pytest.fixture(scope='function')
def client():
    app.dependency_overrides[get_agent] = get_test_agent
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
    # And listen to what they have to say
    root = ET.fromstring(response.text)
    assert root.tag == "Response"
    gather = root.find("Gather")
    assert gather is not None
    
    say = gather.find('Say')
    assert say is not None
    assert say.text == GREETING_TEXT
    assert gather.attrib["action"] == "/respond"
    assert gather.attrib["method"] == "POST"

    

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
    
    say = root.find('Say')
    assert say is not None
    assert len(say.text) > 0