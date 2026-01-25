#!/bin/bash
nohup npx hardhat node > hardhat.log 2>&1 &
cd Server
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
cd ..
