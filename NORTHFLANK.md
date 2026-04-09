# Northflank Deploy Rehberi

## Ön gereksinimler
- Northflank Hesabı
- GitHub / GitLab repo bağlantısı

---

## Adım 1: Servis Oluşturma

1. Northflank paneline giriş yap
2. Yeni **Service** oluştur
3. Kaynak olarak Git deposunu seç ve proje repo'nu bağla
4. **Build ayarları**:
   - Build Type: `Dockerfile`
   - Dockerfile yolu: `./Dockerfile` (varsayılan)
   - Build context: `./`

---

## Adım 2: Çevresel Değişkenler

**Environment Variables** bölümüne ekle:
```
DISCORD_TOKEN=senin_tokenin
# Diğer config değişkenleri buraya ekle
```

.env dosyasını doğrudan yükleyebilirsin.

---

## Adım 3: Kalıcı Depolama (Volume)

⚠️ **ÖNEMLİ**: Bu adımı atlama yoksa tüm veriler restartta silinir!

1. Servis ayarlarında **Volumes** bölümüne git
2. Yeni volume ekle:
   - Mount path: `/app/data`
   - Boyut: Min 1 GB yeterli
   - Access mode: `ReadWriteOnce`

✅ Bu disk `bot.py` içinde `/app/data` klasörüne bağlanır ve kalıcıdır.

---

## Adım 4: Kaynak Ayarları

Minimum önerilen kaynaklar:
- CPU: 0.5 vCPU
- Bellek: 512 MB
- Otomatik restart: Aktif

---

## Adım 5: Deploy

1. **Deploy** butonuna tıkla
2. Build ve deploy işlemleri başlayacak
3. Logları izle, bot çalıştığında Discord'da online olacaktır.

---

## Önemli Notlar

- `/app/data` klasörü kalıcıdır, bot veritabanı dosyalarını, configleri buraya kaydedin
- FFmpeg ve Opus zaten Docker imajında yüklüdür
- Bot Northflank üzerinde restart edildiğinde hiçbir veri kaybolmaz
- Güncellemeleri GitHub'a attığınızda Northflank otomatik deploy eder
