from fastapi import FastAPI

app = FastAPI(title="Research Agent API")

@app.get("/")
def root():
    return {"status": "ok", "service": "Research Agent"}