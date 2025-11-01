import asyncio
import json
import os
import traceback

import gradio as gr
import yaml

from mica import parser
from mica.agents.ensemble_agent import EnsembleAgent
from mica.agents.flow_agent import FlowAgent
from mica.agents.steps.call import Call
from mica.bot import Bot
from mica.llm.openai_model import NoValidRequestHeader
import random
import string

from mica.channel import GradioChannel
from mica.parser import Validator
import logging
# Use a specific logger for demo.py to enable left-aligned logs
demo_logger = logging.getLogger("mica.demo")

# use the web log function defined in utils.py
from mica.utils import get_web_log_contents, clear_web_log_contents

def get_log_contents():
    """Get the log contents for the frontend (only INFO level and above)"""
    return get_web_log_contents()


def generate_random_string(length=6):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))


async def generate_bot(bot_name, yaml_input, code, config_input, user_id):
    try:
        parsed_yaml = yaml.safe_load(yaml_input)
        # validate
        validator = Validator()
        result = validator.validate(parsed_yaml, code)
        assert result == [], "Did not pass the validation."
        # convert
        parsed_agents = parser.parse_agents(parsed_yaml)
        # by default: unsafe_mode on
        parsed_config = {"unsafe_mode": True}
        if config_input and config_input != "":
            parsed_config = yaml.safe_load(config_input)
        bot = Bot.from_json(name=bot_name, data=parsed_agents, tool_code=code, config=parsed_config)
        gr.Info(f"Success generate bot {bot_name}", duration=3)
        _, chatbot, user_id, tracker = await init_conversation(bot, [], user_id)
        return bot, chatbot, user_id, tracker
    except AssertionError as e:
        # Format validation errors with detailed guidance
        formatted_msgs = []
        for err in result:
            error_msg = f"[{err.rule_name} Error]\n"
            error_msg += f"   Problem: {err.message}\n"
            error_msg += f"   Location: {err.path}\n"
            
            # Add specific solutions based on error type
            if "Missing required key" in err.message:
                missing_key = err.message.split("'")[1]
                error_msg += f"   Solution: Add the required '{missing_key}' field to your agent configuration\n"
            elif "spelling error" in err.message.lower():
                error_msg += f"   Solution: Check your field names for typos. {err.message.split('.')[-1].strip()}\n"
            elif "Type mismatch" in err.message:
                error_msg += f"   Solution: {err.message}. Please correct the data type\n"
            elif "Invalid agent type" in err.message:
                valid_types = err.message.split("Valid types are: ")[1] if "Valid types are: " in err.message else "flow agent, llm agent, ensemble agent, kb agent"
                error_msg += f"   Solution: Use one of these valid agent types: {valid_types}\n"
            elif "cannot be null" in err.message:
                error_msg += f"   Solution: Provide a value for this field - it cannot be empty\n"
            else:
                error_msg += f"   Solution: Please review and correct the configuration according to the error message\n"
            
            formatted_msgs.append(error_msg)
        
        msgs_str = '\n'.join(formatted_msgs)
        raise gr.Error(f"Validation Failed\n\n{msgs_str}\nTip: Check the examples folder for reference configurations", duration=15)
    except yaml.YAMLError as e:
        error_details = str(e)
        line_info = ""
        
        # Extract line number information if available
        if hasattr(e, 'problem_mark') and e.problem_mark:
            line_info = f" at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}"
        
        # Provide specific guidance based on common YAML errors
        if "mapping values are not allowed" in error_details:
            solution = "Check for missing colons (:) after field names or incorrect indentation"
        elif "could not find expected" in error_details:
            solution = "Check for missing quotes around strings or unmatched brackets/braces"
        elif "found character that cannot start any token" in error_details:
            solution = "Check for invalid characters or incorrect indentation (use spaces, not tabs)"
        elif "expected <block end>" in error_details:
            solution = "Check your indentation - all items at the same level should have the same indentation"
        else:
            solution = "Verify your YAML syntax - check indentation, colons, and quotes"
        
        raise gr.Error(f"YAML Syntax Error{line_info}\n\nProblem: {error_details}\n\nSolution: {solution}\n\nTip: Use a YAML validator to check your syntax", duration=12)
    except NoValidRequestHeader:
        raise gr.Error(f"Did not find the OpenAI API key. Please set the OpenAI API key in the environment variables.", duration=12)
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Provide user-friendly messages for common errors
        if "Bot.from_json" in traceback.format_exc():
            user_message = f"Bot Creation Failed\n\nProblem: Failed to create bot from configuration\nError: {error_msg}\n\nSolutions:\n- Check that all referenced agents exist\n- Verify tool functions are properly defined\n- Ensure config.yml is valid"
        elif "parse_agents" in traceback.format_exc():
            user_message = f"Agent Parsing Failed\n\nProblem: Failed to parse agent definitions\nError: {error_msg}\n\nSolutions:\n- Check agent structure and syntax\n- Ensure all required fields are present\n- Verify step definitions are correct"
        elif "yaml.safe_load" in traceback.format_exc():
            user_message = f"Configuration Parsing Failed\n\nProblem: Failed to parse yaml file\nError: {error_msg}\n\nSolutions:\n- Check all yaml files syntax\n- Ensure proper YAML formatting\n"
        else:
            # For truly unexpected errors, still show traceback but make it more user-friendly
            tb = traceback.format_exc()
            user_message = f"Unexpected Error ({error_type})\n\nProblem: {error_msg}\n\nDebug Information:\n{tb}\n\nTip: If this persists, please report this issue with your chatbot program"
        
        raise gr.Error(user_message, duration=15)


