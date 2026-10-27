import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlmodel import Field, Session, SQLModel, create_engine, select

# In production these come from environment variables (set on the hosting platform)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-to-a-long-random-string-in-real-life")
ALGORITHM = "HS256"
TOKEN_MINUTES = 60

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///notes.db")
# Hosts like Render/Neon give "postgres://..." or "postgresql://..."; use the psycopg 3 driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
password_hash = PasswordHash.recommended()


class NoteCreate(SQLModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = ""


class NoteUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = None


class Note(NoteCreate, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)


class NoteOut(NoteCreate):
    id: int


class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=100)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str


class UserOut(SQLModel):
    id: int
    username: str


class Token(SQLModel):
    access_token: str
    token_type: str


SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- auth ----------
def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
) -> User:
    error = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error
    user = session.get(User, user_id)
    if user is None:
        raise error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@app.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, session: SessionDep):
    existing = session.exec(
        select(User).where(User.username == data.username)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(
        username=data.username,
        hashed_password=password_hash.hash(data.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
):
    user = session.exec(
        select(User).where(User.username == form.username)
    ).first()
    if user is None or not password_hash.verify(
        form.password, user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    return Token(access_token=create_token(user.id), token_type="bearer")


@app.get("/me", response_model=UserOut)
def read_me(current_user: CurrentUser):
    return current_user


# ---------- notes ----------
def find_note(note_id: int, session: Session, user: User) -> Note:
    note = session.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.post("/notes", response_model=NoteOut, status_code=201)
def create_note(data: NoteCreate, session: SessionDep, current_user: CurrentUser):
    note = Note.model_validate(data, update={"owner_id": current_user.id})
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@app.get("/notes", response_model=list[NoteOut])
def list_notes(session: SessionDep, current_user: CurrentUser):
    return session.exec(
        select(Note).where(Note.owner_id == current_user.id)
    ).all()


@app.get("/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, session: SessionDep, current_user: CurrentUser):
    return find_note(note_id, session, current_user)


@app.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int, changes: NoteUpdate, session: SessionDep, current_user: CurrentUser
):
    note = find_note(note_id, session, current_user)
    for key, value in changes.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, session: SessionDep, current_user: CurrentUser):
    note = find_note(note_id, session, current_user)
    session.delete(note)
    session.commit()