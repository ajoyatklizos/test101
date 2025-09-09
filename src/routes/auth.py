from fastapi import (
    APIRouter,
    Depends, 
    HTTPException, 
    status,
    Body
)
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Optional
from schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenMod
)
from database.db import get_db
from services import auth
router = APIRouter()

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = auth.register_user(db, user)
    if db_user:
        return user
    else:
        return {"Generally Normal People Register Once !"}


@router.post("/refresh")
def refresh_token(token: TokenMod, db: Session = Depends(get_db)):
    payload = auth.decode_token(token.token, expected_type="refresh")
    username: str = payload.get("sub")
    user = db.query(auth.User).filter(auth.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/login2")
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


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    users = db.query(auth.User).all()
    return users