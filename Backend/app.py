from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import logging
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables (for the Google API key, if needed)
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("AIzaSyBN3IJNxFJbYzFzVfuydHU7iXIzxZQ61Ho")
if not GOOGLE_API_KEY:
    logger.error("Google API key not found in environment variables!")
genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI()

class ConnectionManager:
    """Manages active WebSocket connections by username."""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[username] = websocket
        logger.info(f"{username} connected.")

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]
            logger.info(f"{username} disconnected.")

    async def send_personal_message(self, message: str, username: str):
        """Send a message to a single connected user by username."""
        if username in self.active_connections:
            await self.active_connections[username].send_text(message)
        else:
            logger.warning(f"No active connection for {username}")

manager = ConnectionManager()

# Configure the text-processing model
generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
)

chat_session = model.start_chat(history=[])

async def process_text(text: str, mode: str) -> str:
    """
    Processes text with Google's Generative AI:
    - 'filter' mode => content moderation
    - 'professional' mode => language enhancement
    """
    try:
        if mode == 'filter':
            prompt = f"""
            Act as a strict content moderator. Analyze and clean the following text:

            '{text}'

            Content Filtering Rules:
            1. Remove any profanity or explicitly offensive words (don't replace with symbols, just remove them)
            2. Remove any slurs or hate speech completely
            3. Remove any explicit adult content references
            4. Keep all other words exactly as they are
            5. Maintain spaces between remaining words
            6. If a sentence becomes grammatically incorrect after removal, fix only the essential grammar
            7. DO NOT add any new words or explanations
            8. DO NOT modify non-offensive casual language
            9. Return ONLY the cleaned text
            """
        else:  # professional mode
            prompt = f"""
            You are a professional language enhancer. Modify the text to be more professional and kind, 
            while preserving its meaning:

            '{text}'

            Rules:
            1. Improve language to be more professional/courteous.
            2. Maintain the original meaning and intent.
            3. Remove any offensive/inappropriate content.
            4. Do NOT add new words or explanations.
            5. Keep the length similar to the original.
            6. Return ONLY the modified text.
            """

        response = await asyncio.to_thread(chat_session.send_message, prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Error in process_text: {e}")
        return text  # Fallback to original text

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    """
    One-to-one private chat:
      - 'username' is the sender's username
      - The payload must include 'to' for the recipient.
    """
    await manager.connect(username, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            text = message_data.get("text", "")
            mode = message_data.get("mode", "filter")
            to_username = message_data.get("to")  # intended recipient

            logger.info(f"Received from {username} -> {to_username}: '{text}' (Mode: {mode})")
            processed_text = await process_text(text, mode)
            logger.info(f"Processed text: '{processed_text}'")

            # Send ONLY to the recipient; no echo to the sender.
            if to_username and to_username in manager.active_connections:
                # The recipient sees "<sender>:<processed_text>"
                await manager.send_personal_message(f"{username}:{processed_text}", to_username)
            else:
                # If the recipient is offline or invalid, do nothing or handle error
                logger.warning(f"Recipient {to_username} not connected.")
    except WebSocketDisconnect:
        manager.disconnect(username)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """
    Basic route to confirm server is running.
    """
    return """
    <html>
      <head><title>Chat App</title></head>
      <body>
        <h1>Chat App Backend is Running!</h1>
        <p>Use the React frontend to access the UI.</p>
      </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    # Run without auto-reload to avoid frequent 403 issues on websockets
    uvicorn.run(app, host="0.0.0.0", port=8000)
