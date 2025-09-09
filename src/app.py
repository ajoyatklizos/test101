from fastapi import FastAPI, Response
from prometheus_client import (
    Counter, 
    Histogram,
    Gauge, 
    generate_latest, 
    CONTENT_TYPE_LATEST
)
import time

from database.db import Base,engine

from routes import (
    resume,auth
)


app = FastAPI()

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])
REQUEST_GAUGE= Gauge("inprogress_requests","Total Number of inprogress requests")

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(process_time)
    REQUEST_GAUGE.inc()
    return response

@app.get("/metrics")
async def metrics():

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(router=resume.router, prefix="/api/resume")
app.include_router(router=auth.router)