async def init_conversation(bot: Bot, chatbot, user_id):
    from mica.agents.steps.bot import Bot as BotStep
    tracker = ""
    main = bot.entrypoint
    if isinstance(main, FlowAgent):
        for step in main.subflows[main.main_flow_name].steps:
            if isinstance(step, BotStep):
                _, chatbot, user_id, tracker = await get_response("/init", chatbot, bot, user_id)
            if isinstance(step, Call):
                initial_agent = bot.agents[step.name]
                if isinstance(initial_agent, EnsembleAgent):
                    if initial_agent.steps is not None:
                        for step in initial_agent.steps:
                            if isinstance(step, BotStep):
                                _, chatbot, user_id, tracker = await get_response("/init", chatbot, bot, user_id)
                if isinstance(initial_agent, FlowAgent):
                    for step in initial_agent.subflows[initial_agent.main_flow_name].steps:
                        if isinstance(step, BotStep):
                            _, chatbot, user_id, tracker = await get_response("/init", chatbot, bot, user_id)

    return "", chatbot, user_id, tracker


def save_bot(bot_name: str, agents: str, tools: str = None, config: str = None):
    try:
        # Create folder if it doesn't exist
        base_path = os.path.join("./bot_output", bot_name)
        os.makedirs(base_path, exist_ok=True)

        # Save agents.yml
        agents_path = os.path.join(base_path, 'agents.yml')
        with open(agents_path, 'w', encoding='utf-8') as f:
            f.write(agents)

        # Save tools.py if content is provided
        if tools is not None:
            tools_path = os.path.join(base_path, 'tools.py')
            with open(tools_path, 'w', encoding='utf-8') as f:
                f.write(tools)
        
        # Save config.yml if content is provided
        if config is not None:
            config_path = os.path.join(base_path, 'config.yml')
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config)
        gr.Info(f"Success save to {base_path}", duration=3)
    except OSError as e:
        error_msg = str(e)
        if "Permission denied" in error_msg:
            solution = "Check that you have write permissions to the bot_output directory"
        elif "No space left on device" in error_msg:
            solution = "Free up disk space and try again"
        elif "File name too long" in error_msg:
            solution = "Use a shorter bot name"
        else:
            solution = "Check file system permissions and available space"
        
        raise gr.Error(f"File Save Failed\n\nProblem: Cannot save bot files\nError: {error_msg}\n\nSolution: {solution}", duration=10)


