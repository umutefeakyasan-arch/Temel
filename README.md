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

## Lisans

MIT, bkz. `LICENSE`.
