# Dockerfile at project root
FROM python:3.11-slim

WORKDIR /app

# Copy everything in the project
COPY . .

# Install dependencies (make sure you have requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask port
EXPOSE 5000

# Run the app
CMD ["python", "run.py"]