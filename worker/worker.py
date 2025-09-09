import redis
import json
import time
import os
import openai
from prometheus_client import (
    Counter, 
    Histogram,
    start_http_server
)
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/files")  # use shared volume
API_KEY=os.getenv("API_KEY", "")

TASKS_PROCESSED = Counter("worker_tasks_total", "Total tasks processed")
TASKS_FAILED = Counter("worker_tasks_failed", "Total tasks failed")
TASK_DURATION = Histogram("worker_task_duration_seconds", "Task processing duration (seconds)")

# os.makedirs(UPLOAD_DIR, exist_ok=True)    
redis_conn = redis.from_url(REDIS_URL)

client = openai.OpenAI(api_key=API_KEY)


def extract_entities(text: str) -> dict:
    """Use OpenAI to extract structured entities from text."""
    prompt = f"""
    Extract structured entities from the following resume extracted text. 
    Respond in JSON format with keys: people, organizations, locations, dates, emails, phones, skills, projects, experiences and many more.

    Text:
    {text[:2000]}  # limit text length for token safety
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",   # lightweight + cheap
        messages=[
            {"role": "system", "content": "You are an information extraction engine."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    try:
        entities = json.loads(response.choices[0].message.content)
    except Exception as e:
        try:
            entities = json.loads(response.choices[0].message.content[7:-3])
        except Exception as e:
            
            print(response.choices[0].message.content[7:-3])
            TASKS_FAILED.inc()
            entities = {"error": "Failed to parse entities"}

    return entities



def extract_text(file_path: str) -> str:
    """Simple text extractor (supports PDFs, fallback for others)."""
    if file_path.endswith(".pdf") and PyPDF2:
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text.strip()

    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    return "Text extraction not supported for this file type."


def process_task(task_id: str):
    job_raw = redis_conn.get(f"task:{task_id}")
    if not job_raw:
        return

    job_data = json.loads(job_raw)
    file_path = job_data["file_path"]


    # Update status -> processing
    job_data["status"] = "processing"
    redis_conn.set(f"task:{task_id}", json.dumps(job_data))

    # Extract text
    text = extract_text(file_path)
    
    # Save result
    job_data["status"] = "done"
    
    entities = extract_entities(text)
    job_data["result"] = {"extracted_text": entities}
    redis_conn.set(f"task:{task_id}", json.dumps(job_data))
    
    return entities


def main():
    print("[Worker] Started, waiting for tasks...")
    start_http_server(8001)
    while True:
        t1=time.time()
        task = redis_conn.brpop("task_queue", timeout=5)
        if task:
            _, task_id = task
            ret=process_task(task_id.decode("utf-8"))  # decode bytes to str
            print(ret)
            TASKS_PROCESSED.inc()
            TASK_DURATION.observe(time.time()-t1)
        else:
            continue


if __name__ == "__main__":
    main()
