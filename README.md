# CHIP-8 Python Emulator 

A lightweight, Docker‑based Python CHIP‑8 emulator featuring a FastAPI HTTP & WebSocket interface for web front‑ends, plus an optional PyTest compliance suite.

## Prerequisites
- Docker Engine
- Python 3.10+
- (Optional) VS Code with the Remote – Containers extension

The emulator has been tested with several ROMs (most compliance tests passing), although some classic demos still exhibit timing or input issues.
This is for educational purpose only.

## Development Environment Setup

Here’s a step-by-step guide to running this project locally using Visual Studio Code and Docker.

1. Clone the repository
Open VS Code and clone this repository locally:
```bash
git clone https://github.com/philboiv1n/chip-8-python
```

2. Build and start the Docker container
From your project root directory:
```bash
docker compose up --build
```

3. Run the emulator
Open a browser to http://localhost:8000.

4. (Optional) Attach in VS Code
To edit or run Python/PyTest commands, attach VS Code to the running container:
- Click the Remote Explorer icon (bottom-left corner)
- Select "Attach to Running Container..."
- Choose the container named /chip-8-python
- Open the /code/src/ folder
- Enjoy

5. Run tests
Run the test suite:
```bash
pytest -q
```

## Contributing
Contributions welcome! Please open an issue or pull request.

## License
This project is licensed under the MIT License.