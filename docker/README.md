# MICA Docker Image

## Image Description

MICA Docker image is a complete multi-intelligent conversational agent system that includes the following components:

- **MICA Core Service**: Multi-agent conversational system based on Agent Declarative Language (ADL)
- **Web UI Interface**: Provides visual robot design and management interface & chatbot
- **Nginx Reverse Proxy**: Handles HTTP requests and static file services
- **Supervisord Process Management**: Manages multiple service processes within the container

## Port Description

- **5001**: MICA core API service port
- **80**: Nginx web service port, provides frontend interface access

## Directory Mounting

- `/mica/logs`: System log directory, contains running logs of all services
- `/mica/deployed_bots`: Deployed bot configuration files directory

## Running Instructions

### Basic Running

```bash
docker run -d \
  -v ./logs:/mica/logs \
  -v ./bots:/mica/deployed_bots \
  -e OPENAI_API_KEY=<your key> \
  -p 5001:5001 \
  -p 8090:80 \
  --name mica \
  micalabs/mica:latest      
```

### Parameter Description

- `-v ./logs:/mica/logs`: Mount log directory to local for easy log viewing
- `-v ./bots:/mica/deployed_bots`: Mount bot configuration directory for data persistence
- `-p 5001:5001`: Map MICA API service port
- `-p 8090:80`: Map web interface & chatbot port to local port 8090
- `--name mica`: Specify container name

### Access Methods

After successful startup, you can access through the following ways:

- **Web Interface**: http://localhost:8090
- **API Service**: http://localhost:5001
- **Embedded Chat Widget Generator**: http://localhost:8090/chatbot/deploy.html - Generate web embedded chat widgets for running MICA bots

## Environment Requirements

Before running, please ensure:

1. OpenAI API Key environment variable is set
2. Local ports 5001, 8090 are not occupied
3. Sufficient disk space for logs and bot data storage

## Log Viewing

After the container is running, you can view the running status of each service through the mounted logs directory:

- `supervisord.log`: Process manager log
- `mica.out.log` / `mica.err.log`: MICA core service logs
- `mica-ui.out.log` / `mica-ui.err.log`: UI interface service logs
- `nginx.out.log` / `nginx.err.log`: Web server logs
```