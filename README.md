# SesAdam Discord Bot

Bu Discord botu kullanıcıların ses dosyalarını yüklemesine ve YouTube linklerinden ses çıkarmasına olanak tanır. Ses kanallarında otomatik olarak çalınır ve 15 saniyeye kadar kırpılır.

## Özellikler

- **YouTube linkinden ses yükleme**: `/sesyukle` komutu ile YouTube'dan ses indirip kırpın.
- **Ses dosyası yükleme**: `/dosyaekle` komutu ile MP3, WEBM, MP4, M4A, WAV, FLAC, OGG, AAC, WMA formatlarındaki dosyaları yükleyin.
- **Ses yönetimi**: `/seskaldir` ile yüklediğiniz sesi, `/seslistesi` ile tüm sesleri listeleyin.
- **Otomatik ses çalma**: Kullanıcı ses kanalına girdiğinde otomatik olarak sesi çalınır.
- **24/7 stabil çalışma**: VoiceManager ile thread-safe voice connection yönetimi.
- **Gelişmiş reconnection**: Otomatik reconnection, session persistence, exponential backoff.
- **Production-ready**: Systemd servis desteği, detaylı logging, monitoring, graceful shutdown.
- **Debug logging**: Voice ve gateway bağlantılarını detaylı loglama.

## Kurulum

### Ön Gereksinimler

1. **Python 3.13+**: Python 3.13 veya üzeri gerekli.
2. **FFmpeg**: Ses işleme için gerekli.

   **Ubuntu/Debian**:
   ```bash
   sudo apt update
   sudo apt install ffmpeg python3 python3-pip
   ```

   **CentOS/RHEL**:
   ```bash
   sudo yum install ffmpeg python3 python3-pip
   ```

   **Windows/macOS**: [FFmpeg resmi sitesinden](https://ffmpeg.org/download.html) indirin.

### Hızlı Kurulum

1. **Repository'yi klonlayın**:
   ```bash
   git clone https://github.com/quirxsama/soundman.git
   cd soundman
   ```

2. **Sanal environment oluşturun**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Bağımlılıkları yükleyin**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Bot token'ınızı ayarlayın**:
   ```bash
   # .env dosyasını düzenleyin
   nano .env

   # Aşağıdaki satırı gerçek bot token'ınızla değiştirin
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   ```

   **.env dosya içeriği örneği:**
   ```env
   # Discord Bot Configuration
   DISCORD_BOT_TOKEN=your_actual_bot_token_here

   # Bot Settings
   BOT_PREFIX=/
   LOG_LEVEL=INFO

   # Voice Settings
   VOICE_TIMEOUT=10.0
   AUDIO_MAX_DURATION=15
   AUDIO_QUALITY=96k

   # File Settings
   MAX_FILE_SIZE_MB=10
   DOWNLOADS_DIR=downloads
   ```

5. **Bot'u başlatın**:
   ```bash
   ./start_bot.sh
   ```

### Production Kurulumu (Systemd)

1. **Bot kullanıcısı oluşturun**:
   ```bash
   sudo useradd -m -s /bin/bash discordbot
   sudo usermod -aG audio discordbot  # Ses için gerekli
   ```

2. **Dosyaları kopyalayın**:
   ```bash
   sudo cp -r /path/to/soundman /home/discordbot/
   sudo chown -R discordbot:discordbot /home/discordbot/soundman
   ```

3. **Systemd servisini yükleyin**:
   ```bash
   sudo cp sesadam.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable sesadam
   sudo systemctl start sesadam
   ```

4. **Token'ı ayarlayın**:
   ```bash
   sudo systemctl edit sesadam
   # [Service] bölümüne ekleyin:
   # Environment=DISCORD_BOT_TOKEN=your_actual_token
   sudo systemctl restart sesadam
   ```

## Komutlar

- `/sesyukle [url] [start_time] [end_time]`: YouTube linkinden ses indirip kırpın.
- `/dosyaekle [dosya] [start_time] [end_time]`: Ses dosyası yükleyin.
- `/seskaldir`: Yüklediğiniz sesi kaldırın.
- `/seslistesi`: Tüm sesleri listeleyin.

## Sorun Giderme

### 4006 WebSocket Hatası

Bu hata genellikle session ID kaybından veya paralel bağlantı denemelerinden kaynaklanır:

**Nedenler:**
- İnternet bağlantısı kesintisi
- Discord Gateway sorunları
- Session timeout
- Aynı token ile birden fazla bot instance
- Paralel voice connection denemeleri
- Race conditions

**Çözümler:**
- VoiceManager otomatik olarak reconnection yapar
- Session data persist edilir
- Exponential backoff uygulanır
- Thread-safe connection locking
- Detaylı debug logları: `tail -f bot.log`
- Sadece tek bot instance çalıştırın

### Diğer Voice Bağlantı Hataları

- **ConnectionClosed (4006)**: Session ID hatası - VoiceManager otomatik retry
- **ConnectionClosed (4014)**: Session timeout - yeniden authentication
- **ConnectionClosed (4000)**: Bilinmeyen hata - detaylı log kontrolü
- **Voice handshake failed**: FFmpeg eksik veya network sorunu
- **Cannot write to closing transport**: Paralel bağlantı denemeleri - VoiceManager lock ile çözüldü
- **RuntimeError: Voice connect failed**: Tüm retry denemeleri başarısız - network/gateway sorunu

### Log Analizi

```bash
# Detaylı voice bağlantı logları
tail -f bot.log | grep -E "(Voice|voice|connect|handshake)"

# Session ve reconnection logları
tail -f bot.log | grep -E "(session|resume|disconnect)"

# Hata analizi
tail -f bot.log | grep -E "(ERROR|exception|failed)"

# VoiceManager işlemleri
tail -f bot.log | grep -E "(VoiceManager|connect_with_backoff|cleanup)"

# Gateway logları (debug mode)
tail -f bot.log | grep -E "(gateway|Gateway)"

# Bağlantı durumu
sudo systemctl status sesadam
```

## Production Best Practices

### Monitoring

```bash
# Servis durumu
sudo systemctl status sesadam

# Log takip
sudo journalctl -u sesadam -f

# Resource kullanımı
sudo systemctl show sesadam --property=MemoryCurrent,CPUUsageNSec
```

### Backup

```bash
# Downloads klasörünü yedekle
tar -czf backup_$(date +%Y%m%d).tar.gz downloads/

# Log rotasyonu
sudo logrotate /etc/logrotate.d/sesadam
```

### Güvenlik

- **Bot token'ını .env dosyasında tutun** - Git'e commit edilmez
- Dosya upload'larını sınırlandırın (10MB max)
- Rate limiting uygulayın
- Güvenli dosya uzantıları kontrolü
- Environment variable'ları production'da güvenli şekilde ayarlayın

**Önemli:** `.env` dosyası `.gitignore`'a eklenmiştir ve git'e commit edilmez.

## Desteklenen Formatlar

**Ses Formatları:** MP3, WEBM, MP4, M4A, WAV, FLAC, OGG, AAC, WMA
**Maksimum Dosya Boyutu:** 10MB
**Maksimum Ses Süresi:** 15 saniye
