"""
Bot yapılandırma dosyası
Production-ready ayarlar
"""

import os
from typing import Dict, Any

# Bot yapılandırması
BOT_CONFIG = {
    'token_env_var': 'DISCORD_BOT_TOKEN',
    'command_prefix': '/',
    'max_file_size_mb': 10,
    'audio_trim_max_seconds': 15,
    'voice_connection_timeout': 10.0,
    'reconnection_max_retries': 3,
    'reconnection_backoff_base': 2,
    'heartbeat_timeout': 60.0,
    'guild_ready_timeout': 5.0,
    'log_level': 'INFO',
    'log_file': 'bot.log'
}

# Voice connection ayarları
VOICE_CONFIG = {
    'ffmpeg_options': '-vn -b:a 96k',
    'audio_quality': '96k',
    'max_playback_time': 30,  # saniye
    'connection_retry_delay': 1,  # saniye
    'cleanup_interval': 300  # 5 dakika
}

# Dosya uzantıları
SUPPORTED_AUDIO_FORMATS = [
    '.mp3', '.webm', '.mp4', '.m4a', '.wav',
    '.flac', '.ogg', '.aac', '.wma'
]

# FFmpeg yolları (Linux)
FFMPEG_PATHS = [
    '/usr/bin/ffmpeg',
    '/usr/local/bin/ffmpeg',
    '/opt/ffmpeg/bin/ffmpeg',
    'ffmpeg'  # PATH'den ara
]

# Downloads klasörü
DOWNLOADS_DIR = 'downloads'

def get_token() -> str:
    """Bot token'ını environment variable'dan al"""
    token = os.getenv(BOT_CONFIG['token_env_var'])
    if not token:
        raise ValueError(f"Environment variable {BOT_CONFIG['token_env_var']} bulunamadı!")
    return token

def ensure_directories():
    """Gerekli klasörlerin varlığını kontrol et"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # Log klasörü
    log_dir = os.path.dirname(BOT_CONFIG['log_file'])
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

def get_ffmpeg_path() -> str:
    """FFmpeg yolunu bul"""
    for path in FFMPEG_PATHS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # PATH'de ara
    import shutil
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path

    raise FileNotFoundError("FFmpeg bulunamadı. Lütfen FFmpeg'i yükleyin.")