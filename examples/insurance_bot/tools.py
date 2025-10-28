import os
import json

def insert_new_claim(new_entry, filename="example_database.json"):
    """
    Inserts a new claim dictionary into the JSON database.

    Parameters:
        new_entry (dict): New claim with keys:
            - 'claim number'
            - 'User ID'
            - 'what caused damage'
            - 'date of incident'
            - 'time of incident'
            - 'location of incident'
        filename (str): Default is 'example_database.json'
    """

    # Path resolution (adapted from your tools.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mica_root = os.path.dirname(base_dir)
    full_path = os.path.join(mica_root, "Mica", "examples", "insurance_bot", filename)

    # Check if the file exists
    if not os.path.exists(full_path):
        return [{"bot": f"Path not found: {full_path}"}, 
                {"arg": "status", "value": False}]

    # Read existing data
    try:
        with open(full_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return [{"bot": f"Error reading file: {e}"}, 
                {"arg": "status", "value": False}]

    # Append new entry
    data.append(new_entry)

    # Save back
    try:
        with open(full_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        return [{"bot": f"Error writing file: {e}"}, 
                {"arg": "status", "value": False}]

    return [{"bot": "New claim inserted successfully."},
            {"arg": "status", "value": True}]


# # Example usage
# if __name__ == "__main__":
#     new_claim = {
#         "claim number": "44030",
#         "User ID": "191981",
#         "what caused damage": "Tree fell on my car during a storm",
#         "date of incident": "09/25/2025",
#         "time of incident": "10am",
#         "location of incident": "123 Main St"
#     }

#     result = insert_new_claim(new_claim)
#     print(result)

