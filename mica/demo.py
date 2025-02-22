import asyncio
import glob
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog
from PyQt5.QtWidgets import QApplication, QFileDialog

import gradio as gr
import yaml

from mica import parser
from mica.bot import Bot

import random
import string

from mica.channel import GradioChannel
from mica.parser import Validator
from mica.utils import logger


def generate_random_string(length=6):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


def save_text_to_file(text):

    return f"./"


def generate_bot(bot_name, yaml_input, code=None):
    try:
        parsed_yaml = yaml.safe_load(yaml_input)
        # validate
        validator = Validator()
        result = validator.validate(parsed_yaml)
        assert result == [], "Did not pass the validation."
        # convert
        parsed_agents = parser.parse_agents(parsed_yaml)
        bot = Bot.from_json(name=bot_name, data=parsed_agents, tool_code=code)
        gr.Info(f"Success generate bot {bot_name}", duration=3)
        return bot
    except AssertionError as e:
        msgs = [f"Error Type: {err.rule_name}, Message: {err.message}" for err in result]
        msgs_str = '\n'.join(msgs)
        raise gr.Error(f"Did not pass the validation. "
                       f"Identified the following potential issues: {msgs_str}", duration=5)
    except yaml.YAMLError as e:
        raise gr.Error(f"A valid YAML structure is required.", duration=5)


def save_bot(bot_name: str, agents: str, tools: str = None):
    try:
        # Create folder if it doesn't exist
        base_path = os.path.join("../bot_output", bot_name)
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
        gr.Info(f"Success save to {base_path}", duration=3)
    except OSError as e:
        raise gr.Error(f"Error creating folders or saving files: {str(e)}", duration=5)


def load_bot(files):
    if len(files) == 0:
        return None, "", "", ""

    try:
        tools = ""
        agents = ""
        bot_name = None

        for file_path in files:
            if os.path.isdir(file_path) and not bot_name:
                bot_name = os.path.basename(file_path)
            if os.path.isfile(file_path):
                try:
                    if file_path.endswith('.py'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            tools += f.read()

                    if file_path.endswith('.yml') or file_path.endswith('.yaml'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            agents = f.read()
                except Exception as e:
                    gr.Error(f"Cannot load file {file_path}: {str(e)}\n")

        return generate_bot(bot_name, agents, tools), bot_name, agents, tools

    except Exception as e:
        logger.error(f"Failed to load bot: {bot_name} from disk, {e}")
        return None, "", "", ""

async def get_response(message, history, bot, user_id):
    if not isinstance(bot, Bot) or not message:
        return "", history, user_id, None
    if len(history) == 0:
        user_id = generate_random_string(7)
    gradio_channel = GradioChannel(history)
    bot_response = await bot.handle_message(user_id, message, channel=gradio_channel)
    bot_message = "\n".join(bot_response)
    await gradio_channel.send_message(bot_message, user=message)
    # history.append((message, bot_message))
    print("updated history", history)
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


def load_example_bot_names(file_path="../examples"):
    # make sure the file path exists
    if not os.path.exists(file_path):
        logger.error(f"Path {file_path} does not exists.")
        return

    # get all the bot names (directory names)
    directories = [d for d in os.listdir(file_path)
                   if os.path.isdir(os.path.join(file_path, d))]

    return directories or []


if __name__ == '__main__':
    examples = load_example_bot_names()
    with gr.Blocks(theme=gr.themes.Base()) as demo:
        with gr.Row():
            with gr.Column():
                file_loader = gr.FileExplorer(root_dir="../examples", glob="*", label="Open")
                bot_name = gr.Textbox(label="Enter Bot Name", lines=1, value="Default bot")
                yaml_input = gr.Code(value="""book_restaurant:
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
  description: You can select an agent to response user's question.
  steps:
  - bot: Hello, I am your intelligent assistant. What can I do for you?

main:
  steps:
  - call: meta
    schedule: priority
""", label="Enter agents.yml", language="yaml", lines=15)
                code_input = gr.Code(label="Enter tools.py", language="python", lines=10)
                bot = gr.State(None)

            with gr.Column():
                with gr.Row():
                    submit_btn = gr.Button("Run")
                    save_btn = gr.Button("Save")
                # folder_dropdown = gr.Dropdown(
                #     choices=examples,
                #     label="Generate from Examples"
                # )
                tracker = gr.Textbox(label="States", interactive=False, lines=1)
                chatbot = gr.Chatbot(height=600)
                msg = gr.Textbox(label="You")
                clear = gr.ClearButton([msg, chatbot], value="Clear the conversation")
                user_id = gr.State("default")

            msg.submit(get_response, [msg, chatbot, bot, user_id], [msg, chatbot, user_id, tracker])
            submit_btn.click(generate_bot, [bot_name, yaml_input, code_input], [bot])
            save_btn.click(save_bot, [bot_name, yaml_input, code_input])
            file_loader.change(load_bot, inputs=file_loader, outputs=[bot, bot_name, yaml_input, code_input])

    import uvloop  # 替代默认的 asyncio 循环，提升性能
    uvloop.install()
    demo.launch(share=False)
