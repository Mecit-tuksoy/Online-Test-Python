FROM python:3.10-slim
WORKDIR /app
# Volume olarak dışarıdan test verilerini alacağımız klasörü (data) eklemeyi unutmayın;
# Docker-compose ile bu klasörü mount edeceğiz.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && apt install -y default-mysql-client
RUN apt install -y curl
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
