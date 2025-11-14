#!/usr/bin/env python
"""
Script to deploy a bot zip file to the MICA server.
Usage: python deploy_bot.py <path_to_zip_file>
"""
import sys
import requests
from pathlib import Path

def deploy_bot(zip_path, server_url="http://127.0.0.1:5001/v1/deploy"):
    """Deploy a bot zip file to the MICA server."""
    zip_path = Path(zip_path)
    
    if not zip_path.exists():
        print(f"Error: File not found: {zip_path}")
        return False
    
    if not zip_path.suffix == '.zip':
        print(f"Error: File must be a .zip file: {zip_path}")
        return False
    
    try:
        print(f"Deploying {zip_path} to {server_url}...")
        with open(zip_path, 'rb') as f:
            files = {'file': (zip_path.name, f, 'application/zip')}
            response = requests.post(server_url, files=files)
        
        if response.status_code == 200:
            print("✓ Deployment successful!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"✗ Deployment failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Error: Could not connect to server at {server_url}")
        print("  Make sure the server is running: python -m mica.server")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_bot.py <path_to_zip_file>")
        print("Example: python deploy_bot.py examples/customer_service/customer_service.zip")
        sys.exit(1)
    
    zip_path = sys.argv[1]
    success = deploy_bot(zip_path)
    sys.exit(0 if success else 1)


