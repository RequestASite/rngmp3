# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the pre-downloaded apt packages (Crucial!)

# Copy the requirements file into the container
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the pre downloaded chromium directory.

# Force playwright install to run by invalidating cache
RUN date > /tmp/force_rebuild

# Install playwright browsers
RUN playwright install chromium

# Copy the ffmpeg directory
COPY ffmpeg-master-latest-win64-gpl-shared /usr/local/ffmpeg

# Copy the application code into the container
COPY . .

# Expose the port that your application listens on
EXPOSE 8080

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]