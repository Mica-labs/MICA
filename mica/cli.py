#!/usr/bin/env python
"""
Command-line interface for MICA chatbot.

Usage:
    python -m mica.cli <bot_folder>
    python -m mica.cli examples/bookstore

The bot folder should contain:
    - agents.yml (required): Agent definitions
    - config.yml (optional): Configuration including LLM settings
    - tools.py (optional): Custom tool functions
"""

import argparse
import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Text

import yaml

from mica import parser
from mica.bot import Bot, InvalidBot
from mica.channel import ChatChannel
from mica.parser import Validator
from mica.utils import logger


class CLIChannel(ChatChannel):
    """Simple CLI channel for displaying messages."""
    
    def __init__(self):
        self.messages = []
    
    async def send_message(self, message) -> None:
        if isinstance(message, list):
            for msg in message:
                self.messages.append(msg)
                print(f"\033[94mBot:\033[0m {msg}")
        else:
            self.messages.append(message)
            print(f"\033[94mBot:\033[0m {message}")


def load_bot_from_folder(folder_path: Text) -> Bot:
    """
    Load a bot from a folder containing agents.yml, config.yml, and tools.py.
    
    Args:
        folder_path: Path to the bot folder
        
    Returns:
        Bot instance
        
    Raises:
        FileNotFoundError: If agents.yml is not found
        InvalidBot: If the bot configuration is invalid
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        raise FileNotFoundError(f"Bot folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    # Load agents.yml (required)
    agents_path = folder / "agents.yml"
    agents_yaml_path = folder / "agents.yaml"
    
    agents_content = None
    if agents_path.exists():
        with open(agents_path, 'r', encoding='utf-8') as f:
            agents_content = f.read()
    elif agents_yaml_path.exists():
        with open(agents_yaml_path, 'r', encoding='utf-8') as f:
            agents_content = f.read()
    else:
        # Try to find any yaml file that might be the agents file
        yaml_files = list(folder.glob("*.yml")) + list(folder.glob("*.yaml"))
        yaml_files = [f for f in yaml_files if "config" not in f.name.lower()]
        if yaml_files:
            with open(yaml_files[0], 'r', encoding='utf-8') as f:
                agents_content = f.read()
        else:
            raise FileNotFoundError(
                f"No agents.yml found in {folder_path}. "
                "Please ensure the folder contains an agents.yml file."
            )
    
    # Parse agents YAML
    try:
        agents_data = yaml.safe_load(agents_content)
    except yaml.YAMLError as e:
        raise InvalidBot(f"Invalid YAML in agents file: {e}")
    
    # Validate agents
    validator = Validator()
    errors = validator.validate(agents_data)
    if errors:
        error_messages = [f"  - [{err.rule_name}] {err.message} at {err.path}" for err in errors]
        raise InvalidBot(
            f"Validation errors in agents file:\n" + "\n".join(error_messages)
        )
    
    # Load config.yml (optional)
    config = {"unsafe_mode": True}  # Default config
    config_path = folder / "config.yml"
    config_yaml_path = folder / "config.yaml"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            if config_content.strip():
                config = yaml.safe_load(config_content)
    elif config_yaml_path.exists():
        with open(config_yaml_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            if config_content.strip():
                config = yaml.safe_load(config_content)
    
    # Ensure unsafe_mode is set if not specified
    if config is None:
        config = {"unsafe_mode": True}
    elif "unsafe_mode" not in config:
        config["unsafe_mode"] = True
    
    # Load tools.py (optional) - check for multiple possible names
    tools_code = None
    tool_files = ["tools.py", "tool.py", "functions.py"]
    
    for tool_file in tool_files:
        tool_path = folder / tool_file
        if tool_path.exists():
            with open(tool_path, 'r', encoding='utf-8') as f:
                tools_code = f.read()
            break
    
    # Also check for any .py files if no standard tool file found
    if tools_code is None:
        py_files = list(folder.glob("*.py"))
        if py_files:
            # Use the first Python file found
            with open(py_files[0], 'r', encoding='utf-8') as f:
                tools_code = f.read()
    
    # Determine bot name from folder name or config
    if config and config.get("bot_name"):
        bot_name = config.get("bot_name")
    else:
        bot_name = folder.name
    
    # Parse agents and create bot
    parsed_agents = parser.parse_agents(agents_data)
    
    bot = Bot.from_json(
        name=bot_name,
        data=parsed_agents,
        config=config,
        tool_code=tools_code
    )
    
    return bot


async def chat_loop(bot: Bot, user_id: str = "cli_user"):
    """
    Main chat loop for interacting with the bot.
    
    Args:
        bot: Bot instance to chat with
        user_id: User identifier for the conversation
    """
    channel = CLIChannel()
    
    print("\n" + "=" * 60)
    print(f"  MICA Chatbot CLI - {bot.name}")
    print("=" * 60)
    print("Type your message and press Enter to chat.")
    print("Commands:")
    print("  /quit, /exit, /q  - Exit the chatbot")
    print("  /reset, /clear    - Clear conversation history")
    print("  /help             - Show this help message")
    print("=" * 60 + "\n")
    
    # Check if there's an initial bot message (from bot steps)
    # Try to trigger any initial bot messages
    try:
        from mica.agents.flow_agent import FlowAgent
        from mica.agents.steps.bot import Bot as BotStep
        from mica.agents.steps.call import Call
        from mica.agents.ensemble_agent import EnsembleAgent
        
        main = bot.entrypoint
        needs_init = False
        
        if isinstance(main, FlowAgent):
            for step in main.subflows[main.main_flow_name].steps:
                if isinstance(step, BotStep):
                    needs_init = True
                    break
                if isinstance(step, Call):
                    initial_agent = bot.agents.get(step.name)
                    if isinstance(initial_agent, EnsembleAgent):
                        if initial_agent.steps is not None:
                            for s in initial_agent.steps:
                                if isinstance(s, BotStep):
                                    needs_init = True
                                    break
                    if isinstance(initial_agent, FlowAgent):
                        for s in initial_agent.subflows[initial_agent.main_flow_name].steps:
                            if isinstance(s, BotStep):
                                needs_init = True
                                break
                if needs_init:
                    break
        
        if needs_init:
            response = await bot.handle_message(user_id, "/init", channel=channel)
            if response:
                for msg in response:
                    if msg:
                        print(f"\033[94mBot:\033[0m {msg}")
    except Exception as e:
        logger.debug(f"No initial message: {e}")
    
    while True:
        try:
            # Get user input
            user_input = input("\033[92mYou:\033[0m ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ["/quit", "/exit", "/q"]:
                print("\nGoodbye!")
                break
            
            if user_input.lower() in ["/reset", "/clear"]:
                # Reset the tracker for this user
                bot.tracker_store.trackers.pop(user_id, None)
                print("\n[Conversation cleared]\n")
                continue
            
            if user_input.lower() == "/help":
                print("\nCommands:")
                print("  /quit, /exit, /q  - Exit the chatbot")
                print("  /reset, /clear    - Clear conversation history")
                print("  /help             - Show this help message\n")
                continue
            
            # Send message to bot
            response = await bot.handle_message(user_id, user_input, channel=channel)
            
            # Display response (if not already displayed by channel)
            if response and not channel.messages:
                for msg in response:
                    if msg:
                        print(f"\033[94mBot:\033[0m {msg}")
            
            # Clear channel messages for next iteration
            channel.messages = []
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n\033[91mError:\033[0m {e}")
            logger.debug(traceback.format_exc())


def main():
    """Main entry point for the CLI."""
    arg_parser = argparse.ArgumentParser(
        description="MICA Chatbot Command-Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m mica.cli examples/bookstore
  python -m mica.cli ./my_bot
  python -m mica.cli /path/to/bot/folder

The bot folder should contain:
  - agents.yml (required): Agent definitions
  - config.yml (optional): Configuration including LLM settings
  - tools.py (optional): Custom tool functions
        """
    )
    
    arg_parser.add_argument(
        "bot_folder",
        type=str,
        help="Path to the bot folder containing agents.yml, config.yml, and tools.py"
    )
    
    arg_parser.add_argument(
        "--user-id",
        type=str,
        default="cli_user",
        help="User ID for the conversation (default: cli_user)"
    )
    
    arg_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (show DEBUG logs, default is INFO only)"
    )
    
    args = arg_parser.parse_args()
    
    # Set logging level
    import logging
    
    # Suppress noisy third-party loggers (httpx, openai, urllib3, etc.)
    third_party_loggers = [
        'httpx', 'httpcore', 'openai', 'urllib3', 'requests',
        'asyncio', 'charset_normalizer', 'filelock'
    ]
    for lib_logger in third_party_loggers:
        logging.getLogger(lib_logger).setLevel(logging.WARNING)
    
    if args.verbose:
        # Enable DEBUG level for all loggers
        logging.getLogger().setLevel(logging.DEBUG)
        # Also set mica loggers to DEBUG
        for logger_name in ['mica', 'user_info', 'sys_info', 'bot_info']:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)
        # In verbose mode, also show third-party DEBUG logs
        for lib_logger in third_party_loggers:
            logging.getLogger(lib_logger).setLevel(logging.DEBUG)
    else:
        # Default: only show INFO and above
        logging.getLogger().setLevel(logging.INFO)
        for logger_name in ['mica', 'user_info', 'sys_info', 'bot_info']:
            logging.getLogger(logger_name).setLevel(logging.INFO)
    
    # Load the bot
    try:
        print(f"Loading bot from: {args.bot_folder}")
        bot = load_bot_from_folder(args.bot_folder)
        print(f"Bot '{bot.name}' loaded successfully!")
    except FileNotFoundError as e:
        print(f"\033[91mError:\033[0m {e}")
        sys.exit(1)
    except InvalidBot as e:
        print(f"\033[91mInvalid Bot:\033[0m {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\033[91mError loading bot:\033[0m {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)
    
    # Run the chat loop
    try:
        asyncio.run(chat_loop(bot, args.user_id))
    except Exception as e:
        print(f"\033[91mError:\033[0m {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

