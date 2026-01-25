#!/bin/bash

# --- Configuration ---
HARDHAT_NODE_PORT=8545
FASTAPI_SERVER_PORT=8000
HARDHAT_PID=""
FASTAPI_PID=""
SERVER_DIR="Server"
VENV_DIR="$SERVER_DIR/.venv"
LOG_FILE="$SERVER_DIR/nohup.out"
TEST_FILE="test_ee.py"
REQUIREMENTS_FILE="$SERVER_DIR/requirements.txt"
HARDHAT_NODE_OUTPUT_FILE="" # Declare globally
DEPLOY_OUTPUT_FILE="" # Declare globally
NPM_INSTALL_LOG="" # For npm install logs
PIP_INSTALL_LOG="" # For pip install logs

# --- ANSI Color Codes ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Utility Functions ---
log() {
    echo -e "$(date +'%Y-%m-%d %H:%M:%S') - $1"
}

success_msg() {
    log "${GREEN}SUCCESS:${NC} $1"
}

warn_msg() {
    log "${YELLOW}WARNING:${NC} $1"
}

error_exit() {
    log "${RED}ERROR:${NC} $1" >&2
    cleanup
    exit 1
}

wait_for_port_free() {
    local port=$1
    local timeout=$2
    log "${BLUE}Waiting for port ${port} to be free (timeout: ${timeout} seconds)...${NC}"
    if ! command -v lsof &> /dev/null; then
        warn_msg "lsof not found. Cannot reliably check if port ${port} is free. Proceeding assuming it will be free."
        return 0 # Assume free if lsof is not available
    fi

    for ((i=0; i<timeout; i++)); do
        if ! lsof -i :"$port" > /dev/null; then
            success_msg "Port ${port} is free."
            return 0
        fi
        sleep 1
    done
    return 1 # Timeout reached, port still in use
}


cleanup() {


    log "${BLUE}Performing cleanup...${NC}"


    if [ -n "$HARDHAT_PID" ]; then


        log "Stopping Hardhat node (PID: $HARDHAT_PID)..."


        kill "$HARDHAT_PID" > /dev/null 2>&1


        wait "$HARDHAT_PID" 2>/dev/null


    fi


    if [ -n "$FASTAPI_PID" ]; then


        log "Stopping FastAPI server (PID: $FASTAPI_PID)..."


        kill "$FASTAPI_PID" > /dev/null 2>&1


        wait "$FASTAPI_PID" 2>/dev/null


    fi





    if [ -n "$HARDHAT_NODE_OUTPUT_FILE" ] && [ -f "$HARDHAT_NODE_OUTPUT_FILE" ]; then


        rm "$HARDHAT_NODE_OUTPUT_FILE"


    fi


    if [ -n "$DEPLOY_OUTPUT_FILE" ] && [ -f "$DEPLOY_OUTPUT_FILE" ]; then


        rm "$DEPLOY_OUTPUT_FILE"


    fi


    if [ -n "$NPM_INSTALL_LOG" ] && [ -f "$NPM_INSTALL_LOG" ]; then


        rm "$NPM_INSTALL_LOG"


    fi


    if [ -n "$PIP_INSTALL_LOG" ] && [ -f "$PIP_INSTALL_LOG" ]; then


        rm "$PIP_INSTALL_LOG"


    fi








    # Proactively kill any Hardhat node processes


    log "Proactively killing any 'hardhat node' processes..."


    pkill -f "hardhat node" > /dev/null 2>&1


    sleep 1 # Give some time for processes to terminate





    # Proactively kill any uvicorn processes


    log "Proactively killing any 'uvicorn' processes..."


    pkill -f uvicorn > /dev/null 2>&1


    sleep 1 # Give some time for processes to terminate





    # Ensure ports are free


    if command -v lsof &> /dev/null; then


        wait_for_port_free "$HARDHAT_NODE_PORT" 5 || warn_msg "Port $HARDHAT_NODE_PORT might still be in use after cleanup."


        wait_for_port_free "$FASTAPI_SERVER_PORT" 5 || warn_msg "Port $FASTAPI_SERVER_PORT might still be in use after cleanup."


    else


        warn_msg "lsof not found. Cannot perform full port cleanup checks."


    fi


    log "${BLUE}Cleanup complete.${NC}"


}





