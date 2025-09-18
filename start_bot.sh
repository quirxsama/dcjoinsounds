#!/bin/bash

# SesAdam Discord Bot başlatma scripti
# Bu script production-ready özellikler içerir

set -e  # Hata durumunda çık

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log fonksiyonu
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Çalışma dizini kontrolü
if [[ ! -f "sesadam.py" ]]; then
    error "sesadam.py dosyası bulunamadı. Doğru dizinde olduğunuzdan emin olun."
    exit 1
fi

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    error "Python3 bulunamadı. Lütfen Python3 yükleyin."
    exit 1
fi

# Sanal environment kontrolü
if [[ -z "$VIRTUAL_ENV" ]]; then
    warning "Sanal environment aktif değil. requirements.txt'yi kontrol edin."
fi

# Dependencies kontrolü
log "Dependencies kontrol ediliyor..."
python3 -c "import discord, yt_dlp" 2>/dev/null || {
    error "Gerekli paketler yüklü değil. 'pip install -r requirements.txt' çalıştırın."
    exit 1
}

# Downloads klasörü oluştur
mkdir -p downloads

# FFmpeg kontrolü
if ! command -v ffmpeg &> /dev/null; then
    warning "FFmpeg bulunamadı. Ses işlevselliği çalışmayabilir."
fi

# .env dosyası kontrolü
if [[ ! -f ".env" ]]; then
    error ".env dosyası bulunamadı. Lütfen .env dosyasını oluşturun."
    exit 1
fi

# .env dosyasından token kontrolü
if ! grep -q "^DISCORD_BOT_TOKEN=your_bot_token_here" .env; then
    log ".env dosyasında bot token bulundu"
else
    error ".env dosyasında DISCORD_BOT_TOKEN ayarlanmamış!"
    error "Lütfen .env dosyasında gerçek bot token'ınızı ayarlayın."
    exit 1
fi

# PID dosyası kontrolü
PID_FILE="bot.pid"
if [[ -f "$PID_FILE" ]]; then
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        error "Bot zaten çalışıyor (PID: $(cat "$PID_FILE"))"
        exit 1
    else
        warning "Eski PID dosyası temizleniyor..."
        rm -f "$PID_FILE"
    fi
fi

# Bot'u başlat
log "SesAdam Discord Bot başlatılıyor..."
python3 sesadam.py &
BOT_PID=$!

# PID'yi kaydet
echo $BOT_PID > "$PID_FILE"

# Başlatma başarılı mı kontrol et
sleep 3
if kill -0 $BOT_PID 2>/dev/null; then
    log "Bot başarıyla başlatıldı (PID: $BOT_PID)"
    log "Logları takip etmek için: tail -f bot.log"
    log "Bot'u durdurmak için: ./stop_bot.sh"
else
    error "Bot başlatılamadı"
    rm -f "$PID_FILE"
    exit 1
fi