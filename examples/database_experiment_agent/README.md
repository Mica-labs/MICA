This example bot demonstrates **MICA's** ability to develop bots that automate **real-time database modifications** and **email validations**.

---

## Overview

There is only a single agent in this bot: **`database_llm_agent`**.

### Workflow
1. The agent asks the user to provide their **email address**.  
   *(In this implementation, we assume the user's information is already stored in the database, including the user's email.)*  
2. The agent sends a **randomly generated 6-digit code** to the provided email.  
3. The user is asked to **enter the validation code**.  
4. Once the correct code is entered, the agent allows the user to **dictate changes to their account information** associated with the email.  

---

## Features
- Real-time database modifications  
- Email-based user validation  
- Simple single-agent design (`database_llm_agent`)  

```yaml
<database_llm_agent:
  type: llm agent
  description: I can make changes to user email in example database as the user requested
  args:
    - status
    - email
    - code
  prompt: |
    1. Ask the user what their email is, and store it in your argument.
    2. Uses the "send_verification_code" function, the argument is the email provided, the rest two argument are set default, do not fill them. I should now ask the user what the verification code is.
    3. If the code is right, proceed to next step; if the code is wrong, tell the user its wrong.
    4. After verifying the code, call the "update_json_field" function, the first argument should be the person's email, second argument is which information (like email) to change, thrid argument is new information, the rest two argument are set default, do not fill them.
  uses:
    - send_verification_code
    - update_json_field

main:
  type: flow agent
  steps:
    - call: database_llm_agent>