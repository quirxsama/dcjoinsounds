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
RUN mkdir -p /app/downloads

# Disk izinleri (Northflank için)
RUN chmod 777 /app/downloads

# Uygulama kodlarını kopyala
COPY . .

# Cookies dosyasını açıkça kopyala (YouTube auth için)
COPY cookies.txt /app/cookies.txt

# Kalıcı depolama volume tanımı (ses dosyaları için)
VOLUME /app/downloads

# Botu başlat
CMD ["python", "bot.py"]
