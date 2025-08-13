from fastapi.testclient import TestClient
from mica.server import app, manager

client = TestClient(app)

def test_read_bots():
    """
    Tests if the server can be initialized and if the /v1/bots endpoint is reachable.
    """
    response = client.get("/v1/bots")
    assert response.status_code == 200
    # The response should be a JSON list, even if it's empty
    assert isinstance(response.json(), list)

def test_deploy_zip(test_bot_zip_file):
    """
    Tests the /v1/deploy endpoint by uploading a zip file containing a bot.
    """
    # Clear any previously loaded bots to ensure a clean state
    manager.bots = {}

    with open(test_bot_zip_file, "rb") as f:
        files = {"file": ("test_bot.zip", f, "application/zip")}
        response = client.post("/v1/deploy", files=files)
    
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == 200
    assert response_json["message"] == "Successfully deployed bot: test_deploy_bot"

    # Verify that the bot was actually loaded into the manager
    assert "test_deploy_bot" in manager.bots
    bot = manager.get_bot("test_deploy_bot")
    assert bot is not None
    assert bot.name == "test_deploy_bot" 