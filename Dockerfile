# 1. Base image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy requirements & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries=5 -r requirements.txt

# 4. Copy project files
COPY . .

# 5. Expose port
EXPOSE 8000

# 6. Set environment variables (optional, can override saat run)
ENV PYTHONUNBUFFERED=1

# 7. Run uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
