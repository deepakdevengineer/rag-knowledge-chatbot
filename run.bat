@echo off
echo Starting RAG Chatbot Servers...

:: Start Backend
echo Starting Backend...
start "RAG Chatbot Backend" cmd /k "cd backend && .\venv\Scripts\python.exe -m app.main"

:: Start Frontend
echo Starting Frontend...
start "RAG Chatbot Frontend" cmd /k "cd frontend && npm run dev"

echo Both servers are starting in new windows!
