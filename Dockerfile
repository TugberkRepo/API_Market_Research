# Dockerfile

# Use official Python image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y tzdata
ENV TZ=Europe/Berlin

# Set a working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the files (including final_dev.py and Excel file)
COPY . /app

# By default, run final_dev.py
CMD ["python", "final_dev.py"]