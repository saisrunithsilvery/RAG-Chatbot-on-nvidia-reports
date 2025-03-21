FROM python:3.10-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8004

# Command to run the application
<<<<<<< HEAD:backend/mistral_ai_service/Dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
=======
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004","--reload"]
>>>>>>> 6267647c562d76f8377640c2746df232af268ba1:backend/data-parsing-backend/mistral_ai_service/Dockerfile
