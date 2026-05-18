#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/Users/turjomazumder/Antigravity Project/Jira Project"

echo -e "${GREEN}=== Starting Jira Team Performance Analytics ===${NC}\n"

# Check if ports are available
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}❌ Port 3000 is already in use${NC}"
    exit 1
fi

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}❌ Port 8000 is already in use${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting Backend (FastAPI)...${NC}"
cd "$PROJECT_DIR/backend"
source venv/bin/activate
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend PID: $BACKEND_PID${NC}"
echo "   Logs: $PROJECT_DIR/backend/backend.log"

sleep 3

echo -e "\n${YELLOW}Starting Frontend (Workpulse Standalone)...${NC}"
cd "$PROJECT_DIR/jira-project/project"
python3 -m http.server 3000 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend PID: $FRONTEND_PID${NC}"
echo "   Logs: $PROJECT_DIR/jira-project/project/frontend.log"

sleep 5

echo -e "\n${GREEN}=== Services Started ===${NC}"
echo -e "Frontend: ${GREEN}http://localhost:3000/Workpulse.html${NC}"
echo -e "Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "Health:   ${GREEN}http://localhost:8000/health${NC}"

echo -e "\n${YELLOW}Opening Chrome...${NC}"
open -a "Google Chrome" http://localhost:3000/Workpulse.html

echo -e "\n${YELLOW}View logs with:${NC}"
echo "  Backend:  tail -f $PROJECT_DIR/backend/backend.log"
echo "  Frontend: tail -f $PROJECT_DIR/frontend/frontend.log"

echo -e "\n${YELLOW}To stop services:${NC}"
echo "  kill $BACKEND_PID $FRONTEND_PID"

wait
