import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import asyncio
import subprocess
import shutil
import logging
import signal
import sys
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from voice_manager import VoiceManager

# Load environment variables from .env file
load_dotenv()

# Logging yapılandırması - Info seviyesinde dengeli log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Enable voice-related debug logging only
logging.getLogger("discord.voice_state").setLevel(logging.DEBUG)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Bot yapılandırması - reconnection için gerekli ayarlar
bot = commands.Bot(
    command_prefix='/',
    intents=intents,
    heartbeat_timeout=60.0,  # Heartbeat timeout
    guild_ready_timeout=5.0,  # Guild ready timeout
    reconnect=True  # Otomatik reconnection
)

# Voice manager instance - only for cleanup
voice_manager = VoiceManager(bot)

# Session data for reconnection
session_data: Dict[int, Any] = {}

# Track active playback to prevent multiple simultaneous connections
active_playback: Dict[int, bool] = {}

@bot.event
async def on_ready():
    if bot.user:
        logger.info(f'{bot.user} olarak giriş yapıldı. Bot ID: {bot.user.id}')
    else:
        logger.warning('Bot user bilgisi alınamadı')
    try:
        synced = await bot.tree.sync()
        logger.info(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        logger.error(f"Komutlar senkronize edilirken hata oluştu: {e}")

@bot.event
async def on_disconnect():
    """Bot bağlantısı kesildiğinde çağrılır"""
    logger.warning("Bot Discord'dan bağlantısı kesildi!")
    # Voice manager üzerinden tüm bağlantıları temizle
    await voice_manager.cleanup_all()

@bot.event
async def on_resumed():
    """Bot bağlantısı yeniden kurulduğunda çağrılır"""
    logger.info("Bot bağlantısı yeniden kuruldu (session devam ediyor)!")
    # Session data ile voice bağlantılarını yeniden kurmaya çalış
    for guild_id, data in session_data.items():
        try:
            guild = bot.get_guild(guild_id)
            if guild and data.get('channel_id'):
                channel = guild.get_channel(data['channel_id'])
                if channel and isinstance(channel, discord.VoiceChannel):
                    # VoiceManager ile güvenli bağlantı
                    voice_client = await voice_manager.connect_with_backoff(channel)
                    logger.info(f"Voice bağlantısı yeniden kuruldu: {guild.name}")
        except Exception as e:
            logger.error(f"Voice bağlantısı yeniden kurulurken hata (Guild {guild_id}): {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Genel hata yakalama"""
    logger.error(f"Event hatası - {event}: args={args}, kwargs={kwargs}")

@bot.event
async def on_voice_state_error(member, error):
    """Voice state hatası yakalama"""
    logger.error(f"Voice state hatası - Üye: {member}, Hata: {error}")

@bot.event
async def on_gateway_error(error):
    """Gateway hatası yakalama"""
    logger.error(f"Gateway hatası: {error}")
    # Otomatik reconnection için kısa bekleme
    await asyncio.sleep(5)

async def download_file(url, path):
    async with bot.http_session.get(url) as response: # type: ignore
        with open(path, 'wb') as f:
            f.write(await response.read())

# FFmpeg yolunu bulan yardımcı fonksiyon ekleyelim
def get_ffmpeg_path():
    # Önce PATH'de ffmpeg'i ara
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # Yaygın Linux konumlarını kontrol et
    common_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/opt/ffmpeg/bin/ffmpeg'
    ]
    
    for path in common_paths:
        if os.path.isfile(path):
            return path
            
    return None

def trim_audio(input_path, output_path, start_time=0, end_time=15):
    duration = min(end_time - start_time, 15)  # Maximum 15 seconds
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        raise Exception("FFmpeg bulunamadı. Lütfen FFmpeg'i yükleyin.")
        
    subprocess.run([
        ffmpeg_path, '-y', '-i', input_path, 
        '-ss', str(start_time),  # Start time
        '-t', str(duration),     # Duration
        '-c:a', 'libopus', '-b:a', '96k', '-vbr', 'on', 
        output_path
    ])

# Desteklenen dosya formatlarını kontrol eden fonksiyon
def is_supported_format(filename):
    supported_extensions = ['.mp3', '.webm', '.mp4', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.wma']
    return any(filename.lower().endswith(ext) for ext in supported_extensions)

@bot.tree.command(name="sesyukle", description="Downloads audio from YouTube")
async def sesyukle(interaction: discord.Interaction, url: str, start_time: float = None, end_time: float = None): # type: ignore
    await interaction.response.defer()  # İşlem başladığını belirtiyoruz
    if url:
        try:
            # Varsayılan değerleri ayarla
            start = 0 if start_time is None else float(start_time)
            end = 15 if end_time is None else float(end_time)

            # Ensure the downloads directory exists
            if not os.path.exists('downloads'):
                os.makedirs('downloads')

            temp_output = f'downloads/{interaction.user.id}_temp.webm'
            final_output = f'downloads/{interaction.user.id}.webm'

            # Eğer dosya varsa sil
            if os.path.exists(final_output):
                os.remove(final_output)

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_output,
                'noplaylist': True,
                'max_filesize': 10000000,  # 10 MB
                'no_warnings': True,
                'quiet': True,
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl: # pyright: ignore[reportArgumentType]
                ydl.extract_info(url, download=True)

            # Trim the audio with specified times
            trim_audio(temp_output, final_output, start_time=start, end_time=end) # type: ignore

            # Remove temporary file
            os.remove(temp_output)

            await interaction.followup.send(f"Ses başarıyla yüklendi ve {start}-{end} arası kısaltıldı.")

        except Exception as e:
            await interaction.followup.send(f"İndirme hatası: {e}")
    else:
        await interaction.followup.send("Bir YouTube linki ya da ses dosyası ekleyin.")

@bot.tree.command(name="dosyaekle", description="Ses dosyası ekleyin (mp3, webm, mp4, m4a, wav, flac, ogg, aac, wma).")
async def dosyaekle(interaction: discord.Interaction, attachment: discord.Attachment, start_time: float = None, end_time: float = None): # type: ignore
    await interaction.response.defer()  # İşlem başladığını belirtiyoruz
    if not attachment:
        await interaction.followup.send("Lütfen bir dosya ekleyin.")
        return

    # Dosya formatını kontrol et
    if not is_supported_format(attachment.filename):
        supported_formats = "mp3, webm, mp4, m4a, wav, flac, ogg, aac, wma"
        await interaction.followup.send(f"Desteklenmeyen dosya formatı. Desteklenen formatlar: {supported_formats}")
        return

    # Varsayılan değerleri ayarla
    start = 0 if start_time is None else float(start_time)
    end = 15 if end_time is None else float(end_time)

    try:
        # Ensure the downloads directory exists
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        # Geçici dosya yolları
        temp_input = f'downloads/{interaction.user.id}_temp_input{os.path.splitext(attachment.filename)[1]}'
        final_output = f'downloads/{interaction.user.id}.webm'
        
        # Eğer final dosya varsa sil
        if os.path.exists(final_output):
            os.remove(final_output)
        
        # Dosyayı kaydet
        await attachment.save(temp_input) # type: ignore
        
        # Ses dosyasını kısalt ve webm formatına dönüştür
        trim_audio(temp_input, final_output, start_time=start, end_time=end) # type: ignore
        
        # Geçici dosyayı sil
        os.remove(temp_input)
        
        await interaction.followup.send(f"{attachment.filename} başarıyla yüklendi ve {start}-{end} arası webm formatına dönüştürüldü.")
        
    except Exception as e:
        await interaction.followup.send(f"Dosya işlenirken hata oluştu: {e}")

@bot.tree.command(name="seskaldir", description="Yüklenmiş ses dosyanızı kaldırır.")
async def seskaldir(interaction: discord.Interaction): # type: ignore
    await interaction.response.defer()
    
    file_path = f'downloads/{interaction.user.id}.webm'
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            await interaction.followup.send("Ses dosyanız başarıyla kaldırıldı.")
        except Exception as e:
            await interaction.followup.send(f"Dosya kaldırılırken hata oluştu: {e}")
    else:
        await interaction.followup.send("Kaldırılacak ses dosyanız bulunamadı.")

@bot.tree.command(name="seslistesi", description="Sunucudaki tüm kullanıcıların ses dosyalarını listeler.")
async def seslistesi(interaction: discord.Interaction): # type: ignore
    await interaction.response.defer()
    
    if not os.path.exists('downloads'):
        await interaction.followup.send("Henüz hiç ses dosyası yüklenmemiş.")
        return
    
    files = os.listdir('downloads')
    webm_files = [f for f in files if f.endswith('.webm')]
    
    if not webm_files:
        await interaction.followup.send("Henüz hiç ses dosyası yüklenmemiş.")
        return
    
    # Kullanıcı ID'lerini al ve kullanıcı bilgilerini bul
    user_files = []
    for filename in webm_files:
        user_id = filename.replace('.webm', '')
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.display_name
        except:
            username = f"Bilinmeyen Kullanıcı ({user_id})"
        
        file_path = os.path.join('downloads', filename)
        file_size = os.path.getsize(file_path)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        user_files.append(f"• {username}: {file_size_mb} MB")
    
    message = "**Yüklenmiş Ses Dosyaları:**\n" + "\n".join(user_files)
    
    # Discord mesaj sınırını aşmamak için böl
    if len(message) > 2000:
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(chunk)
    else:
        await interaction.followup.send(message)

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes - only play audio, don't manage connections"""

    # Log bot's own voice state changes for debugging
    if bot.user and member.id == bot.user.id:
        logger.info("Bot voice state changed: before=%s after=%s",
                   before.channel.name if before and before.channel else None,
                   after.channel.name if after and after.channel else None)

        # If bot was unexpectedly disconnected, we might want to reconnect
        if before and before.channel and (not after or not after.channel):
            logger.warning("Bot was disconnected from voice channel unexpectedly")
        return

    if member.bot:
        return

    # User left voice channel - cleanup if needed
    if after.channel is None and before.channel is not None:
        guild_id = member.guild.id
        logger.info(f"User {member.display_name} left voice channel in {member.guild.name}")
        return

    if after.channel is None:
        return

    # Only process when user joins or switches channels
    if before.channel is None or before.channel != after.channel:
        file_path = f'downloads/{member.id}.webm'

        if not os.path.isfile(file_path):
            logger.debug(f"No audio file found for user {member.id}")
            return

        voice_channel = after.channel
        guild_id = member.guild.id

        # Check if there's already active playback for this guild
        if active_playback.get(guild_id, False):
            logger.debug(f"Active playback already in progress for guild {guild_id}, skipping")
            return

        try:
            # Set active playback flag
            active_playback[guild_id] = True

            # Get existing voice client for this guild
            voice_client = voice_channel.guild.voice_client

            if not voice_client or not voice_client.is_connected():
                logger.info(f"Connecting to voice channel for user {member.display_name}")
                try:
                    voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
                    logger.info(f"Successfully connected to voice channel: {voice_channel.name}")
                except discord.errors.ConnectionClosed as e:
                    logger.error(f"Voice connection failed with code {e.code}: {e.reason}")
                    active_playback[guild_id] = False
                    return
                except Exception as e:
                    logger.error(f"Voice connection failed: {e}")
                    active_playback[guild_id] = False
                    return

            # Update session data
            session_data[guild_id] = {
                'channel_id': voice_channel.id,
                'user_id': member.id,
                'timestamp': asyncio.get_event_loop().time()
            }

            # Check FFmpeg
            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                try:
                    text_channel = voice_channel.guild.text_channels[0]
                    await text_channel.send(f"{member.mention} FFmpeg bulunamadı. Lütfen sistem yöneticinizle iletişime geçin.")
                except Exception as e:
                    logger.error(f"Could not notify user about FFmpeg: {e}")
                return

            # Play audio
            try:
                audio_source = discord.FFmpegOpusAudio(
                    file_path,
                    executable=ffmpeg_path,
                    options='-vn -b:a 96k'
                )

                def after_playing(error):
                    if error:
                        logger.error(f"Audio playback error: {error}")
                    else:
                        logger.info("Audio played successfully")

                voice_client.play(audio_source, after=after_playing)

                # Wait for playback to complete (max 30 seconds)
                timeout = 30
                waited = 0
                while voice_client.is_playing() and waited < timeout:
                    await asyncio.sleep(1)
                    waited += 1

                if waited >= timeout:
                    logger.warning("Audio playback timed out")
                    voice_client.stop()

                # Disconnect after playback completes or times out
                try:
                    if voice_client and voice_client.is_connected():
                        await voice_client.disconnect(force=True)
                        logger.info("Disconnected from voice channel after playback")
                except Exception as e:
                    logger.error(f"Error disconnecting after playback: {e}")
                finally:
                    # Clear active playback flag
                    active_playback[guild_id] = False

            except Exception as e:
                logger.error(f"Audio playback failed: {e}")

        except Exception as e:
            logger.error(f"Voice state update error: {e}")
            # Clean up on any error
            session_data.pop(guild_id, None)
            active_playback[guild_id] = False

# Graceful shutdown için signal handler
import signal
import sys

async def graceful_shutdown():
    """Asenkron graceful shutdown"""
    logger.info("Graceful shutdown başlatılıyor...")

    try:
        # VoiceManager üzerinden tüm bağlantıları temizle
        await voice_manager.cleanup_all()

        # Clear active playback flags
        active_playback.clear()

        # Bot'u kapat
        await bot.close()
        logger.info("Bot başarıyla kapatıldı")

    except Exception as e:
        logger.error(f"Shutdown sırasında hata: {e}")

def signal_handler(signum, frame):
    """Signal handler - asenkron shutdown başlatır"""
    logger.info(f"Signal {signum} alındı. Graceful shutdown başlatılıyor...")

    # Event loop'ta graceful shutdown çalıştır
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Running loop'ta task oluştur
            loop.create_task(graceful_shutdown())
        else:
            # Loop çalışmıyorsa direkt çalıştır
            loop.run_until_complete(graceful_shutdown())
    except Exception as e:
        logger.error(f"Signal handler hatası: {e}")
        # Fallback - force exit
        sys.exit(1)

# Signal handler'ları kaydet
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Bot token'ı .env dosyasından al (güvenlik için)
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN or TOKEN == 'your_bot_token_here':
    logger.error("DISCORD_BOT_TOKEN .env dosyasında ayarlanmamış veya varsayılan değerde!")
    logger.error("Lütfen .env dosyasında DISCORD_BOT_TOKEN değerini gerçek bot token'ınızla değiştirin.")
    sys.exit(1)

logger.info("Bot token başarıyla yüklendi")

try:
    bot.run(TOKEN)
except discord.LoginFailure:
    logger.error("Bot token geçersiz!")
    sys.exit(1)
except Exception as e:
    logger.error(f"Bot başlatılırken beklenmeyen hata: {e}")
    sys.exit(1)
