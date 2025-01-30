# Use the default Alpine Linux image for a lightweight container
FROM alpine:latest

# Set environment variables to prevent Python from writing pyc files to disk and buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install necessary dependencies including Python, pip, and system utilities
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    libffi-dev \
    openssl-dev \
    gcc \
    musl-dev \
    git \
    curl

# Set the working directory inside the container
WORKDIR /bot

# Create a virtual environment and activate it
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements.txt file into the working directory
COPY requirements.txt /bot/

# Install Python dependencies from the requirements.txt file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot's source code into the working directory
COPY . /bot/

# Command to run your bot
CMD ["python3", "bot.py"]