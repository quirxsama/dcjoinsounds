import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import asyncio
import subprocess

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}.')
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash commands synced.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

def trim_audio(input_path, output_path, duration=15):
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', input_path, '-t', str(duration), '-c:a', 'libopus', '-b:a', '96k', '-vbr', 'on', output_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

@bot.tree.command(name="uploadlink", description="Uploads audio from a YouTube link.")
async def uploadlink(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    if url:
        try:
            if not os.path.exists('downloads'):
                os.makedirs('downloads')

            temp_output = f'downloads/{interaction.user.id}_temp.webm'
            final_output = f'downloads/{interaction.user.id}.webm'

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

            trim_audio(temp_output, final_output, duration=15)

            os.remove(temp_output)

            await interaction.followup.send("Audio successfully uploaded and trimmed to 15 seconds.")

        except youtube_dl.utils.DownloadError as e:
            await interaction.followup.send(f"Download error: {e}")
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {e}")
    else:
        await interaction.followup.send("Please provide a YouTube link.")

@bot.tree.command(name="uploadfile", description="Upload an audio file (mp3 or webm).")
async def uploadfile(interaction: discord.Interaction, attachment: discord.Attachment):
    await interaction.response.defer()
    if not attachment:
        await interaction.followup.send("Please upload a file.")
        return

    if attachment.filename.endswith('.mp3'):
        save_path_mp3 = f'downloads/{interaction.user.id}.mp3'
        save_path_webm = f'downloads/{interaction.user.id}.webm'
        
        if os.path.exists(save_path_webm):
            os.remove(save_path_webm)
        
        await attachment.save(save_path_mp3)
        trim_audio(save_path_mp3, save_path_webm, duration=15)
        
        os.remove(save_path_mp3)
        await interaction.followup.send("MP3 file successfully uploaded and converted to webm format.")
    elif attachment.filename.endswith('.webm'):
        temp_save_path = f'downloads/{interaction.user.id}_temp.webm'
        final_save_path = f'downloads/{interaction.user.id}.webm'
        
        if os.path.exists(final_save_path):
            os.remove(final_save_path)
        
        await attachment.save(temp_save_path)
        trim_audio(temp_save_path, final_save_path, duration=15)
        
        os.remove(temp_save_path)
        await interaction.followup.send("WEBM file successfully uploaded and trimmed to 15 seconds.")
    else:
        await interaction.followup.send("Please upload only mp3 or webm files.")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if before.channel is None and after.channel is not None:
        file_path = f'downloads/{member.id}.webm'
        if not os.path.isfile(file_path):
            return

        voice_channel = after.channel
        try:
            voice_client = await voice_channel.connect()
        except discord.errors.ClientException:
            voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)

        try:
            source = discord.FFmpegOpusAudio(file_path)
            voice_client.play(source, after=lambda e: print(f'Playback finished: {e}' if e else 'Playback finished'))
        except Exception as e:
            print(f"Playback error: {e}")
            await voice_client.disconnect()
            return

        while voice_client.is_playing():
            await asyncio.sleep(1)

        await voice_client.disconnect()

bot.run('YOUR_DISCORD_BOT_TOKEN_HERE')
