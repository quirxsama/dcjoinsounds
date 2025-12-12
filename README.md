# SesAdam Discord Bot

Kullanıcılar ses kanalına girdiğinde otomatik olarak kişisel ses dosyalarını çalan Discord bot. **Birden fazla sunucu ve kanalda eşzamanlı çalışır.**

## 🎉 v2.0 - Büyük Güncelleme (2024)

### Yeni Özellikler

- ✅ **Çoklu Kanal Desteği** - Her sunucuda 5 kanala aynı anda bağlanabilir
- ✅ **Modüler Mimari** - Cog sistemi ile düzenli kod yapısı
- ✅ **Gelişmiş Loglama** - Renkli console, log rotation, structured logs
- ✅ **VoicePool** - Thread-safe, concurrent voice connection yönetimi
- ✅ **Graceful Shutdown** - Signal handling ile düzgün kapanma

### Değişiklikler

- `sesadam.py` → `bot.py` (yeni modüler yapı)
- `voice_manager.py` → `voice_pool.py` (çoklu kanal desteği)
- Yeni `logger_setup.py` (kapsamlı loglama)
- Yeni `commands/` modülü (Cog yapısı)

---

## Özellikler

- **YouTube'dan ses yükleme**: `/sesyukle` komutu ile YouTube'dan ses indirin
- **Dosya yükleme**: `/dosyaekle` ile MP3, WEBM, WAV vb. formatları yükleyin
- **Ses yönetimi**: `/seskaldir` ve `/seslistesi` komutları
- **Bot durumu**: `/botstatus` ile istatistikleri görün
- **Otomatik çalma**: Kullanıcı kanala girdiğinde sesi otomatik çalınır
- **24/7 stabil**: VoicePool ile production-ready voice yönetimi

## Hızlı Kurulum

### Gereksinimler

- Python 3.10+
- FFmpeg

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg python3 python3-pip

# Repository klonla
git clone https://github.com/quirxsama/soundman.git
cd soundman

# Sanal environment
python3 -m venv venv
source venv/bin/activate

# Bağımlılıklar
pip install -r requirements.txt

# Token ayarla
cp .env.example .env
nano .env  # DISCORD_BOT_TOKEN=your_token

# Başlat
./start_bot.sh
```

## Komutlar

| Komut                              | Açıklama                        |
| ---------------------------------- | ------------------------------- |
| `/sesyukle [url] [start] [end]`    | YouTube'dan ses indir (max 15s) |
| `/dosyaekle [dosya] [start] [end]` | Ses dosyası yükle               |
| `/seskaldir`                       | Sesinizi kaldırın               |
| `/seslistesi`                      | Tüm sesleri listele             |
| `/botstatus`                       | Bot istatistikleri              |

## Yapılandırma

### .env Dosyası

```env
DISCORD_BOT_TOKEN=your_token_here
LOG_LEVEL=INFO
DOWNLOADS_DIR=downloads
```

### config.py Ayarları

```python
VOICE_CONFIG = {
    'max_sessions_per_guild': 5,  # Sunucu başına kanal limiti
    'session_timeout': 60.0,       # Idle timeout (saniye)
    'connection_timeout': 15.0,    # Bağlantı timeout
}
```

## Production (Systemd)

```bash
# Servis kopyala
sudo cp sesadam.service /etc/systemd/system/

# Başlat
sudo systemctl daemon-reload
sudo systemctl enable sesadam
sudo systemctl start sesadam

# Durum
sudo systemctl status sesadam
sudo journalctl -u sesadam -f
```

## 🚂 Railway Deploy

### 1. Railway'e Bağlan

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Repository'yi seç: `quirxsama/soundman`

### 2. Volume Oluştur (Kalıcı Veri için)

1. Proje dashboard'unda **+ New** → **Volume**
2. Mount path: `/data`
3. Volume'u service'e bağla

### 3. Environment Variables

Railway dashboard'da **Variables** sekmesine git:

```env
DISCORD_BOT_TOKEN=your_token_here
RAILWAY_VOLUME_MOUNT_PATH=/data
```

### 4. Deploy

Otomatik deploy başlayacak. Logları **Deployments** sekmesinden takip edin.

## Proje Yapısı

```
dcjoinsounds/
├── bot.py              # Ana bot dosyası
├── voice_pool.py       # Çoklu kanal yönetimi
├── logger_setup.py     # Loglama sistemi
├── config.py           # Yapılandırma
├── commands/
│   ├── __init__.py
│   └── audio.py        # Ses komutları (Cog)
├── downloads/          # Ses dosyaları
├── .env                # Token (git'e commit edilmez)
└── requirements.txt
```

## Sorun Giderme

### Log Analizi

```bash
# Canlı log takibi
tail -f bot.log

# Voice olayları
grep -i voice bot.log | tail -20

# Hatalar
grep -i error bot.log | tail -20
```

### Yaygın Sorunlar

- **FFmpeg bulunamadı**: `sudo apt install ffmpeg`
- **Token hatası**: `.env` dosyasını kontrol edin
- **Bağlantı timeout**: Network/firewall kontrolü

## Desteklenen Formatlar

**Ses:** MP3, WEBM, MP4, M4A, WAV, FLAC, OGG, AAC, WMA  
**Max Boyut:** 10MB  
**Max Süre:** 15 saniye

## Lisans

MIT License
