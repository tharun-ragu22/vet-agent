import xml.etree.ElementTree as ET
from fastapi.testclient import TestClient
from main import app, GREETING_TEXT
from unittest.mock import patch

# Initialize the FastAPI TestClient
client = TestClient(app)
TEST_MESSAGE = "Hello computer, this is a local unit test."

def test_voice_endpoint_returns_twiml_gather():
    # Given the system can accept calls
    # When the user makes a call to the system
    response = client.post("/voice")
    
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    
    # Then the system should listen to what they have to say
    root = ET.fromstring(response.text)
    assert root.tag == "Response"
    gather = root.find("Gather")
    assert gather is not None
    assert gather.attrib["action"] == "/respond"
    assert gather.attrib["method"] == "POST"

    # And listen to what they have to say
    say = gather.find('Say')
    assert say is not None
    assert say.text == GREETING_TEXT

@patch("main.process_user_transcript")
def test_respond_endpoint_captures_speech_transcript(mock_processor):
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
    mock_processor.assert_called_once_with('hi')