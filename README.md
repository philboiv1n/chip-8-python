# CHIP-8 Python Emulator 

Yet another CHIP-8 emulator using Docker container.

## Development Environment Setup

Here’s a step-by-step guide to running this project locally using Visual Studio Code and Docker.

1. Clone the repository
Open VS Code and clone this repository locally:
```
git clone https://github.com/philboiv1n/chip-8-python
```

2. Make sure [Docker](https://www.docker.com/) is installed and the engine is started.

3. Build and start the Docker container
From your project root directory:
```
docker compose up --build
```

4. Connect to the container through Visual Studio Code
- Click the Remote Explorer icon (bottom-left corner)
- Select "Attach to Running Container..."
- Choose the container named /chip-8-python
- Open the /code/src/ folder
- Enjoy