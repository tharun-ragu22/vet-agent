import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
from agent.mock_agent import MockAgent
from main import app, GREETING_TEXT, create_transcript, get_agent, get_summarizer, get_context_store
from context_store.context_store import ContextStore, ConversationTurn
import json

def get_test_agent():
    return MockAgent(None, None)




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
    root = ET.fromstring(response.text)
    assert root.tag == "Response"
    assert GREETING_TEXT in response.text
    # And listen to what they have to say
    CONVERSATION_TAGS = {"Gather", "Connect", "Redirect", "Record"}
    assert any(child.tag in CONVERSATION_TAGS for child in root)


def test_websocket_can_send_and_receive(client):
    # given the user has connected on the call
    with client.websocket_connect('/ws') as websocket:
        # when the websocket connection is established
        websocket.send_json({'type': 'setup', 'callSid': '1234'})
        # then client and server can send messages bidirectionally
        assert websocket is not None
        websocket.send_json({'type': 'prompt', 'voicePrompt': 'test'})
        response = websocket.receive_json()
        print('my response:', response)
        assert response.get('token') is not None

def test_websocket_multiple_connections(client):
    # Given a user is connected with the agent
    # And the clinic has a free line available
    with client.websocket_connect('/ws') as websocket:
        # When another user connects to the service
        with client.websocket_connect('/ws') as websocket2:
            # Then the system can serve both users
            assert websocket is not None
            assert websocket2 is not None
            assert websocket != websocket2
            # and client and server can send messages bidirectionally
            websocket.send_json({'type': 'setup', 'callSid': '1234'})
            websocket2.send_json({'type': 'setup', 'callSid': '1235'})

            websocket.send_json({'type': 'prompt', 'voicePrompt': 'test'})
            websocket2.send_json({'type': 'prompt', 'voicePrompt': 'test'})
            response2 = websocket2.receive_json()
            response = websocket.receive_json()
            assert response2.get('token') is not None
            assert response.get('token') is not None

def test_websocket_when_redirect_system_transfers_and_closes_connection(client):
    # Given the user is on call with the agent
    with client.websocket_connect('/ws') as websocket:
        websocket.send_json({'type': 'setup', 'callSid': '1234'})
        # When the agent signals to transfer the call to a human
        websocket.send_json({'type': 'prompt', 'voicePrompt': 'REDIRECT'}) # mock agent echoes prompt
        response = websocket.receive_json()
        # Then the system transfers to a human
        assert response.get('type') == 'end'
        assert response.get('handoffData') is not None
        assert json.loads(response.get('handoffData')).get('transferTo','') != ''

def test_redirect_endpoint_redirects_to_number(client):
    # Given the agent could not answer the user query
    # And signalled to redirect the call
    # When the telephony system posts the redirect endpoint
    expected_redirect_number = '+15551234567'
    redirect_data = {
        "HandoffData": f'{{"transferTo": "{expected_redirect_number}"}}',
    }
    response = client.post('/redirect', data=redirect_data)
    # Then the user is transferred to the clinic's phone number
    root = ET.fromstring(response.text)
    dial_node = root.find('Dial')
    assert any([elem.text == expected_redirect_number for elem in dial_node.iter()])

def test_redirect_endpoint_instructs_to_use_brief_endpoint(client):
    # Given the agent could not answer the user query
    expected_redirect_number = '+15551234567'
    expected_summary_text = "expected summary text"
    redirect_data = {
        "HandoffData": f'{{"transferTo": "{expected_redirect_number}", "callContext": "{expected_summary_text}"}}',
    }
    # And signalled to redirect the call
    # When the telephony system posts the redirect endpoint
    response = client.post('/redirect', data=redirect_data)
    # Then it should receive instructions to post to the briefing endpoint
    root = ET.fromstring(response.text)
    assert root is not None
    assert any(['brief-reception' in node.get('url','') for node in root.iter()])

