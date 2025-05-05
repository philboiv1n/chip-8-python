import asyncio
import json
import time
import traceback # For better error logging
from fastapi import WebSocketDisconnect, HTTPException
from fastapi import FastAPI, WebSocket, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import src.chip_8 as chip_8
from src.chip_8 import NeedKey

# --- Configuration ---
DEFAULT_TICKS_PER_SEC = 700 # Target Chip-8 instructions per second (adjust as needed)
FRAME_RATE = 60             # Target updates per second (timers, display, sound)
TARGET_FRAME_TIME = 1.0 / FRAME_RATE

# --- Constants ---
KEY_UP = 0
KEY_DOWN = 1

# --- Global State ---
chip = chip_8.Chip8()
current_ticks_per_sec = DEFAULT_TICKS_PER_SEC
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- HTTP Routes ---
@app.get("/")
async def get_index():
    """Display HTML index page."""
    return FileResponse("static/index.html")

@app.post("/load")
async def load_rom(file: UploadFile = File(...)):
    """
    Upload a .ch8 ROM, reset the emulator, and load the ROM.
    """
    global chip
    data = await file.read()
    max_size = chip.MEM_SIZE - 0x200 # Max ROM size

    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty ROM file received.")
    if len(data) > max_size:
        raise HTTPException(status_code=400, detail=f"ROM file too large (Max: {max_size} bytes)")

    print(f"Received ROM: {file.filename}, Size: {len(data)} bytes")

    # --- Reset emulator state ---
    chip = chip_8.Chip8() # Create a fresh instance
    print("Chip-8 state reset.")

    # Load ROM into memory starting at 0x200
    chip.mem[0x200 : 0x200 + len(data)] = data
    print(f"ROM loaded into memory at 0x200 - 0x{0x200 + len(data) - 1:X}")

    return {"status": "loaded", "size": len(data), "filename": file.filename}

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for emulator control, key events, and display/sound updates."""
    await ws.accept()
    print("WebSocket connection accepted.")
    # Queue for specific key events needed by Fx0A opcode
    key_event_queue: asyncio.Queue = asyncio.Queue()
    # Start the background emulator loop task
    runner_task = asyncio.create_task(emulator_runner(ws, key_event_queue))

    try:
        while True:
            # Wait for messages from the client
            msg = await ws.receive()

            if "text" in msg:
                try:
                    data = json.loads(msg["text"])
                    msg_type = data.get("type")

                    if msg_type == "set_speed":
                        global current_ticks_per_sec
                        new_tps = int(data.get("tps", DEFAULT_TICKS_PER_SEC))
                        current_ticks_per_sec = max(1, new_tps) # Ensure positive speed
                        print(f"Emulator speed set to: {current_ticks_per_sec} TPS")

                    elif msg_type == "key_event_fx0a" and "value" in data:
                        # This specific event is for the Fx0A instruction waiting state
                        key_value = data.get("value")
                        if key_value is not None and 0 <= key_value <= 0xF:
                             await key_event_queue.put(data) # Put the validated event in the queue
                        else:
                             print(f"Ignoring invalid key_event_fx0a: {data}")

                    else:
                        print(f"Received unhandled text message: {data}")

                except json.JSONDecodeError:
                    print(f"Received invalid JSON: {msg['text']}")
                except Exception as e:
                    print(f"Error processing text message: {e}")

            elif "bytes" in msg:
                # Binary messages for standard key up/down state
                key_data = msg["bytes"]
                if len(key_data) >= 2:
                    key_state = key_data[0] # KEY_DOWN or KEY_UP
                    key_index = key_data[1] # 0x0 to 0xF
                    if 0 <= key_index <= 0xF:
                        chip.keypad[key_index] = (key_state == KEY_DOWN)
                        # print(f"Keypad state updated: Key {key_index:X} {'Pressed' if chip.keypad[key_index] else 'Released'}")
                    else:
                        print(f"Received invalid key index in binary message: {key_index}")
                else:
                    print(f"Received short binary message: {key_data}")

    except WebSocketDisconnect:
        print(f"WebSocket disconnected (client closed). Code: {ws.client_state}")
    except Exception as e:
        print(f"An error occurred in WebSocket handling: {e}")
        traceback.print_exc()
    finally:
        # Ensure the emulator runner task is cancelled when the connection closes
        if not runner_task.done():
            runner_task.cancel()
            print("Emulator runner task cancellation requested.")
        try:
            # Wait for the task to acknowledge cancellation
            await runner_task
            print("Emulator runner task finished.")
        except asyncio.CancelledError:
            print("Emulator runner task successfully cancelled.")
        except Exception as e:
             print(f"Error during runner task cleanup: {e}")
        print("WebSocket connection closed.")


# --- Emulator Runner Task ---
async def emulator_runner(ws: WebSocket, key_event_queue: asyncio.Queue):
    """
    Runs the Chip-8 emulation loop.

    Handles CPU cycles based on target TPS, updates timers, manages sound state,
    sends display updates at FRAME_RATE, and handles the Fx0A blocking wait.
    """
    last_frame_update_time = time.perf_counter()
    accumulated_cpu_time_debt = 0.0 # Tracks how much CPU time we owe
    paused_for_key_vx_idx = -1 # Register index waiting for key (-1 means not waiting)
    last_known_sound_state = False # Track sound state to send updates only on change

    try:
        while True:
            # --- ADDED: Reset draw wait flag at start of frame ---
            chip._waiting_for_draw_sync = False
            # ----------------------------------------------------
            current_time = time.perf_counter()
            delta_time = current_time - last_frame_update_time

            # --- Handle Fx0A Waiting State ---
            if paused_for_key_vx_idx != -1:
                try:
                    # Check if a key event has arrived, but don't block indefinitely here.
                    # Use timeout to allow loop to check websocket state etc.
                    key_event = await asyncio.wait_for(key_event_queue.get(), timeout=0.1)
                    key_value = key_event.get("value")

                    if key_value is not None and 0 <= key_value <= 0xF:
                        chip.regs[paused_for_key_vx_idx] = key_value
                        print(f"Key {key_value} received for V{paused_for_key_vx_idx:X}. Resuming execution.")
                        paused_for_key_vx_idx = -1 # Resume execution state
                        # Clear queue in case multiple keys were sent
                        while not key_event_queue.empty():
                            key_event_queue.get_nowait()
                    else:
                        print(f"Invalid key event received while waiting: {key_event}")
                        # Stay paused, loop will try again

                    # Reset timing after getting key to avoid sudden burst of cycles
                    last_frame_update_time = time.perf_counter()
                    accumulated_cpu_time_debt = 0.0
                    continue # Skip the rest of this loop iteration

                except asyncio.TimeoutError:
                    await asyncio.sleep(0.01) # Small sleep prevent busy-waiting
                    continue
                except asyncio.QueueEmpty: # Should be caught by timeout, but just in case
                     await asyncio.sleep(0.01)
                     continue


            # --- Execute CPU Cycles ---
            if paused_for_key_vx_idx == -1: # Only run CPU if not paused
                # Add the real time elapsed to the CPU time we need to simulate
                accumulated_cpu_time_debt += delta_time
                cycles_to_run = int(accumulated_cpu_time_debt * current_ticks_per_sec)

                if cycles_to_run > 0:
                    # Decrease the debt for the cycles we are about to run
                    time_debt_to_remove = cycles_to_run / current_ticks_per_sec
                    accumulated_cpu_time_debt = max(0, accumulated_cpu_time_debt - time_debt_to_remove)

                    for i in range(cycles_to_run):
                        try:
                            if not chip.step():
                                print("Chip8 core halted (step returned False). Stopping runner.")
                                await ws.send_json({"type": "status", "state": "halted"})
                                return # Exit runner task normally
                        except NeedKey as e:
                            if paused_for_key_vx_idx == -1: # Check if already pausing
                                print(f"Chip8 needs key for V{e.vx_idx:X}. Pausing execution.")
                                paused_for_key_vx_idx = e.vx_idx
                                # Notify the frontend that we are waiting
                                await ws.send_json({"type": "need_key", "vx": e.vx_idx})
                            # Stop executing cycles for this frame/debt cycle
                            break # Exit the inner 'for cycles_to_run' loop
                        except Exception as cpu_err:
                            print(f"CRITICAL ERROR during chip.step(): {cpu_err}")
                            traceback.print_exc()
                            await ws.close(code=1011) # Internal Error
                            return # Exit runner task
                        
                        # --- ADDED: Check Display Wait Quirk Flag ---
                        if chip.quirk_display_wait and chip._waiting_for_draw_sync:
                            # Stop executing CPU cycles for this frame after a draw
                            break # Exit inner cycle loop
                        # -----------------------------------------


                    # If NeedKey broke the loop, we need to reset timing before the next iteration's wait check
                    if paused_for_key_vx_idx != -1:
                        last_frame_update_time = time.perf_counter()
                        accumulated_cpu_time_debt = 0.0 # Reset debt as we are pausing
                        continue # Skip frame updates until resumed


            # --- 60Hz Updates (Timers, Sound, Display) ---
            # These happen regardless of CPU cycles executed, tied to real time for FRAME_RATE

            # Update Chip-8 timers (DT and ST)
            chip.update_timers()

            # Check sound state and notify client IF it changed
            current_sound_state = chip.is_sound_on
            if current_sound_state != last_known_sound_state:
                try:
                    await ws.send_json({"type": "sound", "state": "on" if current_sound_state else "off"})
                    last_known_sound_state = current_sound_state
                    # print(f"Sound state changed: {'ON' if current_sound_state else 'OFF'}")
                except WebSocketDisconnect:
                     print("WebSocket disconnected during sound update.")
                     break # Exit the main while loop

            # Send the current framebuffer state
            try:
                await ws.send_bytes(bytes(chip.screen))
            except WebSocketDisconnect:
                print("WebSocket disconnected during display update.")
                break # Exit the main while loop

            # --- Frame Timing / Sleep ---
            # Mark the end of processing for this frame
            processing_end_time = time.perf_counter()
            # Calculate time spent in this iteration's logic
            time_spent_this_iteration = processing_end_time - current_time
            # Calculate how long to sleep to maintain FRAME_RATE
            sleep_duration = max(0, TARGET_FRAME_TIME - time_spent_this_iteration)

            # Update the time marker for the next frame's delta calculation
            last_frame_update_time = current_time # Use start time of iteration for next delta

            # Yield control/sleep
            await asyncio.sleep(sleep_duration)

    # --- Runner Task Cleanup ---
    except WebSocketDisconnect:
        print("Emulator runner stopping due to WebSocket disconnect.")
    except asyncio.CancelledError:
        print("Emulator runner task cancelled.")
    except Exception as e:
        print(f"Emulator runner task crashed: {e}")
        traceback.print_exc()
        try:
            await ws.close(code=1011) # Internal error
        except Exception:
            pass # Ignore errors during close after crash
    finally:
        print("Emulator runner cleanup finished.")


if __name__ == "__main__":
    import uvicorn
    # Make sure static files are served correctly relative to this script
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True) # Use reload for 