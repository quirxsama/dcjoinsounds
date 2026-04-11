"""
Audio Commands - Ses yükleme ve yönetim komutları
"""

import os
import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl

from logger_setup import get_logger
from config import DOWNLOADS_DIR, BOT_CONFIG, get_ffmpeg_path

log = get_logger('bot.command.audio')

# Sabitler
MAX_AUDIO_DURATION = BOT_CONFIG.get('audio_trim_max_seconds', 15)  # saniye
MAX_FILE_SIZE_MB = BOT_CONFIG.get('max_file_size_mb', 10)
SUPPORTED_FORMATS = ['.mp3', '.webm', '.mp4', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.wma']


async def trim_audio(input_path: str, output_path: str, start_time: float = 0, end_time: float = 15):
    """Ses dosyasını kırp ve webm formatına dönüştür (async)"""
    duration = min(end_time - start_time, MAX_AUDIO_DURATION)
    ffmpeg_path = get_ffmpeg_path()
    
    process = await asyncio.create_subprocess_exec(
        ffmpeg_path, '-y', '-i', input_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-c:a', 'libopus', '-b:a', '96k', '-vbr', 'on',
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {stderr.decode()}")


def is_supported_format(filename: str) -> bool:
    """Dosya formatı destekleniyor mu?"""
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_FORMATS)


def ensure_downloads_dir():
    """Downloads klasörünün varlığını garantile"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class AudioCommands(commands.Cog):
    """Ses yükleme ve yönetim komutları"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="sesyukle", description="YouTube'dan ses indir")
    @app_commands.describe(
        url="YouTube video linki",
        start_time="Başlangıç zamanı (saniye)",
        end_time="Bitiş zamanı (saniye, max 15)"
    )
    async def sesyukle(
        self,
        interaction: discord.Interaction,
        url: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ):
        await interaction.response.defer()
        
        log.info(
            f"sesyukle komutu kullanıldı",
            extra={
                'user_id': interaction.user.id,
                'guild_id': interaction.guild_id if interaction.guild else None,
                'user_name': str(interaction.user)
            }
        )
        
        try:
            ensure_downloads_dir()
            
            start = 0 if start_time is None else float(start_time)
            end = MAX_AUDIO_DURATION if end_time is None else float(end_time)
            
            # Süre kontrolü
            if end - start > MAX_AUDIO_DURATION:
                end = start + MAX_AUDIO_DURATION
            
            temp_output = f'{DOWNLOADS_DIR}/{interaction.user.id}_temp.webm'
            final_output = f'{DOWNLOADS_DIR}/{interaction.user.id}.webm'
            
            # Eski dosyayı sil
            if os.path.exists(final_output):
                os.remove(final_output)
            
            # YouTube'dan indir
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_output,
                'noplaylist': True,
                'max_filesize': MAX_FILE_SIZE_MB * 1024 * 1024,
                'no_warnings': True,
                'quiet': True,
                'cookiefile': 'cookies.txt',
            }
            
            await interaction.followup.send("⏳ İndiriliyor...")
            
            def _download():
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
            
            await asyncio.to_thread(_download)
            
            # Sesi kırp
            await trim_audio(temp_output, final_output, start_time=start, end_time=end)
            
            # Geçici dosyayı sil
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
            log.info(f"Ses başarıyla yüklendi: user={interaction.user.id}")
            await interaction.edit_original_response(
                content=f"✅ Ses başarıyla yüklendi! ({start:.1f}s - {end:.1f}s arası)"
            )
            
        except Exception as e:
            log.error(f"sesyukle hatası: {e}", exc_info=True)
            await interaction.followup.send(f"❌ İndirme hatası: {str(e)[:100]}")
    
    @app_commands.command(name="dosyaekle", description="Ses dosyası yükle")
    @app_commands.describe(
        attachment="Ses dosyası (mp3, webm, mp4, m4a, wav, flac, ogg, aac, wma)",
        start_time="Başlangıç zamanı (saniye)",
        end_time="Bitiş zamanı (saniye, max 15)"
    )
    async def dosyaekle(
        self,
        interaction: discord.Interaction,
        attachment: discord.Attachment,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ):
        await interaction.response.defer()
        
        log.info(
            f"dosyaekle komutu kullanıldı",
            extra={
                'user_id': interaction.user.id,
                'guild_id': interaction.guild_id if interaction.guild else None,
                'user_name': str(interaction.user)
            }
        )
        
        # Format kontrolü
        if not is_supported_format(attachment.filename):
            formats = ", ".join(SUPPORTED_FORMATS)
            await interaction.followup.send(f"❌ Desteklenmeyen format. Desteklenen: {formats}")
            return
        
        # Boyut kontrolü
        if attachment.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            await interaction.followup.send(f"❌ Dosya çok büyük. Maksimum: {MAX_FILE_SIZE_MB}MB")
            return
        
        try:
            ensure_downloads_dir()
            
            start = 0 if start_time is None else float(start_time)
            end = MAX_AUDIO_DURATION if end_time is None else float(end_time)
            
            # Dosya uzantısını al
            ext = os.path.splitext(attachment.filename)[1]
            temp_input = f'{DOWNLOADS_DIR}/{interaction.user.id}_temp_input{ext}'
            final_output = f'{DOWNLOADS_DIR}/{interaction.user.id}.webm'
            
            # Eski dosyayı sil
            if os.path.exists(final_output):
                os.remove(final_output)
            
            # Dosyayı kaydet
            await attachment.save(temp_input)
            
            # Sesi kırp ve dönüştür
            await trim_audio(temp_input, final_output, start_time=start, end_time=end)
            
            # Geçici dosyayı sil
            if os.path.exists(temp_input):
                os.remove(temp_input)
            
            log.info(f"Dosya başarıyla yüklendi: user={interaction.user.id}, file={attachment.filename}")
            await interaction.followup.send(
                f"✅ **{attachment.filename}** başarıyla yüklendi! ({start:.1f}s - {end:.1f}s)"
            )
            
        except Exception as e:
            log.error(f"dosyaekle hatası: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Dosya işlenirken hata: {str(e)[:100]}")
    
    @app_commands.command(name="seskaldir", description="Yüklenmiş sesinizi kaldırın")
    async def seskaldir(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        log.info(
            f"seskaldir komutu kullanıldı",
            extra={
                'user_id': interaction.user.id,
                'guild_id': interaction.guild_id if interaction.guild else None
            }
        )
        
        file_path = f'{DOWNLOADS_DIR}/{interaction.user.id}.webm'
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                log.info(f"Ses silindi: user={interaction.user.id}")
                await interaction.followup.send("✅ Ses dosyanız başarıyla kaldırıldı.")
            except Exception as e:
                log.error(f"seskaldir hatası: {e}")
                await interaction.followup.send(f"❌ Dosya kaldırılırken hata: {e}")
        else:
            await interaction.followup.send("⚠️ Kaldırılacak ses dosyanız bulunamadı.")
    
    @app_commands.command(name="seslistesi", description="Sunucudaki tüm sesleri listele")
    async def seslistesi(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        log.info(
            f"seslistesi komutu kullanıldı",
            extra={
                'user_id': interaction.user.id,
                'guild_id': interaction.guild_id if interaction.guild else None
            }
        )
        
        if not os.path.exists(DOWNLOADS_DIR):
            await interaction.followup.send("📭 Henüz hiç ses dosyası yüklenmemiş.")
            return
        
        files = os.listdir(DOWNLOADS_DIR)
        webm_files = [f for f in files if f.endswith('.webm') and not f.endswith('_temp.webm')]
        
        if not webm_files:
            await interaction.followup.send("📭 Henüz hiç ses dosyası yüklenmemiş.")
            return
        
        # Kullanıcı bilgilerini al (cache-first, sonra toplu fetch)
        user_ids = []
        for filename in webm_files:
            user_id_str = filename.replace('.webm', '')
            try:
                user_ids.append(int(user_id_str))
            except ValueError:
                user_ids.append(None)
        
        # Cache'den çözümlenemeyenleri toplu fetch et
        async def resolve_user(uid):
            if uid is None:
                return None
            user = self.bot.get_user(uid)
            if user:
                return user
            try:
                return await self.bot.fetch_user(uid)
            except Exception:
                return None
        
        users = await asyncio.gather(*(resolve_user(uid) for uid in user_ids))
        
        user_files = []
        for filename, uid, user in zip(webm_files, user_ids, users):
            username = user.display_name if user else f"Bilinmeyen ({uid})"
            
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            file_size = os.path.getsize(file_path)
            file_size_kb = round(file_size / 1024, 1)
            
            user_files.append(f"• **{username}**: {file_size_kb} KB")
        
        message = "🎵 **Yüklenmiş Sesler:**\n\n" + "\n".join(user_files)
        
        # Uzun mesajları böl
        if len(message) > 2000:
            chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
            for chunk in chunks:
                await interaction.followup.send(chunk)
        else:
            await interaction.followup.send(message)
    
    @app_commands.command(name="botstatus", description="Bot durumunu göster")
    async def botstatus(self, interaction: discord.Interaction):
        """Bot durumunu ve istatistikleri göster"""
        await interaction.response.defer()
        
        # Bot istatistikleri
        guild_count = len(self.bot.guilds)
        user_count = sum(g.member_count or 0 for g in self.bot.guilds)
        
        # Voice pool istatistikleri (varsa)
        voice_pool = getattr(self.bot, 'voice_pool', None)
        if voice_pool:
            total_sessions = voice_pool.total_sessions
            total_playing = voice_pool.total_playing
        else:
            total_sessions = 0
            total_playing = 0
        
        # Ses dosyası sayısı
        audio_count = 0
        if os.path.exists(DOWNLOADS_DIR):
            audio_count = len([f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.webm')])
        
        # FFmpeg durumu
        try:
            get_ffmpeg_path()
            ffmpeg_status = "✅ Yüklü"
        except FileNotFoundError:
            ffmpeg_status = "❌ Bulunamadı"

        embed = discord.Embed(
            title="🤖 Bot Durumu",
            color=discord.Color.green()
        )
        embed.add_field(name="📊 Sunucu Sayısı", value=str(guild_count), inline=True)
        embed.add_field(name="👥 Kullanıcı Sayısı", value=str(user_count), inline=True)
        embed.add_field(name="🎵 Kayıtlı Ses", value=str(audio_count), inline=True)
        embed.add_field(name="🔊 Aktif Bağlantı", value=str(total_sessions), inline=True)
        embed.add_field(name="▶️ Çalan Ses", value=str(total_playing), inline=True)
        embed.add_field(name="🏓 Gecikme", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="📼 FFmpeg", value=ffmpeg_status, inline=True)
        
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Cog'u bot'a ekle"""
    await bot.add_cog(AudioCommands(bot))
    log.info("AudioCommands cog yüklendi")
