from fastapi import FastAPI, Request, Response, Depends, WebSocket, WebSocketDisconnect
from agent.agent_interface import AgentBaseClass
from agent.prod_agent import ProdAgent
from contextlib import asynccontextmanager
import uvicorn
import json
from dotenv import load_dotenv
import os

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = ProdAgent()
    yield

def get_agent(websocket: WebSocket) -> AgentBaseClass:
    return websocket.app.state.agent

app = FastAPI(lifespan=lifespan)

GREETING_TEXT = "Example Animal Hospital. This is virtual agent Janine speaking, how can I help?"
PORT=8000
DOMAIN = os.getenv('NGROK_URL')
WS_URL = f"wss://{DOMAIN}/ws"

sessions = {}

@app.get("/health")
def health_check():
    return {'status': 'healthy'}


@app.post("/voice")
async def twiml_endpoint():
    """Endpoint that returns TwiML for Twilio to connect to the WebSocket"""
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Connect>
        <ConversationRelay url="{WS_URL}" welcomeGreeting="{GREETING_TEXT}" ttsProvider="ElevenLabs" voice="FGY2WhTYpPnrIDTdsKH5" />
      </Connect>
    </Response>"""
    
    return Response(content=xml_response, media_type="application/xml")

@app.post('/redirect')
async def redirect(request : Request):
    form_data = await request.form()
    handoff_data : str = form_data.get("HandoffData", {})
    handoff_data_dict : dict = json.loads(handoff_data)

    transfer_number = handoff_data_dict.get('transferTo')
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say>Transferring you now, please hold.</Say>
        <Dial>{transfer_number}</Dial>
    </Response>"""

    return Response(content=twiml, media_type='application/xml')
    

def get_websocket_handler():
    return websocket_handler



async def websocket_handler(websocket: WebSocket, agent: AgentBaseClass):
    call_sid = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print('message:\n', message)
            
            if message["type"] == "setup":
                call_sid = message["callSid"]
                print(f"Setup for call: {call_sid}")
                websocket.call_sid = call_sid
                sessions[call_sid] = None
                
            elif message["type"] == "prompt":
                print(f"Processing prompt: {message['voicePrompt']}")
                conversation = sessions[websocket.call_sid]
                print("current_conversation:", conversation)
                response = await agent.run_agent(message['voicePrompt'], message_history=conversation)
                if response.output == 'REDIRECT':
                    await websocket.send_text(
                        json.dumps({
                            "type": "end",
                            "handoffData": {
                                "transferTo": os.getenv("REDIRECT_PHONE_NUMBER")
                            }
                        })
                    )
                    return
                sessions[websocket.call_sid] = response.all_messages()
                
                await websocket.send_text(
                    json.dumps({
                        "type": "text",
                        "token": response.output,
                        "last": True
                    })
                )
                print(f"Sent response: {response.output}")
                
            elif message["type"] == "interrupt":
                print("Handling interruption.")
                
            else:
                print(f"Unknown message type received: {message['type']}")
                
    except WebSocketDisconnect:
        print("WebSocket connection closed")
        if call_sid:
            sessions.pop(call_sid, None)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, handler = Depends(get_websocket_handler), agent : AgentBaseClass = Depends(get_agent)):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()

    await handler(websocket, agent)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    print(f"Server running at http://localhost:{PORT} and {WS_URL}")