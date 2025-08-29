from fastapi import FastAPI, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base
import uuid  
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

Base.metadata.create_all(bind=engine) 

def save_session(session_id, username, room_code):
    db = SessionLocal()
    user_session = UserSession(session_id=session_id, username=username, room_code=room_code)
    db.add(user_session)
    db.commit()
    db.close()
db = SessionLocal()
def get_session(session_id):
    db = SessionLocal()
    session_data = db.query(UserSession).filter_by(session_id = session_id).first()
    db.close()
    return session_data

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    
    return templates.TemplateResponse("welcome.html", {"request": request})
@app.post("/", response_class=HTMLResponse)
def check_name(request: Request, username: str = Form(...)):
    if db.query(UserSession).filter_by(username = username).first():
        print('hi')
        return templates.TemplateResponse("welcome.html", {"status": "Username already exists", "request": request}) 
    return templates.TemplateResponse("home.html", {"request": request, "name": username})
@app.post("/create-room/{username}")
def create_room(response: Response,request: Request, username: str, room_code: str = Form(...)):
    print(room_code,'room_code')
    session_id = str(uuid.uuid4())  
    
    if room_code:
        room_code = int(room_code)
        ses = db.query(UserSession).filter_by(room_code = room_code).first()
        if not ses:                                      
            print('not')
            return templates.TemplateResponse("home.html", {"status": "Room code does not exist", "request": request, "name": username})

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
        return RedirectResponse(url="/")  
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
    response.delete_cookie("session_id")  
    return response
