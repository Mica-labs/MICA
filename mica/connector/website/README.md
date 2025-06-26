# MICA Website Chatbot Integration Component

MICA web chatbot integration component that embeds chatbots into any website through simple script tags.

## Features

- 🚀 Plug-and-play, simple integration
- 💬 Floating chat window
- 📱 Responsive design
- 🎨 Customizable themes
- 🌐 Cross-domain support

## Quick Start

### 1. Start MICA Service

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=<your_api_key>
python -m mica.server
```

### 2. Integrate Chatbot into Your Website

Add the following code to your HTML page:

- If you're running MICA with Docker, visit http://your_mica_server/chatbot/deploy.html, select your bot and generate the integration script.

```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Website</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <!-- Your webpage content -->
    <h1>Welcome to My Website</h1>
    <p>This is your webpage content...</p>

    <!-- MICA Chatbot Integration Script -->
    <script>
        const SERVER = 'http://localhost';  // MICA server address
        const CHATBOT_CONFIG = {
            config: "Your bot configuration ID",  // Base64 encoded bot configuration
            server: SERVER,
            minimize: false,  // Whether to minimize by default
            tooltip: "Click to start conversation"  // Hover tooltip text
        };
        
        function loadChatbot() {
            const script = document.createElement('script');
            script.src = SERVER + '/chatbot/static/js/sdk.js';
            script.onload = function() {
                if (typeof Chatbot !== 'undefined') {
                    Chatbot.initialize(CHATBOT_CONFIG);
                }
            };
            document.head.appendChild(script);
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', loadChatbot);
        } else {
            loadChatbot();
        }
    </script>
</body>
</html>
```

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

## Debugging and Testing

The project includes a debug page `debugging.html`. You can:

1. Start MICA service
2. Open `debugging.html` in your browser
3. Test the chatbot integration effect

## Troubleshooting

### Common Issues

1. **Chat window not displaying**
   - Check if MICA service is running properly
   - Confirm server address configuration is correct

## Contributing

Welcome to submit Issues and Pull Requests to improve this component!

---

For more information, please refer to [MICA Main Project Documentation](https://mica-labs.github.io/).
        
        