#!/usr/bin/env python3
"""
SesAdam Discord Bot - Global Multi-Channel Version
Kullanıcılar ses kanalına girdiğinde otomatik ses çalar.
Birden fazla sunucu ve kanalda eşzamanlı çalışır.
"""

import os
import sys
import signal
import asyncio
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from logger_setup import setup_logging, get_logger
from voice_pool import VoicePool
from config import BOT_CONFIG, VOICE_CONFIG, DOWNLOADS_DIR, get_ffmpeg_path

# Environment variables yükle
load_dotenv()

# Logging yapılandır
bot_logger = setup_logging(
    log_file=BOT_CONFIG.get('log_file', 'bot.log'),
    log_level=BOT_CONFIG.get('log_level', 'INFO'),
)
log = get_logger('bot.main')


class SesAdamBot(commands.Bot):
    """
    Ana bot sınıfı.
    Çoklu ses kanalı desteği ve gelişmiş event handling.
    """
    
    def __init__(self):
        # Intents yapılandır
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix=BOT_CONFIG.get('command_prefix', '/'),
            intents=intents,
            heartbeat_timeout=BOT_CONFIG.get('heartbeat_timeout', 60.0),
            guild_ready_timeout=BOT_CONFIG.get('guild_ready_timeout', 5.0),
            reconnect=True,
        )
        
        # Voice Pool - çoklu kanal yönetimi
        self.voice_pool: Optional[VoicePool] = None
        
        # Graceful shutdown flag
        self._shutdown_event = asyncio.Event()
    
    async def setup_hook(self):
        """Bot başlarken çalışır - cog'ları yükle ve sync et"""
        log.info("Bot setup başlıyor...")
        
        # Voice Pool oluştur
        self.voice_pool = VoicePool(
            bot=self,
            max_sessions_per_guild=VOICE_CONFIG.get('max_sessions_per_guild', 5),
            session_timeout=VOICE_CONFIG.get('session_timeout', 60.0),
            connection_timeout=VOICE_CONFIG.get('connection_timeout', 15.0),
        )
        self.voice_pool.start_cleanup_task()
        
        # Downloads klasörünü oluştur
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        
        # FFmpeg kontrolü
        try:
            ffmpeg_path = get_ffmpeg_path()
            log.info(f"FFmpeg bulundu: {ffmpeg_path}")
        except FileNotFoundError as e:
            log.error(f"FFmpeg bulunamadı: {e}")
        
        # Commands cog'unu yükle
        try:
            await self.load_extension('commands.audio')
            log.info("Audio commands yüklendi")
        except Exception as e:
            log.error(f"Commands yüklenemedi: {e}", exc_info=True)
        
        log.info("Bot setup tamamlandı")
    
    async def on_ready(self):
        """Bot Discord'a bağlandığında çalışır"""
        if self.user:
            log.info(f"Bot olarak giriş yapıldı: {self.user} (ID: {self.user.id})")
        
        # Slash komutlarını senkronize et
        try:
            synced = await self.tree.sync()
            log.info(f"{len(synced)} slash komutu senkronize edildi")
        except Exception as e:
            log.error(f"Komut senkronizasyonu başarısız: {e}")
        
        # İstatistikler
        log.info(f"Toplam sunucu sayısı: {len(self.guilds)}")
        log.info(f"Bot hazır ve çalışıyor!")
        
        # Status ayarla
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/sesyukle"
            )
        )
    
    async def on_disconnect(self):
        """Bot bağlantı kesintisinde çalışır"""
        log.warning("Bot Discord'dan bağlantısı kesildi")
    
    async def on_resumed(self):
        """Bot yeniden bağlandığında çalışır"""
        log.info("Bot bağlantısı yeniden kuruldu")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Bot yeni sunucuya eklendiğinde çalışır"""
        log.info(f"Yeni sunucuya katıldı: {guild.name} (ID: {guild.id})")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Bot sunucudan ayrıldığında çalışır"""
        log.info(f"Sunucudan ayrıldı: {guild.name} (ID: {guild.id})")
        
        # Sunucudaki tüm voice bağlantılarını temizle
        if self.voice_pool:
            await self.voice_pool.disconnect_guild(guild.id)
    
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """
        Kullanıcı ses kanalına girdiğinde/çıktığında çalışır.
        Ana işlev: Kullanıcı kanala girdiğinde sesini çal.
        """
        # Bot'un kendi voice state değişikliklerini logla
        if self.user and member.id == self.user.id:
            log.debug(
                f"Bot voice state değişti: "
                f"{before.channel.name if before.channel else 'None'} -> "
                f"{after.channel.name if after.channel else 'None'}"
            )
            return
        
        # Bot'ları atla
        if member.bot:
            return
        
        # Voice pool kontrolü
        if not self.voice_pool:
            log.warning("Voice pool henüz hazır değil")
            return
        
        # Kullanıcı ses kanalından ayrıldı
        if after.channel is None:
            log.debug(f"Kullanıcı ses kanalından ayrıldı: {member.display_name}")
            return
        
        # Kullanıcı ses kanalına katıldı veya kanal değiştirdi
        if before.channel is None or before.channel.id != after.channel.id:
            await self._handle_user_join(member, after.channel)
    
    async def _handle_user_join(self, member: discord.Member, channel: discord.VoiceChannel):
        """Kullanıcı ses kanalına katıldığında sesi çal"""
        guild_id = member.guild.id
        channel_id = channel.id
        user_id = member.id
        
        # Kullanıcının ses dosyası var mı kontrol et
        audio_file = f'{DOWNLOADS_DIR}/{user_id}.webm'
        
        if not os.path.isfile(audio_file):
            log.debug(f"Ses dosyası bulunamadı: user={user_id}")
            return
        
        log.info(
            f"Kullanıcı ses kanalına katıldı, ses çalınacak",
            extra={
                'user_id': user_id,
                'guild_id': guild_id,
                'channel_id': channel_id,
                'user_name': member.display_name,
                'channel_name': channel.name
            }
        )
        
        try:
            # FFmpeg kontrolü
            ffmpeg_path = get_ffmpeg_path()
            
            # Voice kanalına bağlan
            session = await self.voice_pool.connect(channel, user_id)
            
            if not session:
                log.error(f"Ses kanalına bağlanılamadı: {channel.name}")
                return
            
            # Ses kaynağı oluştur
            audio_source = discord.FFmpegOpusAudio(
                audio_file,
                executable=ffmpeg_path,
                options=VOICE_CONFIG.get('ffmpeg_options', '-vn -b:a 96k')
            )
            
            # Ses çal
            success = await self.voice_pool.play_audio(
                guild_id=guild_id,
                channel_id=channel_id,
                audio_source=audio_source,
                wait_for_completion=True
            )
            
            if success:
                log.info(f"Ses başarıyla çalındı: user={member.display_name}")
            else:
                log.warning(f"Ses çalınamadı: user={member.display_name}")
            
            # Ses çaldıktan sonra bağlantıyı kes
            await self.voice_pool.disconnect(guild_id, channel_id)
            
        except FileNotFoundError as e:
            log.error(f"FFmpeg hatası: {e}")
        except Exception as e:
            log.error(f"Ses çalma hatası: {e}", exc_info=True)
            # Hata durumunda bağlantıyı temizle
            if self.voice_pool:
                await self.voice_pool.disconnect(guild_id, channel_id)
    
    async def on_error(self, event: str, *args, **kwargs):
        """Genel hata yakalama"""
        log.error(f"Event hatası - {event}", exc_info=True)
    
    async def close(self):
        """Bot kapatılırken çalışır"""
        log.info("Bot kapatılıyor...")
        
        # Voice pool'u temizle
        if self.voice_pool:
            await self.voice_pool.cleanup_all()
        
        await super().close()
        log.info("Bot kapatıldı")