# --- Main Script Logic ---


trap cleanup EXIT # Ensure cleanup runs on exit





log "${BLUE}=====================================================${NC}"


log "${BLUE}  Starting Key Reconstruction System Demonstration   ${NC}"


log "${BLUE}=====================================================${NC}"





log "${BLUE}\n--- 1. Hardhat Smart Contract Setup ---${NC}"
if ! command -v npm &> /dev/null; then
    error_exit "npm is not installed. Please install Node.js and npm."
fi
if ! command -v npx &> /dev/null; then
    error_exit "npx is not installed. Please install Node.js and npm."
fi

log "Installing Hardhat dependencies..."
NPM_INSTALL_LOG=$(mktemp)
npm install > "$NPM_INSTALL_LOG" 2>&1
if [ $? -eq 0 ]; then
    success_msg "Hardhat dependencies installed."
else
    error_exit "Failed to install Hardhat dependencies. Check $NPM_INSTALL_LOG for details."
fi


log "Compiling smart contracts..."
npx hardhat compile > /dev/null 2>&1 || error_exit "Failed to compile smart contracts."
success_msg "Smart contracts compiled."

# Perform proactive kill and wait for port before starting Hardhat
log "Proactively ensuring port $HARDHAT_NODE_PORT is free before starting Hardhat..."
pkill -f "hardhat node" > /dev/null 2>&1
sleep 2 # Give some time for old processes to exit
if ! wait_for_port_free "$HARDHAT_NODE_PORT" 10; then
    error_exit "Port $HARDHAT_NODE_PORT is still in use after cleanup. Cannot start Hardhat."
fi

log "Starting Hardhat Network node in background..."
HARDHAT_NODE_OUTPUT_FILE=$(mktemp) # Temporary file for node output
nohup npx hardhat node > "$HARDHAT_NODE_OUTPUT_FILE" 2>&1 &
HARDHAT_PID=$!
log "Hardhat node started with PID: $HARDHAT_PID"

log "Waiting for Hardhat node to start..."
sleep 15 # Give Hardhat some time to start

log "--- Hardhat Node Output (first 50 lines for debugging) ---"
head -n 50 "$HARDHAT_NODE_OUTPUT_FILE"
log "--- Hardhat Node Output End ---"


SERVER_PRIVATE_KEY=$(grep -oE 'Private Key:\s*(0x[a-fA-F0-9]{64})' "$HARDHAT_NODE_OUTPUT_FILE" | head -n 1 | awk '{print $NF}')
if [ -z "$SERVER_PRIVATE_KEY" ]; then
    error_exit "Could not extract SERVER_PRIVATE_KEY from Hardhat node output. Check $HARDHAT_NODE_OUTPUT_FILE for details."
fi
success_msg "Extracted Hardhat Server Private Key: ${GREEN}$SERVER_PRIVATE_KEY${NC}"

log "Deploying contract via Hardhat Ignition..."
DEPLOY_OUTPUT_FILE=$(mktemp) # Temporary file for deploy output
npx hardhat ignition deploy ./ignition/modules/KeyReconstructionModule.js --network localhost --parameters "{ \"KeyReconstructionModule\": { \"serverPubKey\": \"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266\", \"threshold\": 2 } }" > "$DEPLOY_OUTPUT_FILE" 2>&1
DEPLOY_EXIT_CODE=$? # Capture exit code of deploy command


log "--- Hardhat Deploy Output (for debugging, if needed) ---"
cat "$DEPLOY_OUTPUT_FILE"
log "--- Hardhat Deploy Output End ---"

if [ "$DEPLOY_EXIT_CODE" -ne 0 ]; then
    error_exit "Hardhat Ignition deployment failed. Check $DEPLOY_OUTPUT_FILE for details."
fi
success_msg "Hardhat Ignition deployment completed."


