import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import asyncio
import subprocess
import shutil

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı.')
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"Komutlar senkronize edilirken hata oluştu: {e}")

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

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

            # Trim the audio with specified times
            trim_audio(temp_output, final_output, start_time=start, end_time=end) # type: ignore

            # Remove temporary file
            os.remove(temp_output)

            await interaction.followup.send(f"Ses başarıyla yüklendi ve {start}-{end} arası kısaltıldı.")

        except youtube_dl.utils.DownloadError as e:
            await interaction.followup.send(f"İndirme hatası: {e}")
        except Exception as e:
            await interaction.followup.send(f"Beklenmeyen bir hata oluştu: {e}")
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
    if member.bot:
        return

    if after.channel is None:
        return

    # Değişiklik: Kullanıcı kanalına giriş yaparken veya kanal değiştirirken her zaman aynı dosyayı kullan
    if before.channel is None or before.channel != after.channel:
        file_path = f'downloads/{member.id}.webm'
    else:
        return

    if not os.path.isfile(file_path):
        return

    voice_channel = after.channel
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
        if voice_client is None:
            voice_client = await voice_channel.connect()

        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            try:
                text_channel = voice_channel.guild.text_channels[0]
                await text_channel.send(f"{member.mention} FFmpeg bulunamadı. Lütfen sistem yöneticinizle iletişime geçin.")
            except:
                print("FFmpeg bulunamadı ve kullanıcıya bilgi verilemedi.")
            return

        # Değişiklik: FFmpegPCMAudio yerine FFmpegOpusAudio kullanıldı
        voice_client.play(discord.FFmpegOpusAudio(file_path, executable=ffmpeg_path),  # type: ignore
                            after=lambda e: print('Ses çalındı' if e is None else f'Hata: {e}'))

        while voice_client.is_playing():  # type: ignore
            await asyncio.sleep(1)

        await voice_client.disconnect()  # type: ignore
            
    except Exception as e:
        print(f"Ses çalma hatası: {e}")
        try:
            if voice_client and voice_client.is_connected():  # type: ignore
                await voice_client.disconnect()  # type: ignore
        except:
            pass

bot.run('MTI0NzQzNzAyNDY2Nzg5Nzg1Nw.GeXMbZ.yYE7kDEds7wghMPgpvvcbwlhpvhPXp0sMD5rnw')
