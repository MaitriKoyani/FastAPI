from fastapi import FastAPI, Request, Response, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, String, Integer, JSON, ARRAY
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel
import uuid  
from typing import List, Optional
import random

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DATABASE_URL = "sqlite:///./sessions.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserSession(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True, index=True)
    username = Column(String)
    room_code = Column(String)
    matrix = Column(JSON, default=lambda: [[0]*5 for _ in range(5)])   
    bingo_count = Column(Integer, default=0)

Base.metadata.create_all(bind=engine) 


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var username = {username}
            document.querySelector("#ws-id").textContent = username;
            var ws = new WebSocket(`ws://localhost:8000/ws/${username}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var number = document.createElement('li')
                var content = document.createTextNode(event.data)
                number.appendChild(content)
                messages.appendChild(number)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


def save_session(session_id, username, room_code, matrix, bingo_count):
    db = SessionLocal()
    user_session = UserSession(session_id=session_id, username=username, room_code=room_code, matrix=[[0]*5 for _ in range(5)], bingo_count=0)
    db.add(user_session)
    db.commit()
    db.close()
db = SessionLocal()
def get_session(session_id):
    db = SessionLocal()
    session_data = db.query(UserSession).filter_by(session_id = session_id).first()
    print(session_data,'session_data')
    db.close()
    return session_data


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    
    return templates.TemplateResponse("welcome.html", {"request": request})
@app.post("/", response_class=HTMLResponse)
async def check_name(request: Request, username: str = Form(...)):
    if db.query(UserSession).filter_by(username = username).first():
        print('hi')
        return templates.TemplateResponse("welcome.html", {"status": "Username already exists", "request": request}) 
    return templates.TemplateResponse("home.html", {"request": request, "name": username})
@app.post("/create-room/{username}")
async def create_room(response: Response,request: Request, username: str, room_code: Optional[str] = Form(None)):
   
    session_id = str(uuid.uuid4())  
   
    try:
        if room_code:
            ses = True if db.query(UserSession).filter_by(room_code = room_code).first() else False
            print(ses,'ses')
            if not ses:                                      
                print('not')
                return templates.TemplateResponse("home.html", {"status": "Room code does not exist", "request": request, "name": username})

        if not room_code:
            room_code = random.randint(100000, 999999)
            print(room_code,'room_code')
        save_session(session_id, username, room_code, matrix=[[0]*5 for _ in range(5)], bingo_count=0)
    except Exception as e:
        return templates.TemplateResponse("home.html", {"status": "Error creating room", "request": request, "name": username})
    
    response = RedirectResponse(url=f"/room/", status_code=303)
    response.set_cookie(key="session_id", value=session_id,httponly=True, max_age=74400,samesite="Lax",)  # Store session ID in a cookie
    
    return response

@app.get("/room/", response_class=HTMLResponse)
async def room(request: Request):
    print('room')
    session_id = request.cookies.get("session_id")
    print(session_id,'session_id')
    user_data = get_session(session_id)
    print(user_data,'user_data')
    room_code = user_data.room_code
    room_code=int(room_code)
    
    if not user_data:
        return RedirectResponse(url="/")  
    users = db.query(UserSession).filter_by(room_code=room_code).all()
    users_in_room = []
    for user in users:
        users_in_room.append(user.username)
    return templates.TemplateResponse("room.html", {"request": request, "user": user_data, "users": users_in_room})

@app.get("/join-room/{username}")
async def join_room(request: Request, username: str):
    session_id = request.cookies.get("session_id")
    user_data = get_session(session_id)
    if not user_data:
        return RedirectResponse(url="/")
    room_code = user_data.room_code
    users = db.query(UserSession).filter_by(room_code=room_code).all()
    users_in_room = []
    for user in users:
        users_in_room.append(user.username)
    print(users_in_room,'users_in_room')
    content = html.replace("{username}", f'"{username}"')
    return HTMLResponse(content=content)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, number: int, websocket: WebSocket):
        await websocket.send_text(number)

    async def broadcast(self, number: int):
        for connection in self.active_connections:
            await connection.send_text(number)


manager = ConnectionManager()


@app.get("/{username}")
async def get(username: str):
    content = html.replace("{username}", f'"{username}"')
    return HTMLResponse(content=content)


@app.websocket("/ws/{username}")
async def websocket_endpoint(request: Request, websocket: WebSocket, username: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            number = int(data)
            session_id = request.cookies.get("session_id")
            user_data = get_session(session_id)
            print(user_data,'user_data')
            # if user_data:
                # matrix = user_data.matrix
                # print(matrix,'matrix')
            await manager.send_personal_message(f"Your number is: {data}", websocket)

            await manager.broadcast(f"Client #{username} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{username} left the chat")

@app.get("/logout")
def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    print(session_id,'session_id')

    db.query(UserSession).filter_by(session_id=session_id).delete()
    db.commit()
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")  
    return response
