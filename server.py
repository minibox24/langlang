from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import Optional, List

from core import Languages, Runner, setup, get_images
import docker


class EvalData(BaseModel):
    language: str
    code: str
    inputs: Optional[List[str]] = []


app = FastAPI()
client = docker.from_env()


@app.on_event("startup")
async def startup():
    await setup(client)


@app.get("/languages")
async def languages():
    return {"languages": await get_images(client)}


@app.post("/eval")
async def run_eval(data: EvalData, response: Response):
    try:
        lang = Languages.find(data.language)
    except ValueError:
        response.status_code = 400
        return {"status": "error", "result": "NOT_SUPPORT_LANGUAGE"}

    runner = Runner(client, lang, data.code, data.inputs)

    await runner.setup()

    await runner.compile()
    await runner.run()

    await runner.clear()

    return {"status": runner.status.value, "result": runner.result}
