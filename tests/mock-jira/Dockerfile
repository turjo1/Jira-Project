FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mock Jira code
COPY mock_jira/ ./mock_jira/

# Expose port
EXPOSE 8000

# Run the mock server
CMD ["python", "-m", "uvicorn", "mock_jira.server:app", "--host", "0.0.0.0", "--port", "8000"]
