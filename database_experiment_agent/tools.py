import os
import json
import smtplib
import ssl
from email.message import EmailMessage
from secrets import choice
from string import digits
from dotenv import load_dotenv

def update_json_field(
    match_value,
    update_key,
    update_value,
    match_key="email",
    filename="example_database.json"
):
    # Base dir = Mica root
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Go up to Mica root, then into examples/database_experiment_agent
    mica_root = os.path.dirname(base_dir)
    full_path = os.path.join(mica_root, "Mica", "examples", "database_experiment_agent", filename)

    if not os.path.exists(full_path):
        return [{"bot": f"Path not found: {full_path}"}, 
                {"arg": "status", "value": False},
                {"arg": "email", "value": "passed"},
                {"arg": "code", "value": "passed"}
                ]

    with open(full_path, 'r') as f:
        data = json.load(f)

    updated = False
    for entry in data:
        if entry.get(match_key) == match_value:
            entry[update_key] = update_value
            updated = True
            break

    if not updated:
        return [{"bot": "Not updated."}, 
                {"arg": "status", "value": False},
                {"arg": "email", "value": "passed"},
                {"arg": "code", "value": "passed"}
                ]

    with open(full_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return [{"bot": "Information updated."},
            {"arg": "status", "value": True},
            {"arg": "email", "value": "passed"},
                {"arg": "code", "value": "passed"}
                ]

load_dotenv()

EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_SSL = True  # try True first to use port 465
EMAIL_PORT = 465 if EMAIL_USE_SSL else 587
EMAIL_USER = "hanzhezhang@ucsb.edu"               # sender account
EMAIL_PASS = "zjjs plen wqjz osgx"                # app password
EMAIL_FROM = EMAIL_USER
#EMAIL_USE_SSL = False

def send_verification_code(email, code_length: int = 6, ttl_seconds: int = 600):
    # Generate code
    code = "".join(choice(digits) for _ in range(code_length))

    # Prepare email
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_FROM):
        return [{"bot": "Email credentials missing."},
                {"arg": "status", "value": False},
                {"arg": "email", "value": email},
                {"arg": "code", "value": None}]

    msg = EmailMessage()
    msg["Subject"] = "Your Verification Code"
    msg["From"] = EMAIL_FROM
    msg["To"] = email
    msg.set_content(f"Your verification code is: {code}\nIt expires in {ttl_seconds//60} minutes.")

    # Send email
    try:
        if EMAIL_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as smtp:
                smtp.login(EMAIL_USER, EMAIL_PASS)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(EMAIL_USER, EMAIL_PASS)
                smtp.send_message(msg)
    except Exception as e:
        return [{"bot": f"Failed to send email: {e}"},
                {"arg": "status", "value": False},
                {"arg": "email", "value": email},
                {"arg": "code", "value": None}]
    print("Email successfully sent.")
    return [{"bot": f"Verification code sent to {email}."},
            {"arg": "status", "value": True},
            {"arg": "email", "value": email},
            {"arg": "code", "value": code}]

# For testing:
# if __name__ == "__main__":
#     # Example: send a code to yourself
#     result = send_verification_code("FILL IN RECEIVER EMAIL HERE")
#     print(result)
#     code_only = next(item["value"] for item in result if item.get("arg") == "code")
#     print(code_only)