# Graceful shutdown
async def graceful_shutdown(bot: SesAdamBot, signal_name: str):
    """Graceful shutdown handler"""
    log.info(f"Signal {signal_name} alındı, bot kapatılıyor...")
    await bot.close()


def setup_signal_handlers(bot: SesAdamBot, loop: asyncio.AbstractEventLoop):
    """Signal handler'ları kur"""
    for sig_name in ('SIGINT', 'SIGTERM'):
        sig = getattr(signal, sig_name, None)
        if sig:
            loop.add_signal_handler(
                sig,
                lambda s=sig_name: asyncio.create_task(graceful_shutdown(bot, s))
            )


def main():
    """Ana başlatma fonksiyonu"""
    # Token kontrolü
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token or token == 'YOUR_DISCORD_BOT_TOKEN_HERE':
        log.error("DISCORD_BOT_TOKEN ayarlanmamış!")
        log.error("Lütfen .env dosyasına geçerli bir token girin.")
        sys.exit(1)
    
    log.info("Bot başlatılıyor...")
    
    # Bot instance oluştur
    bot = SesAdamBot()
    
    try:
        # Event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Signal handlers
        try:
            setup_signal_handlers(bot, loop)
        except NotImplementedError:
            # Windows'ta signal handler çalışmaz
            pass
        
        # Bot'u çalıştır
        loop.run_until_complete(bot.start(token))
        
    except discord.LoginFailure:
        log.error("Geçersiz bot token!")
        sys.exit(1)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt alındı")
    except Exception as e:
        log.error(f"Beklenmeyen hata: {e}", exc_info=True)
        sys.exit(1)
    finally:
        try:
            loop.run_until_complete(bot.close())
            loop.close()
        except:
            pass


if __name__ == '__main__':
    main()
