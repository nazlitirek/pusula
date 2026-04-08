from fastapi import FastAPI
from database import engine
import models
from routers import auth, users

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)

@app.get("/")
def read_root():
    return {"message": "Pusula API çalışıyor! 🧭"}