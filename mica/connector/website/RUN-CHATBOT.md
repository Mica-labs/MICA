
# MICA Website Chatbot Integration Component

MICA web chatbot integration component that embeds chatbots into any website through simple script tags.

## Features

- 🚀 Plug-and-play, simple integration
- 💬 Floating chat window
- 📱 Responsive design
- 🎨 Customizable themes
- 🌐 Cross-domain support

## Quick Start

### Local Development with Nginx (Recommended)

#### 1. Prerequisites
- Nginx

#### 3. Build Chatbot Static Files

```bash
# Navigate to the website directory
cd mica/connector/website

# Build the chatbot SDK and static files
./scripts/build-static.sh
```
**Note**: This build process will generate static files in the docker/dist directory, which will be used in the Nginx configuration below.

#### 4. Configure Nginx

Create a nginx configuration file `/usr/local/etc/nginx/nginx.conf` (macOS with Homebrew) or `/etc/nginx/nginx.conf` (Linux):

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # Allow underscores in header names
    underscores_in_headers on;

    server {
        listen 8090;
        server_name localhost;
        
        # Allow underscores in header names
        underscores_in_headers on;

        # API routes forward to backend service
        location /v1/ {
            proxy_pass http://127.0.0.1:5001;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        # Chatbot static files service
        location /chatbot {
            alias /path/to/your/MICA/docker/dist;  # Update this path
            try_files $uri $uri/ /index.html;
            index index.html;
            
            # Set static file cache
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
        
        # Root path forward to UI service
        location / {
            proxy_pass http://127.0.0.1:7860;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

**Important**: Update the `/path/to/your/MICA/docker/dist` path to your actual MICA project path.

#### 5. Start Services

Start services in the following order:

```bash
# Terminal 1: Start MICA Core Service
python -m mica.server

# Terminal 2: Start MICA UI Service
python -m mica.demo

# Terminal 3: Start Nginx
nginx
# Or on macOS with Homebrew:
brew services start nginx
```

#### 6. Access Services

- **Web Interface**: http://localhost:8090
- **API Service**: http://localhost:5001
- **Embedded Chat Widget Generator**: http://localhost:8090/chatbot/deploy.html


## Debugging and Testing

### Using the Debug Page

The project includes a debug page `debugging.html`. You can:

1. Start MICA service (with Nginx)
2. Generate chatbot integration script from http://localhost:8090/chatbot/deploy.html
3. Copy the generated script and paste it into `debugging.html` to replace the existing script section
4. Open `debugging.html` in your browser
5. Test the chatbot integration effect

## Project Structure

```
website/
├── packages/
│   ├── sdk/                 # Chatbot SDK
│   │   ├── src/
│   │   │   └── index.js     # Main SDK code
│   │   ├── package.json
│   │   └── rollup.config.js # Build configuration
│   └── ava/                 # Frontend application
│       ├── src/
│       ├── public/
│       └── package.json
├── scripts/
│   └── build-static.sh      # Build script
├── debugging.html           # Debug page example
└── README.md               # This document
```

## Local Development Setup

### Directory Structure for Nginx

Ensure your MICA project has the following structure for chatbot static files:

```
MICA/
├── docker/
│   ├── dist/                # Chatbot static files
│   │   ├── index.html
│   │   ├── deploy.html
│   │   ├── static/
│   │   │   ├── js/
│   │   │   │   └── sdk.js   # Chatbot SDK
│   │   │   └── css/
│   │   └── ...
│   └── nginx.conf           # Nginx configuration reference
└── mica/
    └── connector/
        └── website/
```


## Troubleshooting

### Common Issues

1. **Chat window not displaying**
   - Check if MICA service is running properly
   - Confirm server address configuration is correct
   - Verify nginx is serving static files from correct path
   - Check browser console for JavaScript errors

2. **Nginx configuration issues**
   - Verify the alias path in nginx.conf points to your actual MICA docker/dist directory
   - Ensure nginx has read permissions for the static files directory
   - Check nginx syntax: `nginx -t`

3. **Port conflicts**
   - Ensure ports 5001, 7860, and 8090 are not occupied by other services
   - Use `lsof -i :PORT_NUMBER` to check port usage

4. **Static files not found**
   - Verify the `docker/dist` directory exists and contains chatbot files
   - Run the build process if static files are missing
   - Check file permissions

### Service Management

```bash
# Stop nginx (macOS with Homebrew)
brew services stop nginx

# Restart nginx
nginx -s reload

# Stop MICA services
# Use Ctrl+C in the respective terminal windows
```

## Contributing

Welcome to submit Issues and Pull Requests to improve this component!

---

For more information, please refer to [MICA Main Project Documentation](https://mica-labs.github.io/).

        