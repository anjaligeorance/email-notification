import socketio
from fastapi import FastAPI
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
from aiosmtplib import SMTP
from email.message import EmailMessage
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Define Socket.IO and FastAPI apps
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Enable CORS for all origins (for frontend testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for incoming task input
class TaskInput(BaseModel):
    name: str
    email: EmailStr
    task: str

# Async function to send email notifications
async def send_email_notification(name: str, email: str, task: str):
    message = EmailMessage()
    message["From"] = os.getenv("EMAIL_USER")
    message["To"] = email
    message["Subject"] = "New Task Assigned"
    message.set_content(
        f"Hello {name},\n\nYou have been assigned a new task:\n\n{task}\n\nRegards,\nTaskBot"
    )

    try:
        smtp = SMTP(hostname="smtp.gmail.com", port=587, start_tls=True)
        await smtp.connect()
        await smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        await smtp.send_message(message)
        await smtp.quit()
    except Exception as e:
        print("Failed to send email:", e)

# API endpoint to assign a task
@app.post("/assign-task/")
async def assign_task(task: TaskInput):
    # Emit real-time socket event to connected clients
    await sio.emit("task_notification", {
        "name": task.name,
        "email": task.email,
        "task": task.task,
    })

    # Send email to the assigned user
    await send_email_notification(task.name, task.email, task.task)

    return {"status": "Task assigned and notification sent"}

# Socket.IO connection events
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
