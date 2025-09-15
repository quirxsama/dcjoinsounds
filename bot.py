import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import asyncio
import subprocess
import json
import random

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
async def uploadlink(interaction: discord.Interaction, url: str, filename: str):
    await interaction.response.defer()
    if url:
        try:
            user_dir = f'downloads/{interaction.user.id}'
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)

            if len(os.listdir(user_dir)) >= 5:
                await interaction.followup.send("You have reached the maximum number of sounds (5).")
                return

            if not filename.endswith('.webm'):
                filename += '.webm'

            temp_output = f'{user_dir}/{filename}_temp.webm'
            final_output = f'{user_dir}/{filename}'

            if os.path.exists(final_output):
                 await interaction.followup.send("A sound with this name already exists.")
                 return

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_output,
                'noplaylist': True,
                'max_filesize': 10000000,  # 10 MB
                'no_warnings': True,
                'quiet': True,
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            trim_audio(temp_output, final_output, duration=15)

            os.remove(temp_output)

            await interaction.followup.send(f"Audio `{filename}` successfully uploaded and trimmed to 15 seconds.")

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

    user_dir = f'downloads/{interaction.user.id}'
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    if len(os.listdir(user_dir)) >= 5:
        await interaction.followup.send("You have reached the maximum number of sounds (5).")
        return

    filename, file_extension = os.path.splitext(attachment.filename)
    save_path_webm = f'{user_dir}/{filename}.webm'

    if os.path.exists(save_path_webm):
        await interaction.followup.send("A sound with this name already exists.")
        return

    if file_extension == '.mp3':
        save_path_mp3 = f'{user_dir}/{attachment.filename}'
        await attachment.save(save_path_mp3)
        trim_audio(save_path_mp3, save_path_webm, duration=15)
        os.remove(save_path_mp3)
        await interaction.followup.send(f"MP3 file `{filename}.webm` successfully uploaded and converted to webm format.")
    elif file_extension == '.webm':
        temp_save_path = f'{user_dir}/{attachment.filename}_temp.webm'
        await attachment.save(temp_save_path)
        trim_audio(temp_save_path, save_path_webm, duration=15)
        os.remove(temp_save_path)
        await interaction.followup.send(f"WEBM file `{filename}.webm` successfully uploaded and trimmed to 15 seconds.")
    else:
        await interaction.followup.send("Please upload only mp3 or webm files.")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if before.channel is None and after.channel is not None:
        user_dir = f'downloads/{member.id}'
        if not os.path.exists(user_dir) or not os.listdir(user_dir):
            return

        sound_files = [f for f in os.listdir(user_dir) if f.endswith('.webm')]
        if not sound_files:
            return

        file_path = os.path.join(user_dir, random.choice(sound_files))

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

@bot.tree.command(name="my_sounds", description="Lists all your uploaded sounds.")
async def my_sounds(interaction: discord.Interaction):
    user_dir = f'downloads/{interaction.user.id}'
    if not os.path.exists(user_dir) or not os.listdir(user_dir):
        await interaction.response.send_message("You have no uploaded sounds.")
        return

    sound_files = [f for f in os.listdir(user_dir) if f.endswith('.webm')]
    if not sound_files:
        await interaction.response.send_message("You have no uploaded sounds.")
        return

    embed = discord.Embed(
        title="Your Sounds",
        description="Here are all your uploaded sounds:",
        color=discord.Color.green()
    )
    for sound in sound_files:
        embed.add_field(name=sound, value="", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="delete_sound", description="Deletes a specific sound.")
async def delete_sound(interaction: discord.Interaction, filename: str):
    user_dir = f'downloads/{interaction.user.id}'
    if not os.path.exists(user_dir):
        await interaction.response.send_message("You have no uploaded sounds.")
        return

    if not filename.endswith('.webm'):
        filename += '.webm'

    file_path = os.path.join(user_dir, filename)

    if not os.path.exists(file_path):
        await interaction.response.send_message(f"Sound `{filename}` not found.")
        return

    os.remove(file_path)
    await interaction.response.send_message(f"Sound `{filename}` successfully deleted.")

@bot.tree.command(name="help", description="Shows the help message.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(name="</uploadlink:123>", value="Uploads audio from a YouTube link. Provide a URL and a filename.", inline=False)
    embed.add_field(name="</uploadfile:123>", value="Upload an audio file (mp3 or webm).", inline=False)
    embed.add_field(name="</my_sounds:123>", value="Lists all your uploaded sounds.", inline=False)
    embed.add_field(name="</delete_sound:123>", value="Deletes a specific sound.", inline=False)
    await interaction.response.send_message(embed=embed)

with open('config.json', 'r') as f:
    config = json.load(f)

bot.run(config['DISCORD_BOT_TOKEN'])
