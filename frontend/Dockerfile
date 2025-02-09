FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && apt install curl -y
COPY . .
EXPOSE 80
CMD ["python", "app.py"]
