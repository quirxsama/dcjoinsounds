#!/bin/bash

# SesAdam Discord Bot durdurma scripti

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

PID_FILE="bot.pid"

# PID dosyası var mı kontrol et
if [[ ! -f "$PID_FILE" ]]; then
    warning "PID dosyası bulunamadı. Bot çalışıyor mu?"
    exit 0
fi

BOT_PID=$(cat "$PID_FILE")

# Process çalışıyor mu kontrol et
if ! kill -0 "$BOT_PID" 2>/dev/null; then
    warning "Bot process bulunamadı (PID: $BOT_PID). PID dosyası temizleniyor."
    rm -f "$PID_FILE"
    exit 0
fi

log "Bot durduruluyor (PID: $BOT_PID)..."

# Graceful shutdown için SIGTERM gönder
kill -TERM "$BOT_PID"

# Process'in kapanmasını bekle
TIMEOUT=30
COUNT=0
while kill -0 "$BOT_PID" 2>/dev/null && [[ $COUNT -lt $TIMEOUT ]]; do
    sleep 1
    ((COUNT++))
    echo -n "."
done
echo ""

if kill -0 "$BOT_PID" 2>/dev/null; then
    warning "Bot graceful shutdown yapmadı. Force kill uygulanıyor..."
    kill -KILL "$BOT_PID"
    sleep 2
fi

if kill -0 "$BOT_PID" 2>/dev/null; then
    error "Bot durdurulamadı!"
    exit 1
else
    log "Bot başarıyla durduruldu"
    rm -f "$PID_FILE"
fi