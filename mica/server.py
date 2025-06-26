import io
import logging
import os
import traceback
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
from mica.utils import read_yaml_string, logger, read_yaml_file
from mica.connector.facebook import verify_facebook_webhook, handle_facebook_webhook
from mica.connector.slack import handle_slack_webhook

api_description = """MICA Server API."""

app = FastAPI(
    title="MICA Server API",
    description=api_description,
    version="0.1.0",
)

# Initialize the manager
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


# Directory to store deployed bots
BOTS_DIR = os.path.join(os.getcwd(), "deployed_bots")

# Ensure the bots directory exists
os.makedirs(BOTS_DIR, exist_ok=True)

@app.post("/v1/deploy")
async def deploy_zip(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    try:
        # Read uploaded file content to memory
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)

        # Extract bot information from zip
        with zipfile.ZipFile(zip_buffer) as zip_ref:
            # Get files list
            file_list = zip_ref.namelist()
            data = None
            python_script = None
            config = None

            # Read Python file content
            for f in file_list:
                if f.endswith('.py'):
                    python_script = zip_ref.read(f).decode('utf-8')

            # Read YAML file content
            if 'agents.yml' in file_list:
                data_content = zip_ref.read('agents.yml').decode('utf-8')
                data = read_yaml_string(data_content)

            if 'config.yml' in file_list:
                config_content = zip_ref.read('config.yml').decode('utf-8')
                config = read_yaml_string(config_content)

            # Determine bot name
            if config is not None and config.get('bot_name'):
                bot_name = config.get('bot_name')
                del config['bot_name']
            else:
                bot_name = Path(file.filename).stem

            llm_config = config.get('llm_config')
            connector = {key: value for key, value in config.items() if key in ['facebook', 'slack']}

            # Create a directory for this bot
            bot_dir = os.path.join(BOTS_DIR, bot_name)
            os.makedirs(bot_dir, exist_ok=True)
            
            # Save the bot files
            if data:
                with open(os.path.join(bot_dir, 'agents.yml'), 'w') as f:
                    f.write(data_content)
            
            if config:
                with open(os.path.join(bot_dir, 'config.yml'), 'w') as f:
                    f.write(config_content)
            
            if python_script != None:
                with open(os.path.join(bot_dir, 'functions.py'), 'w') as f:
                    f.write(python_script)
            
            # Load the bot
            manager.load(bot_name=bot_name,
                         data=data,
                         llm_config=llm_config,
                         python_script=python_script,
                         connector=connector)

        return ResponseBody(status=200, message=f"Successfully deployed bot: {bot_name}")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/slack/webhook/{bot}")
async def slack_webhook(bot: Text, request: Request):
    return await handle_slack_webhook(request, bot, manager)

@app.get("/v1/facebook/webhook/{bot}")
async def facebook_verify_webhook(bot: str, request: Request):
    return await verify_facebook_webhook(request, bot, manager)

@app.post("/v1/facebook/webhook/{bot}")
async def facebook_webhook(bot: str, request: Request):
    # 获取请求体数据
    return await handle_facebook_webhook(request, bot, manager)

@app.post("/v1/chat")
async def chat(request: Request, body: ChatRequest):
    sender = body.sender
    message = body.message
    logger.info(f"Received message from {sender}: {message} for {request.headers}")
    bot = request.headers.get("bot_name")

    response = await manager.chat(bot, sender, message)
    # this response needs to be encoded in utf-8
    return JSONResponse(content=response, media_type="application/json;charset=utf-8")


@app.get("/v1/bots")
async def get_bots():
    return JSONResponse(content=list(manager.bots.keys()), media_type="application/json;charset=utf-8")


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


# Load all deployed bots when starting the server
@app.on_event("startup")
async def startup_event():
    # Check if the bots directory exists
    if not os.path.exists(BOTS_DIR):
        logger.info(f"Bots directory {BOTS_DIR} does not exist. No bots loaded.")
        return
        
    # Get all subdirectories (each represents a bot)
    bot_dirs = [d for d in os.listdir(BOTS_DIR) 
               if os.path.isdir(os.path.join(BOTS_DIR, d))]
    
    if not bot_dirs:
        logger.info("No deployed bots found in the bots directory.")
        return
    
    # Track successfully loaded bots
    loaded_bots = []
    
    # Load each bot from its directory
    for bot_dir_name in bot_dirs:
        try:
            bot_dir = os.path.join(BOTS_DIR, bot_dir_name)
            
            # Load bot configuration
            data = None
            config = None
            python_script = ""
            
            # Load agents.yml
            agents_path = os.path.join(bot_dir, 'agents.yml')
            if os.path.exists(agents_path):
                data = read_yaml_file(agents_path)
            
            # Load config.yml
            config_path = os.path.join(bot_dir, 'config.yml')
            if os.path.exists(config_path):
                config = read_yaml_file(config_path)
            
            # Load functions.py
            functions_path = os.path.join(bot_dir, 'functions.py')
            if os.path.exists(functions_path):
                with open(functions_path, 'r') as f:
                    python_script = f.read()
            
            # Determine bot name and config
            if config and config.get('bot_name'):
                bot_name = config.get('bot_name')
            else:
                bot_name = bot_dir_name
            
            llm_config = config.get("llm_config", {}) if config else {}
            connector = {key: value for key, value in config.items() if key in ['facebook', 'slack']}
            # Load the bot
            if data:  # Only load if we have agent definitions
                try:
                    manager.load(bot_name=bot_name,
                                          data=data,
                                          llm_config=llm_config,
                                          python_script=python_script,
                                          connector=connector)
                    logger.info(f"Loaded bot: {bot_name} from {bot_dir}")
                    loaded_bots.append(bot_name)
                except Exception as e:
                    logger.error(f"Error loading bot {bot_name} from {bot_dir}: {str(e)}")
                    traceback.print_exc()
                    # Continue with other bots
            else:
                logger.warning(f"Skipping bot {bot_name}: No agent definitions found in {bot_dir}")
        except Exception as e:
            # Catch any exceptions during the loading process for this bot
            # and continue with other bots
            logger.error(f"Unexpected error loading bot from {bot_dir_name}: {str(e)}")
    
    if loaded_bots:
        logger.info(f"Successfully loaded {len(loaded_bots)} bots: {', '.join(loaded_bots)}")
    else:
        logger.warning("No bots were successfully loaded.")


if __name__ == "__main__":
    uvicorn.run("mica.server:app", port=5001, host="0.0.0.0", log_level="info")
