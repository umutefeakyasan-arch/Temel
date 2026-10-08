# T.E.M.E.L.

Windows için Python ile yazılmış sesli masaüstü asistanı. Sesli ve yazılı komutları anlar, uygulamaları açar, ekranı analiz eder, hava durumu / trafik / müzik bilgisi verir ve telefondan uzaktan komut alabilir.

> ⚠️ **Güvenlik uyarısı:** TEMEL bilgisayarını kontrol eder (uygulama açma, tıklama, kapatma vb.). Telefon kontrol sunucusunu yalnızca Tailscale gibi kapalı bir ağda ve güçlü bir şifreyle çalıştır. Asla doğrudan internete açma.

## Kurulum

1. Python 3.10+ kur.
2. Bağımlılıkları yükle:
   ```
   pip install -r requirements.txt
   ```
3. `.env.example` dosyasındaki değişkenleri kendi değerlerinle ortam değişkeni olarak tanımla (Windows: `setx GROQ_API_KEY "..."`). Terminali yeniden aç.
4. Çalıştır:
   ```
   python temel.py
   ```

## Ortam değişkenleri

| Değişken | Zorunlu | Açıklama |
|---|---|---|
| `GROQ_API_KEY` | Evet | Groq API anahtarı |
| `TOMTOM_API_KEY` | Hayır | Trafik ve yol tarifi |
| `TEMEL_TELEFON_SIFRE` | Telefon için | Boşsa telefon sunucusu başlamaz |
| `TEMEL_TELEFON_HOST` | Telefon için | Sunucunun bağlanacağı IP (Tailscale IP'n) |
| `TAILSCALE_MAGICDNS_ADI` | HTTPS için | `tailscale cert` ile alınan alan adı |
| `SPOTIPY_*` | Hayır | Spotify entegrasyonu |

Ekran analizi için Gemini kullanılıyorsa anahtarı `gemini_key.txt` dosyasına yaz (bu dosya `.gitignore`'dadır).

## Telefondan kullanım

1. Bilgisayara ve telefona Tailscale kur, aynı hesapla bağlan.
2. `tailscale cert <alan-adin>` ile sertifika al, `.crt` ve `.key` dosyalarını `temel.py` ile aynı klasöre koy.
3. Telefonda `https://<alan-adin>:5005` adresini aç.

## Sana özel ayarlar (kendi bilgisayarına göre değiştir)

TEMEL ilk olarak yazarın kendi bilgisayarı için yapıldı. Bu yüzden aşağıdaki yerleri kendi kullanımına göre düzenlemen gerekebilir. Satır numaraları yaklaşıktır, `Ctrl+F` ile arayabilirsin.

| Ne | Nerede arayacaksın | Ne yapmalısın |
|---|---|---|
| **Sadece Windows** | `winreg`, `winsound`, `winsdk` | Linux ve macOS'ta çalışmaz |
| **Konum / hava durumu** | `41.0082`, `"Istanbul"` | Koordinatları ve varsayılan şehri kendi şehrinle değiştir (`hava_durumu_al`, `hava_durumu_getir`) |
| **Steam oyunları** | `STEAM_OYUNLARI` | Oyun adı ve Steam ID eşleşmelerini kendi oyunlarına göre düzenle |
| **Masaüstü kısayolları** | `.lnk` yazan sözlükler (`valorant`, `discord`, `netflix` vb.) | Değerleri masaüstündeki kısayol adlarınla aynı yap. Kısayolun yoksa o komut çalışmaz |
| **Opera GX yolu** | `Opera GX\launcher.exe` | Farklı tarayıcı veya farklı kurulum yolu kullanıyorsan değiştir |
| **Not ve hafıza dosyaları** | `notlar.txt`, `temel_hafiza.json` | Masaüstüne kaydedilir. Başka yer istersen `NOT_DOSYASI` ve `HAFIZA_DOSYASI` satırlarını düzenle |
| **Ses** | `tr-TR-AhmetNeural` | Başka bir `edge-tts` sesi seçebilirsin |
| **Konuşma dili** | Kod ve komutlar Türkçe | Başka dilde kullanmak için komut metinlerini çevirmen gerekir |

### Hangi anahtarlar zorunlu?

- **`GROQ_API_KEY`** zorunlu. Olmazsa TEMEL açılmaz.
- **TomTom, Gemini, Spotify** isteğe bağlı. Anahtarı yoksa sadece o özellikler çalışmaz, geri kalanı çalışır.
- **Telefon kontrolü** isteğe bağlı. `TEMEL_TELEFON_SIFRE` tanımlı değilse sunucu hiç başlamaz.

## Lisans

MIT, bkz. `LICENSE`.
