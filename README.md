# T.E.M.E.L.

Windows için Python ile yazılmış sesli masaüstü asistanı. Sesli ve yazılı komutları anlar, uygulamaları açar, ekranı analiz eder, hava durumu / trafik / müzik bilgisi verir ve telefondan uzaktan komut alabilir.

> ⚠️ **Güvenlik uyarısı:** TEMEL bilgisayarını kontrol eder (uygulama açma, tıklama, kapatma vb.). Telefon kontrol sunucusunu yalnızca Tailscale gibi kapalı bir ağda ve güçlü bir şifreyle çalıştır. Asla doğrudan internete açma.

## Proje amacı

T.E.M.E.L., Türkçe konuşan kullanıcıların bilgisayarlarını **doğal dille, sesle ve eller serbest** kullanabilmesi için geliştirilmiş bir masaüstü asistanıdır. Kullanıcı "Temel" diye seslenip komutunu söyler. Asistan komutu anlar, ilgili işlemi yapar (uygulama açma, ses ayarlama, bilgi verme vb.) ve sesli cevap verir. Amaç, tek tek menülere ve tuşlara gitmeden günlük bilgisayar işlerini konuşarak halletmektir.

## Özellikler

- **Sesli komut:** "Temel" kelimesiyle uyanır, `Ctrl + Alt + T` kısayoluyla da dinlemeye başlar. Yazılı komut da kabul eder.
- **Uygulama ve oyun açma**, web sitesi açma, YouTube'da şarkı çalma
- **Sistem kontrolü:** ses seviyesi, medya durdur/başlat, pencere kapatma, masaüstünü gösterme, zamanlı bilgisayar kapatma
- **Ekranı anlama:** ekran görüntüsü alıp yapay zekâ ile yorumlama ve ekranda bir butonu bulup tıklama
- **Bilgi:** hava durumu, döviz kuru, Spotify'da çalan şarkı, TomTom ile trafik ve yol tarifi
- **Hafıza:** kullanıcının söylediği bilgileri (isim, sevdiği şeyler vb.) yerel bir veritabanında saklar
- **Proaktif uyarılar:** CPU/RAM/disk kullanımı yükselince, uzun süre aynı uygulama açık kalınca ve belirli saatlerde kendiliğinden konuşur; Windows bildirimlerini takip eder
- **Telefondan kontrol:** aynı ağdaki telefon tarayıcısından komut gönderme (isteğe bağlı)
- **Zamanlayıcı, not alma, gece ışığı ve tema değiştirme**

## Nasıl çalışır?

```
Mikrofon ──► Konuşma tanıma (Groq Whisper) ──► Komut metni
                                                   │
                       ┌───────────────────────────┴──────────────────────────┐
                       ▼                                                      ▼
         Hızlı tetikleyiciler                                   Yapay zekâ modeli (Groq)
   (örn. "sonraki şarkı", "sesi aç":                          Komutu anlar, uygun aracı seçer
     kelime eşleştirmesiyle doğrudan)                         (function / tool calling)
                       │                                                      │
                       └───────────────────────────┬──────────────────────────┘
                                                   ▼
                                  Araçlar: uygulama aç, ses ayarla, hava durumu,
                                  ekranda bul ve tıkla, trafik, hafıza...
                                                   │
                                                   ▼
                              Cevap ──► Ses sentezi (edge-tts, tr-TR-AhmetNeural) ──► Hoparlör
                                                   └──► Arayüz (PyQt5 HUD)
```

1. **Dinleme:** Mikrofon sesi kaydedilir ve Groq üzerindeki Whisper modeliyle yazıya çevrilir. Asistan, cümlede "Temel" kelimesini duyunca komutu işler.
2. **Anlama:** Sık kullanılan basit komutlar (müzik geçme, ses ayarı gibi) kelime eşleştirmesiyle hemen çalıştırılır. Diğerleri bir büyük dil modeline gönderilir. Model, tanımlı araçlardan (fonksiyonlardan) hangisinin hangi parametrelerle çağrılacağına karar verir.
3. **Eylem:** Seçilen araç Python kodu olarak çalışır. Örneğin `uygulama_veya_oyun_ac`, `ses_seviyesi_ayarla`, `hava_durumu_getir`, `ekranda_bul_ve_tikla`.
4. **Cevap:** Sonuç sesli (edge-tts) ve görsel (HUD arayüzü) olarak kullanıcıya iletilir.
5. **Arka plandaki işler:** Aynı anda ayrı iş parçacıkları (thread) çalışır: dinleme döngüsü, kısayol dinleyici, sistem kaynağı izleyici, bildirim tarayıcı ve telefon sunucusu.

| Katman | Kullanılan teknoloji |
|---|---|
| Programlama dili | Python |
| Konuşma tanıma | Groq Whisper (`whisper-large-v3-turbo`) |
| Yapay zekâ modeli | Groq (`openai/gpt-oss-120b`), ekran analizi için görsel model ve Gemini |
| Ses sentezi | edge-tts |
| Arayüz | PyQt5 |
| Bilgisayar kontrolü | pyautogui, pygetwindow, keyboard, pycaw, winsdk |
| Hafıza | SQLite |
| Telefon kontrolü | Flask + Tailscale (HTTPS) |

