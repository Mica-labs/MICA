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

import random
import string

from mica.channel import GradioChannel
from mica.parser import Validator
from mica.utils import logger

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
        msgs = [f"Error Type: {err.rule_name}, Message: {err.message}" for err in result]
        msgs_str = '\n'.join(msgs)
        raise gr.Error(f"Did not pass the validation. "
                       f"Identified the following potential issues: {msgs_str}", duration=10)
    except yaml.YAMLError as e:
        raise gr.Error(f"A valid YAML structure is required.", duration=10)
    except Exception as e:
        tb = traceback.format_exc()
        error_message = f"Unexpected error: {str(e)}\n\nTraceback:\n{tb}"
        raise gr.Error(error_message, duration=10)


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
        raise gr.Error(f"Error creating folders or saving files: {str(e)}", duration=10)


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
                        if "agent" in file_path:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                agents = f.read()
                        else:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                config = f.read()
                except Exception as e:
                    gr.Error(f"Cannot load file {file_path}: {str(e)}\n")
        if bot_name is None and files:
            first_path = files[0]
            if os.path.isfile(first_path):
                bot_name = os.path.basename(os.path.dirname(first_path))
        bot, chatbot, user_id, tracker = await generate_bot(bot_name, agents, tools, config, user_id)
        return bot, bot_name, agents, tools, config, chatbot, user_id, tracker

    except Exception as e:
        logger.error(f"Failed to load bot: {bot_name} from disk, {e}")
        logger.error(traceback.format_exc())
        gr.Error(f"Failed")
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
    with gr.Blocks(theme=gr.themes.Base()) as demo:
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
                log_output = gr.Textbox(label="Logs", interactive=False, lines=10, autofocus=False, autoscroll=True)
                demo.load(get_log_contents, None, log_output, every=2)
                chatbot = gr.Chatbot(height=600, layout="panel")
                msg = gr.Textbox(label="You")
                clear = gr.ClearButton([msg, chatbot], value="Clear the conversation")
                user_id = gr.State("default")

        msg.submit(get_response, [msg, chatbot, bot, user_id], [msg, chatbot, user_id, tracker])
        submit_btn.click(generate_bot, [bot_name, yaml_input, code_input, config_input, user_id], [bot, chatbot, user_id, tracker])
        save_btn.click(save_bot, [bot_name, yaml_input, code_input, config_input])
        file_loader.change(load_bot, inputs=[file_loader, chatbot, user_id], outputs=[bot, bot_name, yaml_input, code_input, config_input, chatbot, user_id, tracker], trigger_mode="once", show_progress="hidden")

    demo.launch(share=False)
