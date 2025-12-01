# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variable to ensure output is sent to logs immediately
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run monitor.py when the container launches
CMD ["python", "monitor.py"]
