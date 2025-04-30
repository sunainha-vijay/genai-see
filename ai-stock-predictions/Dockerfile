# Dockerfile for AI Stock Predictions Flask App

# 1. Base Image: Use an official Python runtime as a parent image
# Using python:3.11 to match your environment indicated in previous logs.
# '-slim' variants are smaller than the full images. '-bullseye' is a common stable Debian version.
FROM python:3.11-slim-bullseye

# 2. Set Environment Variables
# Prevents Python from buffering stdout/stderr, making logs appear immediately
ENV PYTHONUNBUFFERED=1
# Set the port the application will run on inside the container
ENV PORT=8080
# Set the working directory inside the container
WORKDIR /app

# 3. Install Dependencies
# Copy *only* the requirements file first to leverage Docker cache
# If requirements.txt hasn't changed, Docker won't re-run pip install
COPY requirements.txt .

# Install dependencies specified in requirements.txt
# --no-cache-dir reduces image size by not storing the pip cache
# --upgrade pip ensures the latest pip is used
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Code
# Copy the rest of your application code into the container's working directory
COPY . .

# 5. Expose Port
# Inform Docker that the container listens on the specified port at runtime
EXPOSE 8080

# 6. Define Start Command
# Command to run your application using Gunicorn when the container starts
# Binds Gunicorn to listen on all interfaces (0.0.0.0) on the specified port ($PORT, which is 8080)
# 'app:app' means: look for the file 'app.py' and find the Flask object named 'app' within it.
# Adjust the number of workers (-w) based on your instance resources if needed (e.g., -w 2 or -w 4 for more CPU)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]