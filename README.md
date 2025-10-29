# Twilio Media Streams to Deepgram Transcription

This application receives real-time audio streams from Twilio voice calls and forwards them to Deepgram for live speech-to-text transcription.

## What It Does

- **Receives WebSocket connections from Twilio Media Streams** when a phone call uses the `<Start><Stream>` TwiML verb
- **Captures audio** in real-time from Twilio voice calls (μ-law encoded, 8000Hz, mono)
- **Forwards audio to Deepgram** via WebSocket for real-time transcription
- **Displays transcriptions** as people speak, showing both interim and final results

## Architecture

```
Twilio Call → TwiML (<Stream>) → Your WebSocket Server → Deepgram API
                                      ↓
                              Terminal Output (Transcriptions)
```

## Prerequisites

- Python 3.x
- A Twilio account with a phone number
- A Deepgram account with an API key ([Get one here](https://deepgram.com))
- ngrok (for local development to expose your server publicly)

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install flask gevent gevent-websocket websocket-client
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

Replace `your_deepgram_api_key_here` with your actual Deepgram API key.

### 3. Set Up ngrok (for local testing)

Install ngrok and create a config file at `~/Library/Application Support/ngrok/ngrok.yml`:

```yaml
version: "2"
authtoken: YOUR_NGROK_AUTH_TOKEN

tunnels:
  websocket-app:
    addr: 5001
    proto: http
```

Start the tunnel:
```bash
ngrok start websocket-app
```

Note the public URL (e.g., `https://abc123.ngrok-free.app`)

### 4. Update Your TwiML

In the Volie application, alter your incoming phone number to use streaming and add your ngrok url, this will generate return TwiML that includes:

```xml
<Response>
    <Start>
        <Stream url="wss://YOUR_NGROK_URL.ngrok-free.app/media"></Stream>
    </Start>
    <Dial>
        <!-- Your dial configuration -->
    </Dial>
</Response>
```

If desired, manually alter the twiml code in Volie application repo for easy testing without configuring at the ipn level

**Important Notes on Twiml**: 
- Use `wss://` (secure WebSocket), not `ws://`
- Include the `/media` path in the URL
- Place `<Start>` before `<Dial>` to ensure the stream starts immediately

### 5. Run the Server

```bash
source venv/bin/activate
python app.py
```

You should see:
```
Starting WebSocket server...
Server listening on: http://localhost:5001
WebSocket endpoint: ws://localhost:5001/media
```

## Usage

1. Make a phone call through the Volie application
2. The server will automatically:
   - Accept the WebSocket connection from Twilio
   - Connect to Deepgram
   - Forward audio in real-time
   - Display transcriptions in your terminal

### Example Output

```
============================================================
NEW WEBSOCKET CONNECTION ACCEPTED
WebSocket path: /media
============================================================
Connected Message received: {"event":"connected"...}
Start Message received: {"event":"start"...}
Deepgram connection initiated...
Connected to Deepgram WebSocket
Media message received: 160 bytes
[INTERIM] Transcription: Hello how are you
[FINAL] Transcription: Hello, how are you?
```

## Configuration

### Deepgram Options

You can customize Deepgram settings in the `connect_to_deepgram()` method:

- **Model**: Change `model=nova-2` to other models (nova, whisper-large, etc.)
- **Language**: Change `language=en-US` to other BCP-47 language codes
- **Interim Results**: Set `interim_results=true` for real-time partial transcripts
- **Punctuation**: Set `punctuate=true` to add punctuation automatically

See [Deepgram's API documentation](https://developers.deepgram.com/reference/speech-to-text/listen-streaming) for all available options.

### Audio Format

The app is configured for Twilio's default audio format:
- Encoding: μ-law (mulaw)
- Sample Rate: 8000 Hz
- Channels: 1 (mono)

## Troubleshooting

### No Connection from Twilio
- Verify your ngrok tunnel is running: `ngrok start websocket-app`
- Check the URL in your TwiML matches the ngrok URL exactly
- Ensure you're using `wss://` not `ws://`

### Deepgram Not Connecting
- Verify your API key is set in the `.env` file
- Check for "WARNING: Deepgram API key not set" message
- Ensure no extra spaces around the `=` in `.env` file

### No Transcriptions
- Check that audio is being received (look for "Media message received")
- Verify Deepgram connection message appears
- Check terminal for any error messages

## Project Structure

```
websocket_test/
├── app.py              # Main application (WebSocket server)
├── .env                # Environment variables (not in git)
├── .gitignore          # Git ignore file
├── README.md           # This file
└── venv/               # Virtual environment (not in git)
```

## License

MIT

## Resources

- [Twilio Media Streams Documentation](https://www.twilio.com/docs/voice/twiml/stream)
- [Deepgram Streaming API](https://developers.deepgram.com/reference/speech-to-text/listen-streaming)
- [ngrok Documentation](https://ngrok.com/docs)
