from fastapi import FastAPI
from pydantic import BaseModel
from run_ai_employee import execute_task

app = FastAPI()

class TaskRequest(BaseModel):
    message: str

@app.post("/run")
async def run_task(request: TaskRequest):
    res = execute_task(request.message)
    return {
        "decision": res["action"],
        "result": res["result"],
        "success": res["success"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
