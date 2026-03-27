from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var username = {username}
            document.querySelector("#ws-id").textContent = username;
            var ws = new WebSocket(`ws://localhost:8000/ws/${username}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var number = document.createElement('li')
                var content = document.createTextNode(event.data)
                number.appendChild(content)
                messages.appendChild(number)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, number: int, websocket: WebSocket):
        await websocket.send_text(number)

    async def broadcast(self, number: int):
        for connection in self.active_connections:
            await connection.send_text(number)


manager = ConnectionManager()


@app.get("/{username}")
async def get(username: str):
    content = html.replace("{username}", f'"{username}"')
    return HTMLResponse(content=content)


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{username} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{username} left the chat")