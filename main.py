from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base
import uuid  # For generating unique session IDs
import random

app = FastAPI()
templates = Jinja2Templates(directory="templates")
# SQLite Database
DATABASE_URL = "sqlite:///./sessions.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define Session Model
class UserSession(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True, index=True)
    username = Column(String)
    room_code = Column(String)

Base.metadata.create_all(bind=engine)  # Create the table

# Function to save session to DB
def save_session(session_id, username, room_code):
    db = SessionLocal()
    user_session = UserSession(session_id=session_id, username=username, room_code=room_code)
    db.add(user_session)
    db.commit()
    db.close()
db = SessionLocal()
# Function to get session from DB
def get_session(session_id):
    db = SessionLocal()
    session_data = db.query(UserSession).filter_by(session_id = session_id).first()
    db.close()
    return session_data

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    
    return templates.TemplateResponse("home.html", {"request": request})

@app.post("/create-room")
def create_room(response: Response, username: str = Form(...), room_code: str = Form(...)):
    session_id = str(uuid.uuid4())  # Generate a unique session ID
    # Add user to the room
    if db.query(UserSession).filter_by(username = username).first():
        print('hi')
        return RedirectResponse(url="/model", status_code=404)
    if room_code:
        room_code = int(room_code)
        ses = db.query(UserSession).filter_by(room_code = room_code).first()
        if not ses:
            return RedirectResponse(url="/", status_code=404)
    if not room_code :
        room_code = random.randint(100000, 999999)
        
    save_session(session_id, username, room_code)
    
    response = RedirectResponse(url=f"/room/", status_code=303)
    response.set_cookie(key="session_id", value=session_id,httponly=True, max_age=74400,samesite="Lax",)  # Store session ID in a cookie
    
    return response

@app.get("/room/", response_class=HTMLResponse)
def room(request: Request):
    session_id = request.cookies.get("session_id")
    print(session_id,'session_id')
    user_data = get_session(session_id)
    room_code = user_data.room_code
    room_code=int(room_code)
    
    if not user_data:
        return RedirectResponse(url="/")  # Redirect if no session exists
    users = db.query(UserSession).filter_by(room_code=room_code).all()
    users_in_room = []
    for user in users:
        users_in_room.append(user.username)
    return templates.TemplateResponse("room.html", {"request": request, "user": user_data, "users": users_in_room})

@app.get("/logout")
def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    db.query(UserSession).filter_by(session_id=session_id).delete()
    db.commit()
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")  # Remove cookie
    return response
