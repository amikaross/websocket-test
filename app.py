import base64
import json
import logging
import os
import threading
import websocket

from flask import Flask, request
from geventwebsocket import WebSocketServer, WebSocketApplication, Resource

HTTP_SERVER_PORT = 5001

# Load environment variables from .env file
def load_env():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass

load_env()

# Get Deepgram API key from environment variable
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY', 'YOUR_DEEPGRAM_API_KEY_HERE')

class MediaStreamHandler(WebSocketApplication):
    def on_open(self):
        print("WebSocket connection established")
        self.has_seen_media = False
        self.message_count = 0
        self.deepgram_ws = None
        self.deepgram_thread = None
        self.stream_config = None

    def on_message(self, message):
        if message is None:
            print("No message received...")
            return
        
        # Messages are a JSON encoded string
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            print("Failed to parse JSON message: {}".format(e))
            return
        
        # Using the event type you can determine what type of message you are receiving
        if data['event'] == "connected":
            pass  # Connection established
        if data['event'] == "start":
            self.stream_config = data['start']
            # Connect to Deepgram when stream starts
            self.connect_to_deepgram()
        if data['event'] == "media":
            payload = data['media']['payload']
            chunk = base64.b64decode(payload)
            track = data['media'].get('track', 'unknown')
            
            if not self.has_seen_media:
                self.has_seen_media = True
            
            # For conference calls, process only inbound audio
            # Conference outbound audio often contains echo and is harder to transcribe
            if track == "inbound" and self.deepgram_ws and self.deepgram_ws.sock and self.deepgram_ws.sock.connected:
                try:
                    # Check if chunk has any non-zero bytes (basic audio activity check)
                    has_audio = any(b != 0 for b in chunk)
                    if not has_audio:
                        return
                    
                    self.deepgram_ws.send(chunk, websocket.ABNF.OPCODE_BINARY)
                except Exception as e:
                    print(f"Error sending to Deepgram: {e}")
        if data['event'] == "stop":
            print("Twilio stream stopped")
            self.close_deepgram()
        if data['event'] == "closed":
            self.close_deepgram()
            return
        
        self.message_count += 1

    def connect_to_deepgram(self):
        """Connect to Deepgram WebSocket API"""
        if DEEPGRAM_API_KEY == 'YOUR_DEEPGRAM_API_KEY_HERE':
            print("ERROR: Deepgram API key not set!")
            print("Please create a .env file with: DEEPGRAM_API_KEY=your_actual_api_key")
            print("Or set the environment variable: export DEEPGRAM_API_KEY=your_actual_api_key")
            return
        
        # Build Deepgram WebSocket URL with parameters
        # Twilio sends μ-law audio at 8000Hz mono
        # Using enhanced model and parameters for better conference audio handling
        deepgram_url = (
            f"wss://api.deepgram.com/v1/listen?"
            f"model=nova-2&"
            f"language=en-US&"
            f"encoding=mulaw&"
            f"sample_rate=8000&"
            f"channels=1&"
            f"interim_results=true&"
            f"punctuate=true&"
            f"smart_format=true&"
            f"diarize=false&"
            f"multichannel=false&"
            f"utterance_end_ms=1000&"
            f"vad_events=true"
        )
        
        def on_deepgram_message(ws, message):
            """Handle messages from Deepgram"""
            try:
                response = json.loads(message)
                
                if response.get('type') == 'Results':
                    transcript = response.get('channel', {}).get('alternatives', [{}])[0].get('transcript', '')
                    is_final = response.get('is_final', False)
                    
                    # Only print final transcriptions
                    if transcript and is_final:
                        print(f"Transcription: {transcript}")
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing Deepgram message: {e}")
        
        def on_deepgram_error(ws, error):
            print(f"Deepgram WebSocket error: {error}")
        
        def on_deepgram_close(ws, close_status_code, close_msg):
            pass  # Connection closed
        
        def on_deepgram_open(ws):
            pass  # Connected to Deepgram
        
        # Create WebSocket connection to Deepgram
        ws = websocket.WebSocketApp(
            deepgram_url,
            header={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
            on_message=on_deepgram_message,
            on_error=on_deepgram_error,
            on_close=on_deepgram_close,
            on_open=on_deepgram_open
        )
        
        self.deepgram_ws = ws
        
        # Run Deepgram WebSocket in a separate thread
        self.deepgram_thread = threading.Thread(target=ws.run_forever, daemon=True)
        self.deepgram_thread.start()
    
    def close_deepgram(self):
        """Close Deepgram WebSocket connection"""
        if self.deepgram_ws:
            try:
                self.deepgram_ws.close()
            except:
                pass
            self.deepgram_ws = None
    
    def on_close(self, reason):
        print(f"WebSocket closed: {reason}")
        self.close_deepgram()

# Flask app for HTTP routes
app = Flask(__name__)

@app.route('/')
def index():
    return "WebSocket server is running. Connect to ws://localhost:5001/media for WebSocket connections."

if __name__ == '__main__':
    print("WebSocket transcription server started")
    print("Listening on: http://localhost:" + str(HTTP_SERVER_PORT))
    print("WebSocket endpoint: ws://localhost:" + str(HTTP_SERVER_PORT) + "/media")
    print("Ready for Twilio Media Streams...")
    
    # Create WebSocket server with resource mapping
    WebSocketServer(
        ('', HTTP_SERVER_PORT),
        Resource({'/media': MediaStreamHandler})
    ).serve_forever()
