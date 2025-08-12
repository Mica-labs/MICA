# Dental Assistant Chatbot – Agent Functionality Guide

This assistant supports 5 core functionalities using database operations, GPT-4o, and Twilio SMS. Each function is handled by a dedicated agent and a corresponding backend tool function.


## 1. Create Patient Record

**Agent:** `PatientRecord`  
**Function:** `action_create_patient_record(name, contact_info, date_of_birth)`

**What it does:**  
Creates a new entry in the `patients` table with the patient's name, contact information (email or phone), and date of birth.

**Flow:**
- Asks for name, contact, and DOB (in MM/DD/YYYY format)
- Stores the entry in SQLite
- Returns a success message and patient ID



## 2. Schedule Appointment

**Agent:** `AppointmentScheduler`  
**Functions:** 
- `action_check_availability(appointment_datetime)`
- `action_schedule_appointment(name, appointment_datetime)`

**What it does:**  
Schedules an appointment for an existing patient if the time slot is available.

**Flow:**
- Asks for patient name and appointment date
- Checks if the date is already booked
- If free, inserts a new record in the `appointments` table linking to the patient
- Confirms with a success message



## 3. Patient Information Inquiry

**Agent:** `PatientInformationInquiry`  
**Function:** `action_get_patient_info(name=None, patient_id=None)`

**What it does:**  
Looks up a patient's stored information using either name or patient ID and retrieves:
- Contact info
- Date of birth
- All associated appointments

**Flow:**
- Prompts user for name or ID
- Queries the `patients` and `appointments` tables
- Displays detailed record if found



## 4. Image Analysis

**Agent:** `ImageAnalysis`  
**Function:** `action_analyze_image(image_id)`

**What it does:**  
Takes a dental X-ray or image URL and sends it to GPT-4o with a prompt asking for a brief analysis/diagnosis.

**Flow:**
- Asks user for image URL or identifier
- Uses GPT-4o Vision API to analyze image
- Returns a short diagnostic summary



## 5. Send SMS Notification

**Agent:** `NotificationSender`  
**Function:** `action_send_notification(sender_number, recipient, message)`

**What it does:**  
Sends an SMS message using Twilio from a sender number to a recipient with the desired text.

**Flow:**
- Asks for the recipient's phone number
- Asks for message text
- Sends SMS via Twilio API and confirms status

**Note: Twilio Setup Required**
- To use this functionality, you must set the following environment variables in your `.env` file:

````

TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token

````

- The sender's phone number must be a verified or purchased number from your Twilio account.
- In addition, you must intsall the twilio module before running:

````

pip install twilio

````



