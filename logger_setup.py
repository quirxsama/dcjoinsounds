"""
Kapsamlı Loglama Sistemi
Structured logging, renkli console çıktısı ve log rotation
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Renkli console çıktısı için ANSI kodları
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


class ColoredFormatter(logging.Formatter):
    """Renkli console çıktısı için formatter"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DIM + Colors.WHITE,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    
    MODULE_COLORS = {
        'VOICE': Colors.MAGENTA,
        'COMMAND': Colors.CYAN,
        'BOT': Colors.BLUE,
        'POOL': Colors.YELLOW,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Level rengi
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        
        # Modül rengi (logger adına göre)
        module_color = Colors.WHITE
        for module, color in self.MODULE_COLORS.items():
            if module.lower() in record.name.lower():
                module_color = color
                break
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Formatlanmış mesaj
        formatted = (
            f"{Colors.DIM}{timestamp}{Colors.RESET} "
            f"{level_color}[{record.levelname:^8}]{Colors.RESET} "
            f"{module_color}{record.name}{Colors.RESET}: "
            f"{record.getMessage()}"
        )
        
        # Exception bilgisi varsa ekle
        if record.exc_info:
            formatted += f"\n{Colors.RED}{self.formatException(record.exc_info)}{Colors.RESET}"
        
        return formatted


class StructuredFormatter(logging.Formatter):
    """Dosya logları için structured formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = {
            'timestamp': timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Guild/Channel/User bilgisi varsa ekle
        for attr in ['guild_id', 'channel_id', 'user_id', 'guild_name', 'user_name']:
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)
        
        # Exception bilgisi varsa ekle
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Basit format - JSON benzeri ama okunabilir
        parts = [f"[{timestamp}]", f"[{record.levelname:^8}]", f"[{record.name}]"]
        
        # Ek bilgiler
        extras = []
        for attr in ['guild_id', 'user_id', 'channel_id']:
            if hasattr(record, attr):
                extras.append(f"{attr}={getattr(record, attr)}")
        
        if extras:
            parts.append(f"[{', '.join(extras)}]")
        
        parts.append(record.getMessage())
        
        result = ' '.join(parts)
        
        if record.exc_info:
            result += f"\n{self.formatException(record.exc_info)}"
        
        return result


class BotLogger:
    """Bot için merkezi logger yönetimi"""
    
    def __init__(
        self,
        log_file: str = "bot.log",
        log_level: str = "INFO",
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        enable_console: bool = True,
    ):
        self.log_file = Path(log_file)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        
        # Loggers dictionary
        self._loggers: dict[str, logging.Logger] = {}
        
        # Root logger ayarla
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Root logger'ı yapılandır"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Mevcut handler'ları temizle
        root_logger.handlers.clear()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(ColoredFormatter())
            root_logger.addHandler(console_handler)
        
        # File handler (rotating)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Discord.py loglarını ayarla
        discord_logger = logging.getLogger('discord')
        discord_logger.setLevel(logging.WARNING)  # Sadece warning ve üstü
        
        # Voice debug logları
        voice_logger = logging.getLogger('discord.voice_state')
        voice_logger.setLevel(logging.INFO)
    
    def get_logger(self, name: str) -> logging.Logger:
        """İsimli logger al veya oluştur"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(self.log_level)
            self._loggers[name] = logger
        return self._loggers[name]
    
    @staticmethod
    def voice(message: str, **kwargs):
        """Voice olayları için özel log"""
        logger = logging.getLogger('bot.voice')
        extra = {k: v for k, v in kwargs.items()}
        logger.info(message, extra=extra)
    
    @staticmethod
    def command(message: str, **kwargs):
        """Komut kullanımı için özel log"""
        logger = logging.getLogger('bot.command')
        extra = {k: v for k, v in kwargs.items()}
        logger.info(message, extra=extra)
    
    @staticmethod
    def error(message: str, exc_info: bool = False, **kwargs):
        """Hata logları için özel log"""
        logger = logging.getLogger('bot.error')
        extra = {k: v for k, v in kwargs.items()}
        logger.error(message, exc_info=exc_info, extra=extra)
    
    @staticmethod
    def debug(message: str, **kwargs):
        """Debug logları için özel log"""
        logger = logging.getLogger('bot.debug')
        extra = {k: v for k, v in kwargs.items()}
        logger.debug(message, extra=extra)


# Global logger instance
_bot_logger: Optional[BotLogger] = None


def setup_logging(
    log_file: str = "bot.log",
    log_level: str = "INFO",
    **kwargs
) -> BotLogger:
    """Global logging sistemini kur"""
    global _bot_logger
    _bot_logger = BotLogger(log_file=log_file, log_level=log_level, **kwargs)
    return _bot_logger


def get_logger(name: str) -> logging.Logger:
    """Global logger'dan isimli logger al"""
    if _bot_logger is None:
        setup_logging()
    return _bot_logger.get_logger(name)  # type: ignore
