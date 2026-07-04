FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Copy requirements
COPY ui-probes/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy UI probe runner
COPY ui-probes/runner.py .
COPY config/ui-tests.yaml ./config/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run UI probes
ENTRYPOINT ["python", "runner.py"]
CMD ["--environment", "dev", "--browser", "chromium"]
