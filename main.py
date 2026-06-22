from fastapi import FastAPI, Form, Response, Depends
from twilio.twiml.voice_response import VoiceResponse
from agent.agent_interface import IAgent
from agent.prod_agent import ProdAgent

app = FastAPI()

def get_agent() -> IAgent:
    return ProdAgent()
GREETING_TEXT = "Please say something after the beep."

@app.post("/voice")
async def voice():
    """Triggered when someone dials your Twilio number."""
    response = VoiceResponse()
    
    # Instruct Twilio to listen for speech and send it to our /respond endpoint
    gather = response.gather(input="speech", action="/respond", method="POST")
    gather.say(GREETING_TEXT)
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/respond")
async def respond(SpeechResult: str = Form(None), agent: IAgent = Depends(get_agent)):
    """Triggered after the person finishes speaking."""
    print("\n" + "="*40)
    if SpeechResult:
        print(f"[TRANSCRIPT RECEIVED]: {SpeechResult}")
    else:
        print("[SYSTEM]: No speech was detected.")
    print("="*40 + "\n")
    
    # Hang up the call cleanly
    response = VoiceResponse()
    # background_tasks.add_task(process_user_transcript, SpeechResult)
    ret = await agent.run_agent(SpeechResult)
    print('finished!', ret.output)
    response.say(ret.output)
    
    return Response(content=str(response), media_type="application/xml")