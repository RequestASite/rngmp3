# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install playwright
RUN playwright install

# Copy the application code into the container
COPY . .

# Expose the port that your application listens on
EXPOSE 8080

# Run the application
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080"] # or your specific gunicorn command.