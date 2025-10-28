import json
import os
import hashlib

DEFAULT_CONFIG = {
    "password_hash": hashlib.sha256("@moeder123".encode()).hexdigest(),
    "auto_deposits": {
        # Example: "Child Name": amount
        "Example Kid": 100
    },
    "last_auto_deposit": "2025-09-01"  # Will be updated automatically
}

CONFIG_FILE = "pocket_money_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)