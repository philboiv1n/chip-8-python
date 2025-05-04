import asyncio
import json
import time
from fastapi import WebSocketDisconnect
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import src.chip_8 as chip_8
from fastapi import File, UploadFile

TICKS_PER_SEC = 600
KEY_UP = 0
KEY_DOWN = 1

# create a single Chip8 instance
chip = chip_8.Chip8()

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
    max_size = len(chip.mem) - 0x200
    
    if len(data) > max_size:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="ROM file too large")

    # Reset emulator state
    chip.__init__()

    # Load ROM into memory at 0x200
    chip.mem[0x200:0x200 + len(data)] = data

    # Append HALT opcode (0xFFFF) immediately after the ROM
    end = 0x200 + len(data)
    chip.mem[end:end+2] = bytes([0xFF, 0xFF])
    
    return {"status": "loaded", "size": len(data)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for control and key events
    """
    await ws.accept()
    # Start the background emulator loop
    runner = asyncio.create_task(emulator_runner(ws))
    try:
        while True:
            # Safely receive; exit on disconnect or invalid receive
            try:
                msg = await ws.receive()
            except (WebSocketDisconnect, RuntimeError):
                break

            # Text messages (JSON) for control commands:
            if "text" in msg:
                data = json.loads(msg["text"])
                if data.get("type") == "set_speed":
                    global TICKS_PER_SEC
                    TICKS_PER_SEC = int(data.get("tps", TICKS_PER_SEC))
                    continue

            # Binary messages for key events:
            if "bytes" in msg:
                b = msg["bytes"]
                if len(b) >= 2:
                    chip.keypad[b[1]] = (b[0] == KEY_DOWN)
    finally:
        # Always cancel the emulator loop when connection closes
        runner.cancel()
        try:
            await runner
        except asyncio.CancelledError:
            pass


async def emulator_runner(ws: WebSocket):
    """
    Run chip-8 at TICKS_PER_SEC, updating display and timers at 60 Hz,
    using real elapsed time for accurate speed control.
    """
    frame_interval = 1.0 / 60.0
    last_time = time.perf_counter()
    tick_acc = 0.0

    try:
        while True:
            # Calculate elapsed real time since last loop
            now = time.perf_counter()
            elapsed = now - last_time
            last_time = now

            # Accumulate ticks based on TICKS_PER_SEC and elapsed time
            tick_acc += elapsed * TICKS_PER_SEC
            steps = int(tick_acc)
            tick_acc -= steps

            # Execute pending ticks
            for _ in range(steps):
                if not chip.step():
                    await ws.close()
                    return

            # Update timers at 60 Hz (approx once per frame)
            if chip.dt > 0:
                chip.dt -= 1
            if chip.st > 0:
                chip.st -= 1

            # Send the framebuffer
            try:
                await ws.send_bytes(bytes(chip.screen))
            except WebSocketDisconnect:
                break

            # Sleep until next frame, subtracting time already spent
            frame_end = time.perf_counter()
            to_sleep = frame_interval - (frame_end - now)
            if to_sleep > 0:
                await asyncio.sleep(to_sleep)
    except asyncio.CancelledError:
        return
    except Exception as e:
        print("emulator_runner crashed:", e)
        try:
            await ws.close()
        except:
            pass