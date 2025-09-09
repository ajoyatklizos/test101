from fastapi import FastAPI


from database.db import Base,engine

from routes import (
    resume,auth
)


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)

app.include_router(router=resume.router, prefix="/api/resume")
app.include_router(router=auth.router)



