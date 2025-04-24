# Set base image. Visit https://hub.docker.com/_/python for more options.
FROM python:3.13-alpine

# Set working directory in the container
WORKDIR /code

# Copy the dependencies file to the working directory and install
# Update requirements.txt as needed.
COPY ./requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY ./src ./src