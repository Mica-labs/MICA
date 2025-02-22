import unittest

from mica.bot import Bot


class MyTestCase(unittest.TestCase):
    def test_bot1(self):
        path = "./test_examples/complaint"
        bot = Bot.from_path(path)
        print(bot.agents)

        self.assertEqual(3, len(bot.agents))  # add assertion here

        # chat with bot
        user_id = "tester"
        bot.handle_message(user_id, "The oranges are rotten. My order number is 102938")
        tracker = bot.tracker_store.retrieve(user_id)
        print(tracker.args)
        self.assertEqual("102938", tracker.args["order_id"])


if __name__ == '__main__':
    unittest.main()
