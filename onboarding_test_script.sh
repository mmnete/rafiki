#!/bin/bash

# Define your Flask app's local URL
URL="http://localhost:5000/message"

# Set content type and data headers for all requests
HEADER="Content-Type: application/json"

send_message() {
    local USER_ID=$1
    local MESSAGE=$2
    local PAYLOAD="{\"user_id\":\"$USER_ID\", \"message\":\"$MESSAGE\"}"
    curl -X POST -H "$HEADER" -d "$PAYLOAD" "$URL"
    echo "" # Add a newline for better readability
}


# --- Test Scenario 1: Successful Onboarding Flow ---
echo "--- Starting Scenario 1: Successful Onboarding ---"
PHONE_NUMBER_VALID="+255712345678"

send_message "$PHONE_NUMBER_VALID" "hello"
send_message "$PHONE_NUMBER_VALID" "Morgan Mnete"
send_message "$PHONE_NUMBER_VALID" "Ndio"
send_message "$PHONE_NUMBER_VALID" "Dar es Salaam"
send_message "$PHONE_NUMBER_VALID" "Yes"

# --- Test Scenario 2: Onboarding Failure (Invalid Number) ---
echo -e "\n--- Starting Scenario 2: Invalid Phone Number ---"
PHONE_NUMBER_INVALID="+15551234567"

send_message "$PHONE_NUMBER_INVALID" "hello"

# --- Test Scenario 3: Onboarding with Invalid Name Input ---
echo -e "\n--- Starting Scenario 3: Invalid Name Input ---"
PHONE_NUMBER_INVALID_NAME="+255755555555"

send_message "$PHONE_NUMBER_INVALID_NAME" "hello"
send_message "$PHONE_NUMBER_INVALID_NAME" "Morgan"
send_message "$PHONE_NUMBER_INVALID_NAME" "Morgan Mnete"
send_message "$PHONE_NUMBER_INVALID_NAME" "Dar es Salaam"
send_message "$PHONE_NUMBER_INVALID_NAME" "Sure"    # Invalid confirmation
send_message "$PHONE_NUMBER_INVALID_NAME" "Ndio"

# --- Test Scenario 4: User Says 'No' to Name Confirmation and Re-enters Name ---
echo -e "\n--- Starting Scenario 4: Name Confirmation Rejection ---"
PHONE_NUMBER_REJECT_NAME="+255799999999"

send_message "$PHONE_NUMBER_REJECT_NAME" "hi"
send_message "$PHONE_NUMBER_REJECT_NAME" "Asha Omary"
send_message "$PHONE_NUMBER_REJECT_NAME" "Hapana"   # Rejects name confirmation
send_message "$PHONE_NUMBER_REJECT_NAME" "Asha Ally"
send_message "$PHONE_NUMBER_REJECT_NAME" "Ndio"
send_message "$PHONE_NUMBER_REJECT_NAME" "Moshi"
send_message "$PHONE_NUMBER_REJECT_NAME" "Ndio"

# --- Test Scenario 5: User Says 'No' to Location Confirmation and Re-enters Location ---
echo -e "\n--- Starting Scenario 5: Location Confirmation Rejection ---"
PHONE_NUMBER_REJECT_LOC="+255711111111"

send_message "$PHONE_NUMBER_REJECT_LOC" "hello"
send_message "$PHONE_NUMBER_REJECT_LOC" "Juma Hassan"
send_message "$PHONE_NUMBER_REJECT_LOC" "Ndio"
send_message "$PHONE_NUMBER_REJECT_LOC" "Dodoma"
send_message "$PHONE_NUMBER_REJECT_LOC" "Hapana"  # Rejects location confirmation
send_message "$PHONE_NUMBER_REJECT_LOC" "Arusha"
send_message "$PHONE_NUMBER_REJECT_LOC" "Ndio"

# --- Test Scenario 6: Active User Asking for Flight Booking ---
echo -e "\n--- Starting Scenario 6: Active User Flight Booking Request ---"
PHONE_NUMBER_ACTIVE="+255700000000"

send_message "$PHONE_NUMBER_ACTIVE" "hello"
send_message "$PHONE_NUMBER_ACTIVE" "Amina Suleiman"
send_message "$PHONE_NUMBER_ACTIVE" "Ndio"
send_message "$PHONE_NUMBER_ACTIVE" "Dar es Salaam"
send_message "$PHONE_NUMBER_ACTIVE" "Ndio"

# Now user is active
send_message "$PHONE_NUMBER_ACTIVE" "Ningependa kutafuta ndege kutoka Dar es Salaam kwenda Mwanza tarehe 15 Agosti"
send_message "$PHONE_NUMBER_ACTIVE" "Ndiyo, ningependa kukamilisha booking"

echo -e "\nScript finished. Check your Flask terminal for logs and output."
