FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate icons if not present
RUN python generate_icons.py

EXPOSE 8000

ENV PORT=8000

CMD ["python", "server.py"]
