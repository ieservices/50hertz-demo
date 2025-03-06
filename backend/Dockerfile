FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Set the working directory (the base image defaults to /app)
WORKDIR /app

# Copy your code into the image
COPY . /app

RUN pip install --no-cache-dir --upgrade -r requirements.txt

#CMD ["fastapi", "run", "main.py", "--port", "80"]

EXPOSE 80