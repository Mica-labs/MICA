import os
import pytest
import glob

# Get all subdirectories in the examples folder
example_bots = [d for d in glob.glob("examples/*") if os.path.isdir(d)]

@pytest.mark.parametrize("bot_folder", example_bots)
def test_example_bots(bot_folder, load_bot_from_folder):
    """Tests that all example bots can be loaded."""
    
    # check if there is any yml or yaml file in the folder, if not, skip
    if not glob.glob(os.path.join(bot_folder, "*.yml")) and not glob.glob(os.path.join(bot_folder, "*.yaml")):
        pytest.skip(f"Skipping {bot_folder} as it does not contain any .yml or .yaml file.")

    try:
        bot = load_bot_from_folder(bot_folder)
        assert bot is not None, f"Failed to load bot from {bot_folder}"

        # output_channel = CollectingOutputChannel()
        # bot.handle_message("hello", output_channel=output_channel, sender_id=f"test-{bot_folder}")
        
        # Check that the bot produced at least one message
        # assert len(output_channel.messages) > 0, f"Bot in {bot_folder} did not respond."

    except Exception as e:
        pytest.fail(f"An exception occurred while testing bot from {bot_folder}: {e}") 