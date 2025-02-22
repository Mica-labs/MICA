import logging
from typing import Text, Dict, Optional, Any

from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

from mica.action import custom_functions
from mica.manager import Manager

log = logging.getLogger(__name__)

api_description = """LLM Chatbot Action Server API."""

app = FastAPI(
    title="LLM Chatbot Action Server API",
    description=api_description,
    version="0.1.0",
)


class RequestBody(BaseModel):
    function: Text
    args: Optional[Dict] = None


@app.post("/v1/action")
def chat(body: RequestBody):
    function = body.function
    kwargs = body.args
    result = custom_functions.point_to_func(function, **kwargs)
    return result


if __name__ == "__main__":
    uvicorn.run("action:app", port=5050, host="0.0.0.0", log_level="info")
