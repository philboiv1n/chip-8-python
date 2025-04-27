FROM python:3.13-alpine
WORKDIR /code

# Copy and install only the web dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy your app and static assets
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Launch Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]