CONTRACT_ADDRESS=$(grep -oE 'KeyReconstructionModule#KeyReconstruction - (0x[a-fA-F0-9]{40})' "$DEPLOY_OUTPUT_FILE" | awk '{print $NF}')
if [ -z "$CONTRACT_ADDRESS" ]; then
    error_exit "Could not extract CONTRACT_ADDRESS from Hardhat Ignition deployment output. Check $DEPLOY_OUTPUT_FILE for details."
fi
success_msg "Extracted Hardhat Contract Address: ${GREEN}$CONTRACT_ADDRESS${NC}"
success_msg "Hardhat setup complete."

# 2. --- FastAPI Server Setup ---
log "${BLUE}\n--- 2. FastAPI Server Setup ---${NC}"
if ! command -v python3 &> /dev/null; then
    error_exit "Python 3 is not installed."
fi

log "Creating/activating Python virtual environment..."
mkdir -p "$SERVER_DIR" # Ensure Server directory exists
python3 -m venv "$VENV_DIR" || error_exit "Failed to create virtual environment."
source "$VENV_DIR/bin/activate" || error_exit "Failed to activate virtual environment."
success_msg "Python virtual environment setup."

log "Installing Python dependencies..."
PIP_INSTALL_LOG=$(mktemp)
pip install -r "$REQUIREMENTS_FILE" > "$PIP_INSTALL_LOG" 2>&1
if [ $? -eq 0 ]; then
    success_msg "Python dependencies installed."
else
    error_exit "Failed to install Python dependencies. Check $PIP_INSTALL_LOG for details."
fi


log "Configuring .env file..."
cat << EOF > "$SERVER_DIR/.env"
ETH_NODE_URL=http://127.0.0.1:$HARDHAT_NODE_PORT
CONTRACT_ADDRESS=$CONTRACT_ADDRESS
SERVER_PRIVATE_KEY=$SERVER_PRIVATE_KEY
EOF
success_msg "Created ${SERVER_DIR}/.env"


# Perform proactive kill and wait for port before starting FastAPI
log "Proactively ensuring port $FASTAPI_SERVER_PORT is free before starting FastAPI..."
pkill -f uvicorn > /dev/null 2>&1
sleep 2 # Give some time for old processes to exit
if ! wait_for_port_free "$FASTAPI_SERVER_PORT" 10; then
    error_exit "Port $FASTAPI_SERVER_PORT is still in use after cleanup. Cannot start FastAPI."
fi

log "Starting FastAPI server in background..."
# Ensure log file is created in the Server directory
mkdir -p "$SERVER_DIR"
echo "" > "$SERVER_DIR/nohup.out" # Clear previous server logs

(cd "$SERVER_DIR" && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port "$FASTAPI_SERVER_PORT" --log-level debug > nohup.out 2>&1 &)
FASTAPI_PID=$!
log "FastAPI server started with PID: $FASTAPI_PID"

log "Waiting for FastAPI server to start (checking logs)..."
# Wait for "Application startup complete." in nohup.out
timeout=30
for ((i=0; i<timeout; i++)); do
    if grep -q "Application startup complete." "$SERVER_DIR/nohup.out"; then
        success_msg "FastAPI server is up."
        break
    fi
    sleep 1
    if [ "$i" -eq "$((timeout-1))" ]; then
        log "FastAPI server log (from $SERVER_DIR/nohup.out):"
        cat "$SERVER_DIR/nohup.out"
        error_exit "FastAPI server did not start in $timeout seconds."
    fi
done


success_msg "FastAPI server setup complete."

# 3. --- Run End-to-End Tests ---
log "${BLUE}\n--- 3. Running End-to-End Tests ---${NC}"
log "Test output:"
(cd "$SERVER_DIR" && python3 -m pytest "$TEST_FILE")
TEST_EXIT_CODE=$?
if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    success_msg "End-to-end tests completed successfully!"
else
    error_exit "End-to-end tests failed."
fi


log "${BLUE}\n=====================================================${NC}"
log "${BLUE}  Demonstration script finished successfully!        ${NC}"
log "${BLUE}=====================================================${NC}"
cleanup # Explicitly call cleanup (also called by trap on exit)
exit 0