## Gizlilik ve güvenlik

- **Veri nereye gidiyor?** Mikrofon kayıtları konuşma tanıma için, komut metinleri yapay zekâ cevabı için, ekran görüntüleri ise ekran analizi özelliği kullanıldığında **Groq ve Gemini** sunucularına gönderilir. Ekranında hassas bilgi varken ekran analizi özelliğini kullanma.
- **Hafıza yerelde kalır.** Kullanıcı bilgileri `temel_hafiza.db` dosyasında, senin bilgisayarında saklanır. Bu dosyayı GitHub'a yükleme.
- **Anahtarlar koda yazılmaz.** Tüm API anahtarları ve şifreler ortam değişkeninden okunur.
- **Telefon sunucusu** şifre belirlenmezse başlamaz ve varsayılan olarak yalnızca bilgisayarın kendisinden (127.0.0.1) erişilebilir.
- **Bilgisayarı kontrol eden bir araçtır.** Tıklama, pencere kapatma ve kapatma komutları çalıştırır. Yalnızca kendi bilgisayarında ya da sahibinin izniyle kullan.

## Bilinen sınırlamalar

- Yalnızca Windows'ta çalışır, komutlar ve cevaplar Türkçedir.
- Ses tanıma ve yapay zekâ için internet bağlantısı gerekir.
- Gürültülü ortamda ses tanıma hata yapabilir.
- Bazı özellikler yazarın bilgisayarına göre ayarlanmıştır (aşağıdaki "Sana özel ayarlar" bölümüne bak).

## Kurulum kılavuzu (adım adım)

> TEMEL yalnızca **Windows 10/11** üzerinde çalışır. Mikrofon ve hoparlör gerekir. Bilgisayarı kontrol ettiği için (uygulama açma, tıklama, kapatma) **kendi bilgisayarında ya da sahibinden izin alarak** çalıştır.

