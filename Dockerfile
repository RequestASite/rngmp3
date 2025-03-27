# Use an official Python runtime as a parent image
FROM python:3.9-buster


# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/

FROM python:3.9-slim-buster

# Install system-level OpenGL libraries
RUN apt-get update && apt-get install -y libgl1-mesa-glx

# Copy your requirements.txt
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ... (rest of your Dockerfile)
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the container at /app
COPY . /app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run app.py when the container launches
CMD ["python", "app.py"]
