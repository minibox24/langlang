from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

from core import Languages, run, setup, get_images
import aiodocker


class EvalData(BaseModel):
    language: str
    code: str
    inputs: Optional[List[str]] = []


app = FastAPI()
docker = aiodocker.Docker()


@app.get("/languages")
async def languages():
    return {"languages": await get_images(docker)}


@app.post("/eval")
def run_eval(data: EvalData):
    try:
        lang = Languages.find(data.language)
    except ValueError:
        return {"status": "error", "result": "NOT_SUPPORT_LANGUAGE"}, 400

    status, result = run(client, data.code, lang, data.inputs)

    return {"status": status.value, "result": result}


# setup(client)
