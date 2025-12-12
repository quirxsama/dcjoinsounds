"""
Bot yapılandırma dosyası
Production-ready ayarlar - Çoklu kanal desteği
"""

import os
import shutil
from typing import Dict, Any, Optional

# Bot yapılandırması
BOT_CONFIG: Dict[str, Any] = {
    'token_env_var': 'DISCORD_BOT_TOKEN',
    'command_prefix': '/',
    'max_file_size_mb': 10,
    'audio_trim_max_seconds': 15,
    'heartbeat_timeout': 60.0,
    'guild_ready_timeout': 5.0,
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'log_file': os.getenv('LOG_FILE', 'bot.log'),
}

# Voice connection ayarları - Çoklu kanal desteği
VOICE_CONFIG: Dict[str, Any] = {
    # Çoklu bağlantı ayarları
    'max_sessions_per_guild': 5,  # Sunucu başına maksimum eşzamanlı ses kanalı
    'session_timeout': 60.0,       # Idle session timeout (saniye)
    'connection_timeout': 15.0,    # Bağlantı timeout
    'max_retries': 3,              # Bağlantı retry sayısı
    
    # Ses ayarları
    'ffmpeg_options': '-vn -b:a 96k',
    'audio_quality': '96k',
    'max_playback_time': 30,  # saniye
    
    # Cleanup ayarları
    'cleanup_interval': 30,  # saniye
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

# Downloads klasörü - Railway volume desteği
# Railway'de volume mount path: /data
_volume_path = os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '')
if _volume_path:
    DOWNLOADS_DIR = os.path.join(_volume_path, 'downloads')
else:
    DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', 'downloads')


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
    log_file = BOT_CONFIG.get('log_file', 'bot.log')
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)


def get_ffmpeg_path() -> str:
    """FFmpeg yolunu bul"""
    # Önce PATH'de ara
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # Yaygın konumlarda ara
    for path in FFMPEG_PATHS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    raise FileNotFoundError("FFmpeg bulunamadı. Lütfen FFmpeg'i yükleyin.")


def get_config_summary() -> dict:
    """Yapılandırma özetini al"""
    return {
        'bot': {
            'prefix': BOT_CONFIG['command_prefix'],
            'log_level': BOT_CONFIG['log_level'],
        },
        'voice': {
            'max_sessions_per_guild': VOICE_CONFIG['max_sessions_per_guild'],
            'session_timeout': VOICE_CONFIG['session_timeout'],
        },
        'audio': {
            'max_duration': BOT_CONFIG['audio_trim_max_seconds'],
            'max_file_size_mb': BOT_CONFIG['max_file_size_mb'],
            'quality': VOICE_CONFIG['audio_quality'],
        }
    }