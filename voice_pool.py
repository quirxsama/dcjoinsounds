"""
Voice Pool - Çoklu ses kanalı yönetimi
Her sunucuda birden fazla ses kanalına eşzamanlı bağlantı desteği
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Tuple, Set
from collections import defaultdict

import discord
from discord.ext import tasks

from logger_setup import get_logger

log = get_logger('bot.voice_pool')


@dataclass
class VoiceSession:
    """Tek bir voice bağlantısını temsil eder"""
    guild_id: int
    channel_id: int
    user_id: int  # Sesi tetikleyen kullanıcı
    voice_client: discord.VoiceClient
    started_at: datetime = field(default_factory=datetime.now)
    is_playing: bool = False
    
    @property
    def key(self) -> Tuple[int, int]:
        """Session için benzersiz anahtar (guild_id, channel_id)"""
        return (self.guild_id, self.channel_id)
    
    @property
    def age_seconds(self) -> float:
        """Session yaşı (saniye)"""
        return (datetime.now() - self.started_at).total_seconds()


class VoicePool:
    """
    Çoklu ses kanalı yönetimi.
    Her sunucuda birden fazla kanala eşzamanlı bağlantı destekler.
    """
    
    def __init__(
        self,
        bot: discord.Client,
        max_sessions_per_guild: int = 5,
        session_timeout: float = 60.0,
        connection_timeout: float = 15.0,
        max_retries: int = 3,
    ):
        self.bot = bot
        self.max_sessions_per_guild = max_sessions_per_guild
        self.session_timeout = session_timeout
        self.connection_timeout = connection_timeout
        self.max_retries = max_retries
        
        # Aktif sessionlar: (guild_id, channel_id) -> VoiceSession
        self._sessions: Dict[Tuple[int, int], VoiceSession] = {}
        
        # Guild başına lock - paralel bağlantı denemelerini önlemek için
        self._guild_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # Channel bazlı lock - aynı kanala paralel bağlantı önleme
        self._channel_locks: Dict[Tuple[int, int], asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # Aktif playback takibi - (guild_id, channel_id) -> playing
        self._active_playbacks: Set[Tuple[int, int]] = set()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup_task(self):
        """Periyodik cleanup task'ını başlat"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            log.info("Cleanup task başlatıldı")
    
    async def _cleanup_loop(self):
        """Periyodik olarak expired sessionları temizle"""
        while True:
            try:
                await asyncio.sleep(30)  # Her 30 saniyede bir kontrol
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Cleanup loop hatası: {e}", exc_info=True)
    
    async def _cleanup_expired_sessions(self):
        """Süresi dolmuş sessionları temizle"""
        expired = []
        
        for key, session in self._sessions.items():
            # Session timeout kontrolü
            if session.age_seconds > self.session_timeout and not session.is_playing:
                expired.append(key)
        
        for key in expired:
            try:
                await self.disconnect(key[0], key[1])
                log.info(f"Expired session temizlendi: guild={key[0]}, channel={key[1]}")
            except Exception as e:
                log.error(f"Expired session temizlenirken hata: {e}")
    
    def get_session(self, guild_id: int, channel_id: int) -> Optional[VoiceSession]:
        """Belirli bir kanal için session al"""
        return self._sessions.get((guild_id, channel_id))
    
    def get_guild_sessions(self, guild_id: int) -> list[VoiceSession]:
        """Bir sunucudaki tüm sessionları al"""
        return [s for s in self._sessions.values() if s.guild_id == guild_id]
    
    def is_playing(self, guild_id: int, channel_id: int) -> bool:
        """Belirli bir kanalda ses çalınıyor mu?"""
        return (guild_id, channel_id) in self._active_playbacks
    
    def guild_session_count(self, guild_id: int) -> int:
        """Bir sunucudaki aktif session sayısı"""
        return len(self.get_guild_sessions(guild_id))
    
    async def connect(
        self,
        channel: discord.VoiceChannel,
        user_id: int,
    ) -> Optional[VoiceSession]:
        """
        Ses kanalına bağlan veya mevcut bağlantıyı kullan.
        Thread-safe ve retry desteği ile.
        """
        guild_id = channel.guild.id
        channel_id = channel.id
        key = (guild_id, channel_id)
        
        # Channel bazlı lock al
        async with self._channel_locks[key]:
            # Mevcut session var mı kontrol et
            existing = self._sessions.get(key)
            if existing and existing.voice_client.is_connected():
                log.debug(f"Mevcut session kullanılıyor: {channel.name}")
                return existing
            
            # Guild session limiti kontrolü
            if self.guild_session_count(guild_id) >= self.max_sessions_per_guild:
                log.warning(f"Guild session limiti aşıldı: guild={guild_id}")
                # En eski idle session'ı kapat
                await self._evict_oldest_session(guild_id)
            
            # Yeni bağlantı oluştur
            voice_client = await self._connect_with_retry(channel)
            
            if voice_client is None:
                return None
            
            # Session oluştur
            session = VoiceSession(
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
                voice_client=voice_client,
            )
            
            self._sessions[key] = session
            log.info(
                f"Yeni voice session oluşturuldu: {channel.name}",
                extra={'guild_id': guild_id, 'channel_id': channel_id, 'user_id': user_id}
            )
            
            return session
    
    async def _connect_with_retry(
        self,
        channel: discord.VoiceChannel,
    ) -> Optional[discord.VoiceClient]:
        """Retry desteği ile ses kanalına bağlan"""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                log.debug(f"Bağlantı denemesi {attempt}/{self.max_retries}: {channel.name}")
                
                voice_client = await asyncio.wait_for(
                    channel.connect(timeout=self.connection_timeout, reconnect=True),
                    timeout=self.connection_timeout + 5
                )
                
                log.info(f"Ses kanalına bağlandı: {channel.name}")
                return voice_client
                
            except asyncio.TimeoutError as e:
                log.warning(f"Bağlantı timeout (deneme {attempt}): {channel.name}")
                last_error = e
                
            except discord.errors.ClientException as e:
                # Zaten bağlı olabilir
                if "Already connected" in str(e):
                    existing_vc = channel.guild.voice_client
                    if existing_vc and existing_vc.channel.id == channel.id:
                        return existing_vc
                log.warning(f"Client exception (deneme {attempt}): {e}")
                last_error = e
                
            except Exception as e:
                log.error(f"Beklenmeyen bağlantı hatası (deneme {attempt}): {e}")
                last_error = e
            
            # Retry öncesi bekleme (exponential backoff)
            if attempt < self.max_retries:
                delay = 2 ** (attempt - 1)
                await asyncio.sleep(delay)
        
        log.error(f"Bağlantı başarısız: {channel.name}, son hata: {last_error}")
        return None
    
    async def _evict_oldest_session(self, guild_id: int):
        """En eski idle session'ı kapat"""
        guild_sessions = self.get_guild_sessions(guild_id)
        
        # Oynatma yapmayanları bul ve yaşa göre sırala
        idle_sessions = [s for s in guild_sessions if not s.is_playing]
        idle_sessions.sort(key=lambda s: s.started_at)
        
        if idle_sessions:
            oldest = idle_sessions[0]
            await self.disconnect(oldest.guild_id, oldest.channel_id)
            log.info(f"Eski session kapatıldı (limit aşımı): channel={oldest.channel_id}")
    
    async def play_audio(
        self,
        guild_id: int,
        channel_id: int,
        audio_source: discord.AudioSource,
        wait_for_completion: bool = True,
    ) -> bool:
        """
        Belirtilen kanalda ses çal.
        Returns: Başarılı ise True
        """
        key = (guild_id, channel_id)
        session = self._sessions.get(key)
        
        if not session or not session.voice_client.is_connected():
            log.warning(f"Ses çalınamadı: Session bulunamadı veya bağlı değil")
            return False
        
        if key in self._active_playbacks:
            log.debug(f"Zaten ses çalınıyor: channel={channel_id}")
            return False
        
        try:
            self._active_playbacks.add(key)
            session.is_playing = True
            
            # Playback completion event
            playback_done = asyncio.Event()
            playback_error: Optional[Exception] = None
            
            def after_playing(error):
                nonlocal playback_error
                if error:
                    playback_error = error
                    log.error(f"Ses çalma hatası: {error}")
                else:
                    log.debug("Ses başarıyla çalındı")
                playback_done.set()
            
            # Ses çal
            session.voice_client.play(audio_source, after=after_playing)
            
            if wait_for_completion:
                # Tamamlanmasını bekle (max 30 saniye)
                try:
                    await asyncio.wait_for(playback_done.wait(), timeout=30.0)
                except asyncio.TimeoutError:
                    log.warning("Ses çalma timeout")
                    session.voice_client.stop()
            
            return playback_error is None
            
        except Exception as e:
            log.error(f"Ses çalma exception: {e}", exc_info=True)
            return False
            
        finally:
            self._active_playbacks.discard(key)
            session.is_playing = False
    
    async def disconnect(self, guild_id: int, channel_id: int, force: bool = True):
        """Belirtilen kanaldan bağlantıyı kes"""
        key = (guild_id, channel_id)
        session = self._sessions.pop(key, None)
        
        if session:
            try:
                if session.voice_client.is_connected():
                    await session.voice_client.disconnect(force=force)
                log.info(f"Ses kanalından ayrıldı: guild={guild_id}, channel={channel_id}")
            except Exception as e:
                log.error(f"Disconnect hatası: {e}")
        
        self._active_playbacks.discard(key)
    
    async def disconnect_guild(self, guild_id: int):
        """Bir sunucudaki tüm bağlantıları kes"""
        sessions = self.get_guild_sessions(guild_id)
        
        for session in sessions:
            await self.disconnect(session.guild_id, session.channel_id)
    
    async def cleanup_all(self):
        """Tüm bağlantıları temizle"""
        log.info("Tüm voice bağlantıları temizleniyor...")
        
        # Cleanup task'ı durdur
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Tüm sessionları kapat
        keys = list(self._sessions.keys())
        for key in keys:
            try:
                await self.disconnect(key[0], key[1])
            except Exception as e:
                log.error(f"Cleanup hatası: {e}")
        
        self._sessions.clear()
        self._active_playbacks.clear()
        log.info("Voice cleanup tamamlandı")
    
    @property
    def total_sessions(self) -> int:
        """Toplam aktif session sayısı"""
        return len(self._sessions)
    
    @property
    def total_playing(self) -> int:
        """Toplam ses çalan session sayısı"""
        return len(self._active_playbacks)
