# Discord Join Sounds Bot

This Discord bot allows users to upload audio files or provide YouTube links to extract and play audio in voice channels. The audio can be in MP3 or WEBM format and will be trimmed to 15 seconds.

## Features

- **Upload audio from a YouTube link**: Use the `/uploadlink` command to download and trim audio from YouTube.
- **Upload audio files**: Use the `/uploadfile` command to upload MP3 or WEBM files, which will be converted or trimmed as necessary.

## Installation

To set up the bot, follow these steps:

### Prerequisites

1. **Python 3.8+**: Make sure you have Python 3.8 or higher installed.

2. **FFmpeg**: Install FFmpeg for audio processing. Follow the instructions based on your operating system:

   - **Ubuntu/Debian**:
     ```bash
     sudo apt update
     sudo apt install ffmpeg
     ```

   - **Windows**:
     1. Download FFmpeg from [the official website](https://ffmpeg.org/download.html).
     2. Extract the files and add the path to `ffmpeg.exe` to your system PATH.

   - **macOS**:
     ```bash
     brew install ffmpeg
     ```

### Setup

1. **Clone the repository**:
  ```bash
   git clone https://github.com/quirxsama/dcjoinsounds.git
   cd dcjoinsounds
```
2. **Create a virtual environment** *(optional but recommended)*:
  ```bash
  python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
  ```
3. **Install the required Python packages**:
  ```bash
pip install -r requirements.txt
```
4. **Paste your bot token to bot.py file**
   Paste your bot token to field in the bot.py (YOUR_DISCORD_BOT_TOKEN)
6. **Run the bot**:
```bash
python bot.py
 ```

### Commands


    /uploadlink [url]: Upload audio from a YouTube link. The audio will be trimmed to 15 seconds.

    /uploadfile [file]: Upload an MP3 or WEBM file. MP3 files will be converted to WEBM format and both types will be trimmed to 15 seconds.

