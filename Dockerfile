# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libasound2 && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install playwright

# Force playwright install to run by invalidating cache
RUN date > /tmp/force_rebuild 

# Install playwright browsers
RUN playwright install

# Copy the application code into the container
COPY . .

# Expose the port that your application listens on
EXPOSE 8080

# Run the application
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080"] # or your specific gunicorn command.
