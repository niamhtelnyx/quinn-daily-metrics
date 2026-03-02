FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "uvicorn", "demo_call_api:app", "--host", "0.0.0.0", "--port", "8080"]