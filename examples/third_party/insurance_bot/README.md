This example bot demonstrates **MICA's** ability to develop bots that can perform both real-time modification of database and answering questions based on designated sources.

---

## Overview

There is mainly two agents in this bot: **`claim_agent`**, responsible for filling new claims and store them in database, and **`kb`**, responsible for answering questions based on designated documents or urls.

### Workflow
1. If the user indicates that they want to fill a claim, the **`claim_agent`** will randomly generate a claim number and ask for more necessary information. 
2. The information will be stored in the bot's arguments (as shown on the upper window)
3. The arguments will later be used to call on a tool function to store the claim in database.
4. If the user has a question, **`kb`** agent will answer the question based on the developer-designated sources. 

---

## Features
- Real-time database modifications based on conversations.
- Question-answering based on designated sources.  

```yaml
<kb:
  type: kb agent
  faq:
    - q: what can you do?
      a: I can help you answer questions regarding insurance. 
    - q: Thanks
      a: Bye.
  sources:
    - ./examples/insurance_bot/database_file
    
claim_agent:
  type: llm agent
  description: I help the users fill their insurance claims by inserting new claims to example database.
  args:
    - claim number
    - User ID
    - what caused damage
    - date of incident
    - time of incident
    - location of incident
    - new claim
  prompt: |
    1. Randomly assign a claim number and store it in your argument.
    2. Ask the user what their User ID is, and store it in your argument.
    3. Ask the user what caused damage, and store it in your argument.
    4. Ask the user the date of incident, and store it in your argument.
    5. Ask the user the time of incident, and store it in your argument.
    6. Ask the user the location of incident, and store it in your argument.
    7. put all arguments in sequence in a dictionary and store it in your argument, for example "new_claim = {"claim number": "440305","User ID": "1919810","what caused damage": "Tree fell on my car during a storm","date of incident": "09/25/2025","time of incident": "10am","location of incident": "123 Main St"}"
    9. Remove the quotation marks around dictionary, use the dictionary as the first argument to call the "insert_new_claim" function, leave the second argument of the function alone as it has been set default to some value.
  uses:
    - insert_new_claim


meta:
  type: ensemble agent
  description: You can select an agent to answer user's question. Choose kb agent if the user has a question, choose claim agent if the user wants to fill a claim
  contains: 
    - kb
    - claim_agent
  steps:
    - bot: Hello, I can help you answer some common insurance questions. Feel free to ask me!

main:
  type: flow agent
  steps:
    - call: meta>
