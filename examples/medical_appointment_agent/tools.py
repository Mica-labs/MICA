def modify_balance(name, appointment_fee, filename="example_database.json"):
    import os
    import json

    # Construct path to example_database.json (assumes same structure as update_json_field)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mica_root = os.path.dirname(base_dir)
    full_path = os.path.join(mica_root, "medical_appointment_agent", filename)

    if not os.path.exists(full_path):
        return [{"bot": f"Path not found: {full_path}"},
                {"arg": "name", "value": name},
                {"arg": "remaining_balance", "value": None}]

    # Read JSON and find matching user
    with open(full_path, 'r') as f:
        data = json.load(f)

    updated = False
    for entry in data:
        if entry.get("name") == name:
            if "balance" in entry and isinstance(entry["balance"], (int, float)):
                entry["balance"] -= appointment_fee
                remaining_balance = entry["balance"]
                updated = True
                break

    if not updated:
        return [{"bot": f"User '{name}' not found or balance not numeric."},
                {"arg": "name", "value": name},
                {"arg": "remaining_balance", "value": None}]

    # Write updated data back to JSON
    with open(full_path, 'w') as f:
        json.dump(data, f, indent=2)

    return [{"bot": "Information updated."},
            {"arg": "name", "value": name},
            {"arg": "remaining_balance", "value": remaining_balance}]
response = modify_balance("Klaus", 25)
print(response)

