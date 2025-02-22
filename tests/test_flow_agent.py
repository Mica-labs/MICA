import json
import unittest

from mica.bot import Bot
from mica.utils import read_yaml_file
from mica.agents.flow_agent import FlowAgent

class MyTestCase(unittest.TestCase):
    def test_flow_load(self):
        path = "./test_examples/flow_agent/bot_user.yml"
        data = read_yaml_file(path)
        print(data)
        flow = FlowAgent.from_dict(data["flow_agents"]["transfer_money"]["steps"])
        print(flow["main"].steps)

    def test_single_step_run(self):
        path = "./test_examples/flow_agent"
        bot = Bot.from_path(path)
        print(bot.agents)

if __name__ == '__main__':
    unittest.main()
