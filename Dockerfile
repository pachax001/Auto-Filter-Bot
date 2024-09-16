# Use a stable slim version of Debian as the base image
FROM debian:stable-slim

# Set environment variables to prevent Python from writing pyc files to disc and buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
# This includes software-properties-common to manage repositories and Python-related tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /bot

# Copy the requirements.txt file into the working directory
COPY requirements.txt /bot/

# Install Python dependencies from the requirements.txt file
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of your bot's source code into the working directory
COPY . /bot/

# Command to run your bot
CMD ["python3", "bot.py"]
