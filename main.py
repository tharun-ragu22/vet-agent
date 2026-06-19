from fastapi import FastAPI, Form, Response, BackgroundTasks
from twilio.twiml.voice_response import VoiceResponse

app = FastAPI()
GREETING_TEXT = "Please say something after the beep."

@app.post("/voice")
async def voice():
    """Triggered when someone dials your Twilio number."""
    response = VoiceResponse()
    
    # Instruct Twilio to listen for speech and send it to our /respond endpoint
    gather = response.gather(input="speech", action="/respond", method="POST")
    gather.say(GREETING_TEXT)
    
    return Response(content=str(response), media_type="application/xml")

async def process_user_transcript(text: str):
    """A separate function handling the business logic processing."""
    # This might log to a DB or send data somewhere else in production
    pass

@app.post("/respond")
async def respond(background_tasks: BackgroundTasks, SpeechResult: str = Form(None)):
    """Triggered after the person finishes speaking."""
    print("\n" + "="*40)
    if SpeechResult:
        print(f"[TRANSCRIPT RECEIVED]: {SpeechResult}")
    else:
        print("[SYSTEM]: No speech was detected.")
    print("="*40 + "\n")
    
    # Hang up the call cleanly
    response = VoiceResponse()
    background_tasks.add_task(process_user_transcript, SpeechResult)
    response.say(f"I heard {SpeechResult}. Thanks, goodbye")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")