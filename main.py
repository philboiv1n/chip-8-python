import asyncio
from fastapi import WebSocketDisconnect
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import src.chip_8 as chip_8
from fastapi import File, UploadFile, HTTPException

KEY_UP = 0
KEY_DOWN = 1

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    """
    Display HTML index page
    """
    return FileResponse("static/index.html")


@app.post("/load")
async def load_rom(file: UploadFile = File(...)):
    """
    Upload a .ch8 ROM and load it into memory at 0x200.
    """
    data = await file.read()
    max_size = len(chip_8.mem) - 0x200
    if len(data) > max_size:
        raise HTTPException(status_code=400, detail="ROM too large")
    
    # Clear memory and display
    chip_8.mem[:] = bytearray(len(chip_8.mem))
    chip_8.screen[:] = bytearray(len(chip_8.screen))
    
    # Reset registers, keypad, timers
    for k in list(chip_8.regs):
        chip_8.regs[k] = 0
    chip_8.regs['PC'] = 0x200
    chip_8.regs['I']  = 0
    chip_8.keypad = [False] * 16
    chip_8.dt = 0
    chip_8.st = 0

    # Load ROM into memory at 0x200
    chip_8.mem[0x200:0x200 + len(data)] = data

    # Append HALT opcode (0xFFFF) immediately after the ROM
    end = 0x200 + len(data)
    chip_8.mem[end:end+2] = bytes([0xFF, 0xFF])
    
    return {"status": "loaded", "size": len(data)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    """
    await ws.accept()
    # Start the background emulator loop
    runner = asyncio.create_task(emulator_runner(ws))
    try:
        while True:
            # Handle binary key events: [event_type, key_code]
            msg = await ws.receive()
            if "bytes" in msg:
                b = msg["bytes"]
                if len(b) >= 2:
                    chip_8.keypad[b[1]] = (b[0] == KEY_DOWN)
    except WebSocketDisconnect:
        # Stop the emulator loop when client disconnects
        runner.cancel()


async def emulator_runner(ws: WebSocket):
    """
    Two asyncio coroutines.
    One for steady screen updates and timer handling, 
    the other for raw instruction execution—coordinated 
    via non-blocking sleeps and cooperative yielding.
    """
    
    # Task to send frames at 60 Hz & update timers
    async def frame_task():
        try:
            while True:
                await asyncio.sleep(1/60)
                # Update timers
                if chip_8.dt > 0:
                    chip_8.dt -= 1
                if chip_8.st > 0:
                    chip_8.st -= 1
                # Send current framebuffer
                await ws.send_bytes(bytes(chip_8.screen))
        except asyncio.CancelledError:
            return

    frame_updater = asyncio.create_task(frame_task())

    # Main execution / CPU “stepping” loop
    try:
        while True:
            if not chip_8.step():
                break
            # Yield control so frame_task can run
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        pass
    finally:
        frame_updater.cancel()
