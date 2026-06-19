from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import VoiceResponse

app = FastAPI()

@app.post("/voice")
async def voice():
    """Triggered when someone dials your Twilio number."""
    response = VoiceResponse()
    
    # Instruct Twilio to listen for speech and send it to our /respond endpoint
    gather = response.gather(input="speech", action="/respond", method="POST")
    gather.say("Please say something after the beep.")
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/respond")
async def respond(SpeechResult: str = Form(None)):
    """Triggered after the person finishes speaking."""
    print("\n" + "="*40)
    if SpeechResult:
        print(f"[TRANSCRIPT RECEIVED]: {SpeechResult}")
    else:
        print("[SYSTEM]: No speech was detected.")
    print("="*40 + "\n")
    
    # Hang up the call cleanly
    response = VoiceResponse()
    response.say(f"I heard {SpeechResult}. Thank you. Goodbye.")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")