from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from run_ai_employee import execute_task

app = FastAPI()


class TaskRequest(BaseModel):
    message: str


@app.post("/run")
def run_task(request: TaskRequest):
    try:
        res = execute_task(request.message)

        return {
            "decision": res.get("action"),
            "result": res.get("result"),
            "success": res.get("success", True)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {
        "status": "AI Employee API running",
        "endpoint": "/run",
        "method": "POST"
    }