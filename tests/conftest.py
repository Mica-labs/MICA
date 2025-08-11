import sys
import os
# Add the project root to the Python path so that 'mica' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from typing import Text
from mica.bot import Bot
from mica.utils import read_yaml_file
from mica import parser
import glob


@pytest.fixture
def load_bot_from_folder():
    """Fixture that provides a function to load a bot from a folder."""

    def _load(bot_folder: Text) -> "Bot":
        """Loads a bot from a folder."""
        
        bot_name = os.path.basename(bot_folder)
        
        # Fuzzy match for agents file (any .yml or .yaml except config.yml)
        agents_file = None
        for pattern in ("*.yml", "*.yaml"):
            for f in glob.glob(os.path.join(bot_folder, pattern)):
                if os.path.basename(f) != "config.yml":
                    agents_file = f
                    break
            if agents_file:
                break
        
        # Fuzzy match for tools file (any .py file)
        tool_files = glob.glob(os.path.join(bot_folder, "*.py"))
        tools_file = tool_files[0] if tool_files else None

        config_file = os.path.join(bot_folder, "config.yml")
        
        data = None
        if agents_file and os.path.exists(agents_file):
            yaml_data = read_yaml_file(agents_file)
            data = parser.parse_agents(yaml_data)
            
        tool_code = None
        if tools_file and os.path.exists(tools_file):
            with open(tools_file, "r") as f:
                tool_code = f.read()

        config = None
        if os.path.exists(config_file):
            config = read_yaml_file(config_file)

        return Bot.from_json(
            name=bot_name,
            data=data,
            tool_code=tool_code,
            config=config,
        )
    return _load


@pytest.fixture
def test_bot_zip_file(tmp_path):
    """Creates a temporary zip file containing a simple bot for testing deployment."""
    import zipfile
    
    bot_dir = tmp_path / "test_bot_project"
    bot_dir.mkdir()

    # Create dummy files for a valid bot
    (bot_dir / "agents.yml").write_text("""
flow:
  type: flow agent
  steps:
    - bot: "flow_agent"

llm:
  type: llm agent
  prompt: "You are a helpful assistant."

kb:
  type: kb agent
  faq:
    - q: This is a question.
      a: This is an answer.

ensemble:
  type: ensemble agent
  contains:
    - flow
    - llm
    - kb
main:
  type: flow agent
  steps:
    - call: ensemble
""")
    (bot_dir / "config.yml").write_text("""
bot_name: test_deploy_bot
unsafe_mode: true
""")
    (bot_dir / "tools.py").write_text("""
def dummy_tool():
    return "this is a test tool"
""")

    zip_path = tmp_path / "test_bot.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(bot_dir / "agents.yml", "agents.yml")
        zipf.write(bot_dir / "config.yml", "config.yml")
        zipf.write(bot_dir / "tools.py", "tools.py")

    return zip_path 