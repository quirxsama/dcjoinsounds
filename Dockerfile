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

# Uygulama kodlarını kopyala
COPY . .

# İndirme klasörünü oluştur
RUN mkdir -p downloads

# Botu başlat
CMD ["python", "bot.py"]