async def load_bot(files, chatbot, user_id):
    if len(files) == 0:
        return None, "", "", "", "", "", user_id, ""
    try:      
        tools = ""
        agents = ""
        config = "unsafe_mode: true"
        bot_name = None

        for file_path in files:
            if os.path.isfile(file_path):
                try:
                    if file_path.endswith('.py'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            tools += f.read() + "\n"

                    if file_path.endswith('.yml') or file_path.endswith('.yaml'):
                        if "config" in file_path:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                config = f.read()
                        else:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                agents = f.read()
                except Exception as e:
                    error_msg = str(e)
                    file_type = "Python code" if file_path.endswith('.py') else "YAML configuration"
                    
                    if "UnicodeDecodeError" in str(type(e)):
                        solution = "File encoding issue - ensure the file is saved as UTF-8"
                    elif "PermissionError" in str(type(e)):
                        solution = "Permission denied - check file access permissions"
                    elif "FileNotFoundError" in str(type(e)):
                        solution = "File not found - ensure the file exists at the specified path"
                    else:
                        solution = f"Check {file_type} syntax and formatting"
                    
                    raise gr.Error(f"File Load Failed\n\nProblem: Cannot read {file_type} from {os.path.basename(file_path)}\nError: {error_msg}\n\nSolution: {solution}", duration=10)
        if bot_name is None and files:
            first_path = files[0]
            if os.path.isfile(first_path):
                bot_name = os.path.basename(os.path.dirname(first_path))
        bot, chatbot, user_id, tracker = await generate_bot(bot_name, agents, tools, config, user_id)
        return bot, bot_name, agents, tools, config, chatbot, user_id, tracker

    except Exception as e:
        demo_logger.error(f"Failed to load bot: {bot_name} from disk, {e}")
        demo_logger.error(traceback.format_exc())
        
        error_msg = str(e)
        
        # Find the most relevant error information
        if "generate_bot" in traceback.format_exc():
            user_message = f"Bot Loading Failed\n\nProblem: Failed to create bot from loaded files\nError: {error_msg}\n\nSolutions:\n- Check that agents.yml has correct structure\n- Verify tools.py has valid Python syntax\n- Ensure config.yml is properly formatted\n- Review file contents for any missing or invalid fields"
        elif "yaml.safe_load" in traceback.format_exc():
            user_message = f"YAML Parsing Failed\n\nProblem: Invalid YAML format in loaded files\nError: {error_msg}\n\nSolutions:\n- Check YAML syntax (indentation, colons, quotes)\n- Ensure proper structure in agents.yml or config.yml\n- Remove any special characters or formatting issues"
        else:
            user_message = f"Loading Failed\n\nProblem: Failed to load bot from selected files\nError: {error_msg}\n\nSolutions:\n- Check file permissions and accessibility\n- Verify file contents are valid\n- Try loading files individually to identify issues\n- Check the console logs for more details"
        
        raise gr.Error(user_message, duration=12)
        return None, bot_name or "", agents or "", tools or "", config or "", "", user_id, ""


async def get_response(message, history, bot, user_id):
    if not isinstance(bot, Bot) or not message:
        return "", history, user_id, None
    if len(history) == 0:
        user_id = generate_random_string(7)
    gradio_channel = GradioChannel(history)
    bot_response = await bot.handle_message(user_id, message, channel=gradio_channel)
    if bot_response is not None and len(bot_response) > 0:
        bot_message = "\n".join(bot_response)
    else:
        bot_message = ""
    if message == "/init":
        message = ""
    await gradio_channel.send_message(bot_message, user=message)
    return "", history, user_id, display_tracker_state(bot, user_id)


async def check_updates(history):
    flag = True
    while flag:
        await asyncio.sleep(1)
        print(history)
        # flag = False
        yield gr.update(history)


def display_tracker_state(bot, user_id):
    return json.dumps(bot.tracker_store.retrieve(user_id).args, indent=2)


if __name__ == '__main__':
    default_agents = """book_restaurant:
  type: llm agent
  description: This agent books a restaurant.
  prompt: |
    You are a smart agent for handling booking restaurant request. When user booking a restaurant, you need to gather the following information in each round of conversation: the restaurant name, the number of people, the reservation date, time, and whether the reservation can be flexible (i.e., whether the date is fixed). If flexibility is allowed, continue to inquire about alternative dates. The last information is reservation name. Once all the required information is collected, call the `check_restaurant_available` function, and finally confirm all the reservation details.
  args:
    - name_of_restaurant
    - number_of_people
    - date
    - time
    - is_date_flexible
    - alternative_dummy
    - reservation_name
  uses:
    - check_restaurant_available

meta:
  type: ensemble agent
  contains:
  - book_restaurant
  description: You can select an agent to respond to user's question.
  steps:
  - bot: Hello, I am your intelligent assistant. What can I do for you?

main:
  type: flow agent
  steps:
  - call: meta
"""
    with gr.Blocks(theme=gr.themes.Base(), css="""
        #log_output textarea {
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Courier New', monospace !important;
            font-size: 12px !important;
            line-height: 1.2 !important;
            white-space: pre !important;
            overflow-x: auto !important;
        }
        """) as demo:
        with gr.Row():
            with gr.Column():
                file_loader = gr.FileExplorer(root_dir="./examples", glob="**/*.*", label="Click any directory name to automatically load the bot. If it includes a knowledge base (KB), embedding may take some time.")
                bot_name = gr.Textbox(label="Enter Bot Name", lines=1, value="Default bot")
                yaml_input = gr.Code(value=default_agents, label="Enter agents.yml", language="yaml", lines=15)
                code_input = gr.Code(label="Enter tools.py", language="python", lines=10, value=None)
                config_input = gr.Code(value="""unsafe_mode: true""", label="Enter config.yml", language="yaml", lines=5)
                bot = gr.State(None)

            with gr.Column():
                with gr.Row():
                    submit_btn = gr.Button("Run")
                    save_btn = gr.Button("Save")
                tracker = gr.Textbox(label="States", interactive=False, lines=1)
                log_output = gr.Textbox(label="Logs", interactive=False, lines=10, autofocus=False, autoscroll=True, elem_id="log_output")
                demo.load(get_log_contents, None, log_output, every=2)
                chatbot = gr.Chatbot(height=600, layout="panel")
                msg = gr.Textbox(label="You")
                clear = gr.ClearButton([msg, chatbot], value="Clear the conversation")
                user_id = gr.State("default")

        msg.submit(get_response, [msg, chatbot, bot, user_id], [msg, chatbot, user_id, tracker])
        submit_btn.click(generate_bot, [bot_name, yaml_input, code_input, config_input, user_id], [bot, chatbot, user_id, tracker])
        save_btn.click(save_bot, [bot_name, yaml_input, code_input, config_input])
        file_loader.change(load_bot, inputs=[file_loader, chatbot, user_id], outputs=[bot, bot_name, yaml_input, code_input, config_input, chatbot, user_id, tracker], trigger_mode="once", show_progress="hidden")

    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
