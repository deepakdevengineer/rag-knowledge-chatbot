import subprocess
import os
import sys
import threading

def stream_output(process, prefix):
    for line in iter(process.stdout.readline, b''):
        sys.stdout.write(f"[{prefix}] {line.decode('utf-8', errors='replace')}")

def main():
    print("Starting RAG Chatbot...")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    backend_path = os.path.join(base_path, 'backend')
    frontend_path = os.path.join(base_path, 'frontend')
    
    # Start Backend
    backend_python = os.path.join(backend_path, 'venv', 'Scripts', 'python.exe')
    if not os.path.exists(backend_python):
        print(f"Backend python not found at {backend_python}. Make sure venv is setup.")
        sys.exit(1)

    print("=> Starting Backend...")
    backend_process = subprocess.Popen(
        [backend_python, "-m", "app.main"],
        cwd=backend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Start Frontend
    print("=> Starting Frontend...")
    frontend_process = subprocess.Popen(
        "npm run dev",
        cwd=frontend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True
    )
    
    # Stream outputs in separate threads
    threading.Thread(target=stream_output, args=(backend_process, "BACKEND"), daemon=True).start()
    threading.Thread(target=stream_output, args=(frontend_process, "FRONTEND"), daemon=True).start()
    
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nStopping processes...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()
