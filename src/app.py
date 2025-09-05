from fastapi import FastAPI, Depends, HTTPException, status,Body
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Optional

from database.db import Base,engine,get_db
from schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenMod
)
from services import auth



app = FastAPI()
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)


@app.get("/")
def home(request: Request):
    return {
        "msg":"Welcome to Test101"
    }

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = auth.register_user(db, user)
    if db_user:
        return user
    else:
        return {"Generally Normal People Register Once !"}


@app.post("/refresh")
def refresh_token(token: TokenMod, db: Session = Depends(get_db)):
    payload = auth.decode_token(token.token, expected_type="refresh")
    username: str = payload.get("sub")
    user = db.query(auth.User).filter(auth.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}


@app.post("/login2")
def login_alt(userdata:UserLogin,db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, UserLogin(username=userdata.username, password=userdata.password))

    if not user:
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = auth.create_access_token(data={"sub": user.username})
    refresh_token = auth.create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@app.post("/login")
def login(
    form_data: Optional[OAuth2PasswordRequestForm] = Depends(lambda: None),
    json_data: Optional[UserLogin] = Body(default=None),
    db: Session = Depends(get_db)
):
    # Check if form-data login
    if form_data and form_data.username and form_data.password:
        username, password = form_data.username, form_data.password

    # Otherwise, check if JSON login
    elif json_data:
        username, password = json_data.username, json_data.password

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login request. Send JSON or form-data."
        )

    user = auth.authenticate_user(db, UserLogin(username=username, password=password))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = auth.create_access_token(data={"sub": user.username})
    refresh_token = auth.create_refresh_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    users = db.query(auth.User).all()
    return users
