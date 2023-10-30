"""
Provides a websocket endpoint for watching the state of a 
local graph .json file.
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = FastAPI()

@app.websocket("/watch/{id}")
async def websocket_endpoint(websocket: WebSocket, id: str):
    await websocket.accept()

    async def watcher():
        queue = asyncio.Queue()

        class EventHandler(FileSystemEventHandler):
            def on_modified(self, event):
                queue.put_nowait(event)

        path = id
        observer = Observer()
        observer.unschedule_all()
        observer.schedule(EventHandler(), path, recursive=True)
        observer.start()
        try:
            while True:
                if not queue.empty():
                    event = await queue.get()
                    with open(id, "r") as f:
                        contents = f.read()
                        await websocket.send_text(contents)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            observer.stop()
        observer.join()

    watch_task = asyncio.create_task(watcher())

    with open(id, "r") as f:
        await websocket.send_text(f.read())

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    finally:
        watch_task.cancel()

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)