import io
import logging
import os
import uuid
import zipfile
from pathlib import Path
from typing import Text, Dict, Optional, Any

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from mica.channel import WebSocketChannel
from mica.manager import Manager
from mica.utils import read_yaml_string, logger

api_description = """LLM Chatbot Server API."""

app = FastAPI(
    title="LLM Chatbot Server API",
    description=api_description,
    version="0.1.0",
)

manager = Manager()


class DeployRequest(BaseModel):
    project_name: Text
    account: Dict
    data: Optional[Dict]


class ChatRequest(BaseModel):
    sender: Text
    message: Text


class ResponseBody(BaseModel):
    status: int
    message: Text
    data: Optional[Any] = None


@app.post("/v1/deploy")
async def deploy_zip(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    try:
        # 读取上传的文件内容到内存
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)

        # unzip in memory
        with zipfile.ZipFile(zip_buffer) as zip_ref:
            # get files list
            file_list = zip_ref.namelist()
            data = None
            python_script = None
            config = None

            # read Python file content
            for f in file_list:
                if f.endswith('.py'):
                    python_script = zip_ref.read(f).decode('utf-8')

            # read YAML file content
            if 'agents.yml' in file_list:
                data_content = zip_ref.read('agents.yml').decode('utf-8')
                data = read_yaml_string(data_content)

            if 'config.yml' in file_list:
                config_content = zip_ref.read('config.yml').decode('utf-8')
                config = read_yaml_string(config_content)

            if config is not None:
                bot_name = config.get('bot_name')
            else:
                bot_name = Path(file.filename).stem
            gpt_config = config.get("gptConfig")
            manager.load(bot_name, data, gpt_config, python_script)

        return ResponseBody(status=200, message=f"Already deploy project: {bot_name}.")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat")
async def chat(request: Request, body: ChatRequest):
    sender = body.sender
    message = body.message
    bot = request.headers.get("bot_name")
    response = await manager.chat(bot, sender, message)
    # this response needs to be encoded in utf-8
    return JSONResponse(content=response, media_type="application/json;charset=utf-8")


@app.websocket("/v1/ws/chat/{bot}")
async def chat_ws(websocket: WebSocket, bot):
    # generate unique id for each connection
    sender = str(uuid.uuid4())
    await websocket.accept()
    websocket_channel = WebSocketChannel(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.chat(bot, sender, message, websocket_channel)
    except WebSocketDisconnect:
        print(f"Client {sender} disconnected")


if __name__ == "__main__":
    uvicorn.run("server:app", port=5001, host="0.0.0.0", log_level="info")