### 1. Python'u kur
1. [python.org/downloads](https://www.python.org/downloads/) adresinden **Python 3.11** (3.10 – 3.12 önerilir) indir.
2. Kurulum penceresinin en altındaki **"Add python.exe to PATH"** kutusunu işaretle, sonra **Install Now** de.
3. Kontrol: PowerShell aç ve `python --version` yaz. Sürüm numarası görünmeli.

> Bazı paketler (örneğin `winsdk`) çok yeni Python sürümlerinde sorun çıkarabilir. Hata alırsan 3.11'e geç.

### 2. Projeyi indir
GitHub sayfasında yeşil **Code** düğmesi → **Download ZIP**. ZIP'i bir klasöre çıkar (örneğin `C:\Users\kullanici\temel`).

### 3. Kütüphaneleri yükle
Klasörün içinde boş bir yere **Shift + sağ tık → "PowerShell penceresini burada aç"** de ve şunu yaz:

```
python -m pip install -r requirements.txt
```

Yükleme birkaç dakika sürebilir. Bu komut şu kütüphaneleri kurar:

| Kütüphane | Ne için |
|---|---|
| `groq` | Yapay zekâ (ana beyin) |
| `google-genai` | Ekran analizi (isteğe bağlı) |
| `edge-tts`, `pygame` | Konuşma ve ses çalma |
| `sounddevice`, `scipy`, `numpy` | Mikrofon ve ses işleme |
| `PyQt5` | Arayüz (HUD) |
| `pyautogui`, `pygetwindow`, `keyboard` | Tıklama, pencere ve kısayol kontrolü |
| `pycaw`, `comtypes`, `winsdk` | Ses seviyesi ve Windows bildirimleri |
| `psutil` | Sistem durumu |
| `requests`, `ddgs`, `Pillow` | İnternet, arama ve görüntü |
| `spotipy`, `flask` | Spotify ve telefon kontrolü (isteğe bağlı) |

### 4. Groq anahtarını al
1. [console.groq.com](https://console.groq.com) adresine gir, hesap aç.
2. **API Keys** bölümünden yeni bir anahtar oluştur ve kopyala.
3. Anahtarı **kimseyle paylaşma, koda ya da GitHub'a yazma.**

### 5. Çalıştır
**Kolay yol:** `baslat.bat` dosyasına çift tıkla. Anahtarını sorar, sadece o oturum için kullanır, bilgisayara kaydetmez. Ortak bilgisayarlar için en güvenli yol budur.

**Kalıcı yol (kendi bilgisayarın):**
```
setx GROQ_API_KEY "anahtarin"
```
PowerShell'i kapatıp yeniden aç, sonra:
```
python temel.py
```

### Sorun giderme

| Hata | Çözüm |
|---|---|
| `python` tanınmıyor | Kurulumda "Add to PATH" işaretlenmemiş. Python'u kaldırıp yeniden kur |
| `No module named ...` | `python -m pip install -r requirements.txt` komutunu tekrar çalıştır |
| `winsdk` veya `PyQt5` kurulamıyor | Python 3.11 kullan |
| `GROQ_API_KEY ortam değişkeni tanımlı değil` | Anahtarı `baslat.bat` ile gir ya da `setx` yaptıktan sonra PowerShell'i yeniden aç |
| Ses gelmiyor / mikrofon çalışmıyor | Windows ses ayarlarında doğru mikrofon ve hoparlörü varsayılan yap |
| Okul/iş ağında internete bağlanamıyor | Ağ, Groq adresini engelliyor olabilir. Ağ yöneticisine sor veya kendi internetini kullan |

### Okul veya ortak bilgisayarda kullanım
- Önce **bilgisayarın sorumlusundan izin al**. Program kurmak için yönetici izni gerekebilir.
- Anahtarını `setx` ile kaydetme, `baslat.bat` kullan.
- Kullanım bitince klasörü sil. İşin içinde `notlar.txt`, `temel_hafiza.json` gibi kişisel dosyalar oluşmuş olabilir (Masaüstüne kaydedilir).
- Telefon kontrol sunucusunu ortak ağda **çalıştırma**. `TEMEL_TELEFON_SIFRE` tanımlamazsan zaten başlamaz.

## Ortam değişkenleri

| Değişken | Zorunlu | Açıklama |
|---|---|---|
| `GROQ_API_KEY` | Evet | Groq API anahtarı |
| `TOMTOM_API_KEY` | Hayır | Trafik ve yol tarifi |
| `TEMEL_TELEFON_SIFRE` | Telefon için | Boşsa telefon sunucusu başlamaz |
| `TEMEL_TELEFON_HOST` | Telefon için | Sunucunun bağlanacağı IP (Tailscale IP'n) |
| `TAILSCALE_MAGICDNS_ADI` | HTTPS için | `tailscale cert` ile alınan alan adı |
| `SPOTIPY_*` | Hayır | Spotify entegrasyonu |
| `ASISTAN_ADI` | Hayır | Asistanın adı (varsayılan: Temel) |
| `ASISTAN_EK_KELIMELER` | Hayır | Uyandırma için ek yazımlar, virgülle |

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
| **Not ve hafıza dosyaları** | `notlar.txt`, `temel_hafiza.json`, `temel_hafiza.db` | Not ve JSON dosyası Masaüstüne, `.db` dosyası programın çalıştığı klasöre kaydedilir. Başka yer istersen `NOT_DOSYASI` ve `HAFIZA_DOSYASI` satırlarını düzenle |
| **Ekran tanıma görselleri** | `teams_kabul.png`, `whatsapp_arama.png`, `discord_arama.png`, `teams_arama.png` | Bu görseller repoda yok. Teams/WhatsApp/Discord ile ilgili otomatik tıklama özellikleri için kendi ekran görüntülerinden hazırlayıp programla aynı klasöre koy |
| **Ses** | `tr-TR-AhmetNeural` | Başka bir `edge-tts` sesi seçebilirsin |
| **Konuşma dili** | Kod ve komutlar Türkçe | Başka dilde kullanmak için komut metinlerini çevirmen gerekir |

### Hangi anahtarlar zorunlu?

- **`GROQ_API_KEY`** zorunlu. Olmazsa TEMEL açılmaz.
- **TomTom, Gemini, Spotify** isteğe bağlı. Anahtarı yoksa sadece o özellikler çalışmaz, geri kalanı çalışır.
- **Telefon kontrolü** isteğe bağlı. `TEMEL_TELEFON_SIFRE` tanımlı değilse sunucu hiç başlamaz.

## Asistanın adını değiştirme

Varsayılan ad **Temel**. Kodu açmana gerek kalmadan adı değiştirebilirsin. PowerShell'de:

```
setx ASISTAN_ADI "Athena"
setx ASISTAN_EK_KELIMELER "atena,atina,atene"
```

PowerShell'i kapatıp yeniden aç ve TEMEL'i yeniden başlat. Bu ayar şunları değiştirir: uyandırma kelimesi, arayüz başlığı, sohbet etiketi ve yapay zekânın kendini tanıtma şekli.

- `ASISTAN_EK_KELIMELER` isteğe bağlıdır. Ses tanıma ismi farklı yazabilir (örneğin "Athena" yerine "Atina"). Konsolda programın ne duyduğuna bak, yanlış yazımları buraya ekle.
- Eski adına dönmek için: `setx ASISTAN_ADI "Temel"`.
- Dosya ve fonksiyon adları (`temel.py` vb.) değişmez, bunlara dokunma.
- Projeyi kendi sürümün olarak paylaşacaksan `LICENSE` dosyasını koru ve orijinal projeyi belirt (MIT lisansı şartı).

## Lisans

MIT, bkz. `LICENSE`.
