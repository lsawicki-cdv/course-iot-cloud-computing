FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api.py .

# Expose API port
EXPOSE 5000

# Run the API
CMD ["python", "api.py"]
