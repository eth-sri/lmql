"""
Provides a websocket endpoint for watching the state of a 
local graph .json file.
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = FastAPI()

global file_to_watch
file_to_watch = None

@app.websocket("/watch/{id}")
async def websocket_endpoint(websocket: WebSocket, id: str):
    await websocket.accept()

    async def watcher():
        queue = asyncio.Queue()

        class EventHandler(FileSystemEventHandler):
            def on_modified(self, event):
                queue.put_nowait(event)

        assert file_to_watch is not None, "File to watch not set"

        path = file_to_watch
        print(f"Watching {path}")
        observer = Observer()
        observer.unschedule_all()
        observer.schedule(EventHandler(), path, recursive=True)
        observer.start()
        try:
            while True:
                if not queue.empty():
                    event = await queue.get()
                    with open(path, "r") as f:
                        contents = f.read()
                        await websocket.send_text(contents)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            observer.stop()
        observer.join()

    watch_task = asyncio.create_task(watcher())

    with open(file_to_watch, "r") as f:
        await websocket.send_text(f.read())

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    finally:
        watch_task.cancel()

if __name__ == "__main__":
    # ensure 'npx parcel' is installed
    import subprocess
    import sys
    import os
    import webbrowser

    assert len(sys.argv) == 2, "Usage: lmql graph-watch <graph.json>"
    
    file_to_watch = sys.argv[1]

    if not os.path.exists("node_modules"):
        print("Installing dependencies...")
        subprocess.run(["npm", "install"])

    p = subprocess.Popen(["npx", "parcel", "src/index.html"])
    try:
        webbrowser.open("http://localhost:1234")
        uvicorn.run(app, host="localhost", port=8000)
    finally:
        p.kill()