# Initialize the FastAPI TestClient
@pytest.fixture(scope='function')
def brief_receptionist_client():
    async def mock_summarizer(context):
        return "example summary"
    app.dependency_overrides[get_agent] = get_test_agent
    app.dependency_overrides[get_summarizer] = lambda : mock_summarizer
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_brief_receptionist_endpoint_sends_context_to_receptionist(brief_receptionist_client):
    # Given the agent decided to redirect the call
    example_call_sid = '1234'
    with brief_receptionist_client.websocket_connect('/ws') as websocket:
        websocket.send_json({'type': 'setup', 'callSid': example_call_sid})
        websocket.send_json({'type': 'prompt', 'voicePrompt': 'REDIRECT'}) # mock agent echoes prompt
        response = websocket.receive_json()
    
    # When the telephony system posts the briefing endpoint
    response = brief_receptionist_client.post('/brief-reception', data={"ParentCallSid": example_call_sid})
    # print('received response', response.json())
    # Then it should receive instructions to send the summary of the previous conversation to the receptionist
    root = ET.fromstring(response.text)
    say_nodes = root.findall('.//Say') # look recursively through
    assert any(["example summary" in node.text for node in say_nodes])
    # And to ask them to press any key to continue talking with the user
    gather_nodes = root.findall('Gather')
    assert any([node.get('input','') == 'dtmf' for node in gather_nodes])


@pytest.fixture(scope='function')
def brief_receptionist_client2():
    async def mock_summarizer(context):
        return "example summary 2"
    app.dependency_overrides[get_agent] = get_test_agent
    app.dependency_overrides[get_summarizer] = lambda : mock_summarizer
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_brief_receptionist_endpoint_sends_context_to_receptionist2(brief_receptionist_client2):
    # Given the agent decided to redirect the call
    example_call_sid = '1235'
    with brief_receptionist_client2.websocket_connect('/ws') as websocket:
        websocket.send_json({'type': 'setup', 'callSid': example_call_sid})
        websocket.send_json({'type': 'prompt', 'voicePrompt': 'REDIRECT'}) # mock agent echoes prompt
        response = websocket.receive_json()
    
    # When the telephony system posts the briefing endpoint
    response = brief_receptionist_client2.post('/brief-reception', data={"ParentCallSid": example_call_sid})
    print('received response', response.text)
    print('status', response.status_code)
    # Then it should receive instructions to send the summary of the previous conversation to the receptionist
    root = ET.fromstring(response.text)
    say_nodes = root.findall('.//Say') # look recursively through
    assert any(["example summary 2" in node.text for node in say_nodes])
    # And to ask them to press any key to continue talking with the user
    gather_nodes = root.findall('Gather')
    assert any([node.get('input','') == 'dtmf' for node in gather_nodes])

@pytest.fixture(scope='function')
def context_store_client_and_store():
    mock_summarizer = lambda context : "example summary"
    app.dependency_overrides[get_agent] = get_test_agent
    app.dependency_overrides[get_summarizer] = lambda : mock_summarizer
    external_context_store = ContextStore()
    app.dependency_overrides[get_context_store] = lambda : external_context_store
    with TestClient(app) as c:
        yield c, external_context_store
    app.dependency_overrides.clear()


def test_brief_receptionist_endpoint_gets_context_from_previous_conversation(context_store_client_and_store):
    context_store_client, external_context_store = context_store_client_and_store
    # Given the agent decided to redirect the call
    example_call_sid = '1235'
    expected_text = "hey how's it going"
    with context_store_client.websocket_connect('/ws') as websocket:
        websocket.send_json({'type': 'setup', 'callSid': example_call_sid})
        websocket.send_json({'type': 'prompt', 'voicePrompt': expected_text})
        websocket.send_json({'type': 'prompt', 'voicePrompt': 'REDIRECT'}) # mock agent echoes prompt
        # When the agent disconnects from the user
    
    
    # Then the system has the conversation for summarization
    context = external_context_store.get_context(example_call_sid)
    print('returned contenxt', context)
    assert any([turn.role == 'user' and turn.content == expected_text for turn in context])
    assert any([turn.role == 'agent' for turn in context])

def test_create_transcript_sample_context_should_create_transcript_string():
    example_conversation=[
        ConversationTurn(role='agent',content='hey, how\'s it going'),
        ConversationTurn(role='user',content='hi')
    ]
    transcript = create_transcript(example_conversation)
    transcript_lines = transcript.splitlines()

    assert transcript_lines[0] == 'Transcript:'
    for i in range(len(example_conversation)):
        assert example_conversation[i].role.capitalize() == transcript_lines[i+1].split(sep=': ', maxsplit=1)[0]
        assert example_conversation[i].content == transcript_lines[i+1].split(sep=': ', maxsplit=1)[1]

def test_create_transcript_empty_context_should_just_return_title():
    transcript = create_transcript([])
    assert transcript == 'Transcript:\n'