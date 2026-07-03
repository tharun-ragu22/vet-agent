from fastapi import FastAPI, Form, Response, Depends, Request, WebSocket
from twilio.twiml.voice_response import VoiceResponse
from agent.agent_interface import AgentBaseClass
from agent.prod_agent import ProdAgent
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = ProdAgent()
    yield

def get_agent(request: Request) -> AgentBaseClass:
    return request.app.state.agent

app = FastAPI(lifespan=lifespan)

GREETING_TEXT = "Hi! I'm an AI agent. How can I help?"
PORT=8000
DOMAIN = os.getenv('NGROK_URL')
WS_URL = f"wss://{DOMAIN}/ws"

sessions = {}

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

def get_websocket_handler():
    return websocket_handler

async def websocket_handler(websocket: WebSocket):
    pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, handler = Depends(get_websocket_handler)):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()

    await handler(websocket)
                
    # except WebSocketDisconnect:
    #     print("WebSocket connection closed")
    #     if call_sid:
    #         sessions.pop(call_sid, None)


@app.post("/respond")
async def respond(
    SpeechResult: str = Form(None), agent: AgentBaseClass = Depends(get_agent)
):
    """Triggered after the person finishes speaking."""
    print("\n" + "="*40)
    if SpeechResult:
        print(f"[TRANSCRIPT RECEIVED]: {SpeechResult}")
    else:
        print("[SYSTEM]: No speech was detected.")
    print("="*40 + "\n")

    # Hang up the call cleanly
    response = VoiceResponse()
    gather = response.gather(
        input="speech",
        action="/respond", # Loops back here when they finish speaking again
        method="POST",
        speech_timeout="auto"
    )
    ret = await agent.run_agent(SpeechResult)
    print('finished!', ret.output)
    gather.say(ret.output)

    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    print(f"Server running at http://localhost:{PORT} and {WS_URL}")