FROM python:3.11-slim

# Sistem bağımlılıklarını yükle (FFmpeg ve Opus gerekli)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarla
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Northflank kalıcı depolama klasörü
RUN mkdir -p /app/data
RUN mkdir -p /app/downloads

# Disk izinleri (Northflank için)
RUN chmod 777 /app/data
RUN chmod 777 /app/downloads

# Uygulama kodlarını kopyala
COPY . .

# Kalıcı depolama volume tanımı
VOLUME /app/data

# Botu başlat
CMD ["python", "bot.py"]
