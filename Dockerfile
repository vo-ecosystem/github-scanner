FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -s /bin/bash scanner && \
    chown -R scanner:scanner /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY --chown=scanner:scanner scanner.py .

# Switch to non-root user
USER scanner

# Run script
ENTRYPOINT ["python", "scanner.py"]
