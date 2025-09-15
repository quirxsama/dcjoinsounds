# Discord Join Sounds Bot

This Discord bot allows users to upload multiple audio files or provide YouTube links to set as their join sound. When a user joins a voice channel, the bot will randomly play one of their uploaded sounds.

---

## Türkçe

Bu Discord botu, kullanıcıların birden fazla ses dosyası yüklemesine veya YouTube bağlantıları sağlayarak kendi giriş seslerini ayarlamasına olanak tanır. Bir kullanıcı ses kanalına katıldığında, bot kullanıcının yüklediği seslerden rastgele birini çalar.

---

## Features | Özellikler

- **Upload audio from a YouTube link**: Use the `/uploadlink` command to download and trim audio from YouTube.
- **Upload audio files**: Use the `/uploadfile` command to upload MP3 or WEBM files.
- **Multiple Sounds per User**: Each user can upload up to 5 different sounds.
- **Random Playback**: The bot randomly selects one of the user's sounds to play when they join a voice channel.
- **Sound Management**: Users can list their uploaded sounds with `/my_sounds` and delete specific sounds with `/delete_sound`.
- **Help Command**: A `/help` command is available to list all commands.

---

- **YouTube bağlantısından ses yükleme**: YouTube'dan ses indirmek ve kırpmak için `/uploadlink` komutunu kullanın.
- **Ses dosyası yükleme**: MP3 veya WEBM dosyalarını yüklemek için `/uploadfile` komutunu kullanın.
- **Kullanıcı Başına Birden Fazla Ses**: Her kullanıcı en fazla 5 farklı ses yükleyebilir.
- **Rastgele Çalma**: Bot, bir kullanıcı ses kanalına katıldığında kullanıcının seslerinden rastgele birini seçer.
- **Ses Yönetimi**: Kullanıcılar `/my_sounds` ile yükledikleri sesleri listeleyebilir ve `/delete_sound` ile belirli sesleri silebilirler.
- **Yardım Komutu**: Tüm komutları listelemek için bir `/help` komutu mevcuttur.

---

## Installation | Kurulum

### Prerequisites | Ön Gereksinimler

1.  **Python 3.8+**: Make sure you have Python 3.8 or higher installed.
2.  **FFmpeg**: Install FFmpeg for audio processing.

### Setup | Kurulum Adımları

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/quirxsama/dcjoinsounds.git
    cd dcjoinsounds
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure the bot token**:
    - Rename `config.json.example` to `config.json`.
    - Open `config.json` and replace `"YOUR_DISCORD_BOT_TOKEN_HERE"` with your actual Discord bot token.
4.  **Run the bot**:
    ```bash
    python bot.py
    ```

---

## Commands | Komutlar

-   `/uploadlink [url] [filename]`: Uploads audio from a YouTube link. The audio will be trimmed to 15 seconds.
-   `/uploadfile [file]`: Upload an MP3 or WEBM file. The audio will be trimmed to 15 seconds.
-   `/my_sounds`: Lists all your uploaded sounds.
-   `/delete_sound [filename]`: Deletes a specific sound.
-   `/help`: Shows the help message with all available commands.

---

-   `/uploadlink [url] [dosyaadı]`: Bir YouTube bağlantısından ses yükler. Ses 15 saniyeye kırpılacaktır.
-   `/uploadfile [dosya]`: Bir MP3 veya WEBM dosyası yükler. Ses 15 saniyeye kırpılacaktır.
-   `/my_sounds`: Yüklediğiniz tüm sesleri listeler.
-   `/delete_sound [dosyaadı]`: Belirli bir sesi siler.
-   `/help`: Mevcut tüm komutları içeren yardım mesajını gösterir.
