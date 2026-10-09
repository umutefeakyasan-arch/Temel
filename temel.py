import os
import hmac
import subprocess
import asyncio
import datetime
import webbrowser
import time
import base64
import threading
import re
import warnings
warnings.filterwarnings("ignore")
import urllib.parse
import sys
import math
import numpy as np
import random
import json
import requests
import tempfile
import sqlite3
import wave
from google import genai
import edge_tts
import pygame
import urllib.request
import pyautogui
import pygetwindow as gw
import psutil       # Sistem durum takibi için

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_MEVCUT = True
except ImportError:
    SPOTIPY_MEVCUT = False
    print("spotipy kütüphanesi bulunamadı. 'pip install spotipy --break-system-packages' ile kurup yeniden başlat.")

try:
    from flask import Flask, request, jsonify
    FLASK_MEVCUT = True
except ImportError:
    FLASK_MEVCUT = False
    print("Flask kütüphanesi bulunamadı. 'pip install flask --break-system-packages' ile kurup yeniden başlat.")
import keyboard     # Kısayol tuşu (HotKey) için
import winsound     # Zamanlayıcı alarmı için (Windows Bip Sesi)
import winreg       # Gece ışığı ayarı için (Windows Kayıt Defteri)

try:
    import winsdk.windows.ui.notifications.management as unlm
    import winsdk.windows.ui.notifications as un
    WINSDK_MEVCUT = True
except ImportError:
    WINSDK_MEVCUT = False
    print("winsdk kütüphanesi bulunamadı. 'pip install winsdk --break-system-packages' ile kurup yeniden başlat.")
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from PIL import Image, ImageDraw


# Groq Whisper için Ses Kayıt Kütüphaneleri
import sounddevice as sd
from scipy.io.wavfile import write

# Windows Pencere Başlıklarını Okumak İçin
try:
    import pygetwindow as gw
except ImportError:
    gw = None

# GÜNCEL İNTERNET ARAMASI IMPORTU
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# PyQt5 Grafik ve UI Importları
from PyQt5.QtWidgets import (QApplication, QWidget, QTextEdit, QLineEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QRadialGradient

from groq import Groq

# ==========================================
# 1. API, HAFIZA VE GROQ AYARLARI
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise SystemExit("HATA: GROQ_API_KEY ortam değişkeni tanımlı değil. .env.example dosyasına bak.")
groq_client = Groq(api_key=GROQ_API_KEY)

# --- ASİSTAN ADI (isim değiştirmek için sadece bu bölüme bak) ---
# İsim değiştirmek için ortam değişkeni tanımla, örneğin:  setx ASISTAN_ADI "Athena"
# Whisper ismi farklı yazabilir; yanlış duyulan yazımları virgülle ekleyebilirsin:
#   setx ASISTAN_EK_KELIMELER "atena,atina,atene"
ASISTAN_ADI = (os.getenv("ASISTAN_ADI") or "Temel").strip()
_EK_KELIMELER = [k.strip().lower() for k in (os.getenv("ASISTAN_EK_KELIMELER") or "").split(",") if k.strip()]
if ASISTAN_ADI.lower() == "temel":
    TETIKLEYICI_KELIMELER = ["temel", "temeli", "temem", "temed"] + _EK_KELIMELER
    HUD_BASLIK = "T.E.M.E.L."
    KIMLIK_CUMLESI = "Sen T.E.M.E.L.'sin (Teknolojik Entegre Mantıksal Elektronik Lider)."
else:
    TETIKLEYICI_KELIMELER = [ASISTAN_ADI.lower()] + _EK_KELIMELER
    HUD_BASLIK = ASISTAN_ADI.upper()
    KIMLIK_CUMLESI = f"Senin adın {ASISTAN_ADI}."

# Groq tarafında güncel ve aktif model
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_VISION_MODEL = "qwen/qwen3.8-27b"  # Vision/ekran analizi için - hesabında erişilemezse burayı değiştir

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")

NOT_DOSYASI = os.path.join(os.path.expanduser("~"), "Desktop", "notlar.txt")
HAFIZA_DOSYASI = os.path.join(os.path.expanduser("~"), "Desktop", "temel_hafiza.json")
TEMP_AUDIO_FILE = "input_speech.wav"

def hafiza_yukle():
    if os.path.exists(HAFIZA_DOSYASI):
        try:
            with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Hafıza okuma hatası: {e}")
    return {
        "kullanici_bilgileri": {
            "takim": "Trabzonspor",
            "konum": "Istanbul"
        },
        "sohbet_gecmisi": []
    }

def hafiza_kaydet(data):
    try:
        with open(HAFIZA_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Hafıza kaydetme hatası: {e}")

KALICI_HAFIZA = hafiza_yukle()
SOHBET_HAFIZASI = KALICI_HAFIZA.get("sohbet_gecmisi", [])
MAX_HAFIZA_UZUNLUGU = 10

def kullanici_bilgisi_kaydet(anahtar, deger):
    """Kullanıcıyla ilgili kalıcı bir bilgiyi (sohbet geçmişinden BAĞIMSIZ olarak)
    KALICI_HAFIZA içine yazar. Böylece sohbet geçmişi silinse/kısalsa bile bu bilgi kalır."""
    global KALICI_HAFIZA
    try:
        anahtar = anahtar.strip().lower().replace(" ", "_")
        KALICI_HAFIZA.setdefault("kullanici_bilgileri", {})[anahtar] = deger
        hafiza_kaydet(KALICI_HAFIZA)
        return f"{anahtar} bilgisini kaydettim."
    except Exception as e:
        print(f"Kullanıcı bilgisi kaydetme hatası: {e}")
        return "Bilgiyi kaydederken bir sorun oldu." 

STEAM_OYUNLARI = {
    "csgo": "730", "cs2": "730", "counter strike": "730", "counter-strike": "730",
    "pubg": "578080", "gta 5": "271590", "gta v": "271590", "gta": "271590",
    "apex": "1172470", "apex legends": "1172470", "rust": "252490", "rocket league": "252950",
    "ets 2": "227300", "euro truck": "227300", "efootball": "1665460", "football manager": "2251330",
    "fm": "2251330", "dota": "570", "terraria": "105600", "unturned": "304930"
}

KELIME_DUZELTME = {
    "temem": "temel",
    "temed": "temel",
    "teyp": "temel",
    "temeli": "temel",
    "sesi kır": "sesi kıs",
    "sesı kıs": "sesi kıs",
    "sönraki": "sonraki"
}

# ==========================================
# 2. FUNCTION CALLING (ARAÇLAR) ŞEMASI
# ==========================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "hava_durumu_getir",
            "description": "Belirtilen şehir için anlık hava durumu bilgisini öğrenir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sehir": {"type": "string", "description": "Hava durumu öğrenilecek şehir adı (örn: Istanbul, Trabzon)"}
                },
                "required": ["sehir"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "uygulama_veya_oyun_ac",
            "description": "Bilgisayarda YENİ bir program/uygulama/Steam oyunu başlatır (örn. Chrome, Discord, Valorant, Netflix uygulamasının kendisi). BİR UYGULAMANIN İÇİNDEKİ bir dizi/film/menü öğesi/buton için bunu KULLANMA (Netflix zaten açıksa 'The Mentalist'i aç' demek bu değildir) - onun için ekranda_bul_ve_tikla aracını kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "isim": {"type": "string", "description": "Açılacak uygulama veya oyun adı (örn: Spotify, Discord, CS2, Chrome, Not Defteri)"}
                },
                "required": ["isim"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_direkt_sarki_ac",
            "description": "YouTube üzerinde aranan bir şarkıyı veya videoyu doğrudan açar ve oynatır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sorgu": {"type": "string", "description": "Oynatılacak şarkı veya video adı"}
                },
                "required": ["sorgu"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "zamanlayici_baslat",
            "description": "Belirtilen süre (dakika) sonunda çalacak alarm ve zamanlayıcı kurar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dakika": {"type": "number", "description": "Kaç dakika sonra alarm çalacağı"},
                    "hatirlatma_metni": {"type": "string", "description": "Zamanlayıcı bittiğinde söylenecek hatırlatma mesajı"}
                },
                "required": ["dakika"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ekran_goruntusu_al",
            "description": "Anlık ekran görüntüsünü (screenshot) alarak Masaüstüne kaydeder.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tema_degistir",
            "description": "Arayüzün görünüm temasını veya rengini değiştirir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tema_adi": {"type": "string", "description": "Tema seçeneği: bordo, kırmızı, yeşil, mor, mavi, rgb, sarı, neon"}
                },
                "required": ["tema_adi"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ses_seviyesi_ayarla",
            "description": "Bilgisayarın ses seviyesini %0 ile %100 arasında belirli bir yüzdeye ayarlar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seviye": {"type": "integer", "description": "0 ile 100 arasında ses yüzdesi"}
                },
                "required": ["seviye"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sistem_komutu_calistir",
            "description": "Sistem, pencere, medya veya güç yönetimi komutlarını çalıştırır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem": {
                        "type": "string", 
                        "description": "İşlem türü: ses_kis, ses_ac, sessiz, medya_durdur_baslat (müziği durdur, oynat, başlat, durdur), pencere_kapat, masaustu_goster, bilgisayari_kapat, kapatmayi_iptal_et"
                    },
                    "parametre": {"type": "string", "description": "Eğer bilgisayarı kapatma ise dakika sayısı"}
                },
                "required": ["islem"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kullanici_bilgisi_kaydet",
            "description": "Kullanıcının kendisiyle ilgili kalıcı olarak hatırlanmasını isteyeceğin türden bir bilgi paylaştığında (isim, meslek, evcil hayvan adı, favori takım/renk/yemek, doğum günü, iş yeri vb.) bu bilgiyi kalıcı hafızaya kaydeder. Sıradan sohbet cümlelerinde ÇAĞIRMA, sadece net ve kalıcı bir bilgi olduğunda kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "anahtar": {"type": "string", "description": "Bilginin kısa adı (örn: isim, meslek, evcil_hayvan, sevdigi_takim, dogum_gunu)"},
                    "deger": {"type": "string", "description": "Bilginin değeri (örn: Ahmet, yazılımcı, Pamuk, Trabzonspor)"}
                },
                "required": ["anahtar", "deger"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ekranda_bul_ve_tikla",
            "description": "Ekranda görsel olarak bir metin, buton, ikon veya menü öğesi arar (gerekirse aşağı kaydırıp tekrar dener) ve bulunca üzerine tıklar. Kullanıcı zaten açık olan bir uygulama/pencere İÇİNDE bir şeyi seçmek/açmak istediğinde kullan (örn. 'The Mentalist'i aç' derken Netflix zaten açıksa, ya da 'Hesaplar sekmesine tıkla' gibi). Yeni bir UYGULAMA başlatmak için bunu değil, uygulama_veya_oyun_ac aracını kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hedef": {"type": "string", "description": "SADECE aranacak öğenin kendisinin kısa tarifi - 'ekranda', 'yazan yere', 'tıkla' gibi komut/talimat kelimelerini KESİNLİKLE dahil ETME. Örnek doğru: 'The Mentalist dizisi'. Örnek YANLIŞ: 'ekranda The Mentalist yazan yere'."}
                },
                "required": ["hedef"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_sitesi_ac",
            "description": "Bir web sitesini varsayılan tarayıcıda açar (YouTube, Google, Gmail gibi). Kullanıcı bir WEBSITE'yi açmak istediğinde bunu kullan, uygulama_veya_oyun_ac'ı DEĞİL - web siteleri bilgisayarda kurulu bir program değildir, exe olarak aranamaz.",
            "parameters": {
                "type": "object",
                "properties": {
                    "site_adi_veya_url": {"type": "string", "description": "Site adı (örn. 'youtube', 'google') ya da tam URL (örn. 'https://youtube.com')"}
                },
                "required": ["site_adi_veya_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_traffic_route",
            "description": "İki konum arasındaki güncel trafik durumuna göre tahmini süre ve mesafeyi söyler. Kullanıcı 'X'ten Y'ye nasıl giderim', 'trafik nasıl' gibi bir şey sorduğunda kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "baslangic": {"type": "string", "description": "Başlangıç konumu/semt/adres (örn. 'Esenyurt')"},
                    "bitis": {"type": "string", "description": "Varış konumu/semt/adres (örn. 'Üsküdar')"}
                },
                "required": ["baslangic", "bitis"]
            }
        }
    }
]

# Thread'ler arası GUI çakışmasını (QTextCursor hatasını) önleyen Signal Köprüsü
class UIBridge(QObject):
    chat_append_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str, str)

ui_bridge = UIBridge()

# ==========================================
# 3. ADVANCED JARVIS HUD + CHAT PANEL ARAYÜZÜ
# ==========================================
class TemelJarvisHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Ana Pencere Boyutu (Genişlik ferahlatıldı)
        self.resize(1250, 620)

        self.angle = 0
        self.pulse = 0
        self.pulse_dir = 1
        self.rgb_hue = 0
        
        self.cpu_usage = 0
        self.ram_usage = 0

        self.num_bars = 48
        self.bar_heights = [5 for _ in range(self.num_bars)]

        self.status_mode = "LISTENING"
        self.status_text = "SYSTEM READY // WAITING FOR INPUT"
        self.last_msg = ""

        self.current_theme = "bordo"
        self.themes = {
            "mavi": {"main": QColor(0, 230, 255), "glow": QColor(0, 230, 255, 100), "bg": QColor(10, 40, 70, 180), "outer": QColor(0, 230, 255)},
            "kırmızı": {"main": QColor(255, 40, 40), "glow": QColor(255, 40, 40, 100), "bg": QColor(70, 10, 10, 180), "outer": QColor(255, 40, 40)},
            "yeşil": {"main": QColor(0, 255, 120), "glow": QColor(0, 255, 120, 100), "bg": QColor(10, 70, 30, 180), "outer": QColor(0, 255, 120)},
            "mor": {"main": QColor(180, 50, 255), "glow": QColor(180, 50, 255, 100), "bg": QColor(50, 10, 70, 180), "outer": QColor(180, 50, 255)},
            "bordo": {"main": QColor(30, 160, 230), "glow": QColor(30, 160, 230, 120), "bg": QColor(15, 30, 60, 190), "outer": QColor(140, 10, 35)},
            "sarı": {"main": QColor(255, 215, 0), "glow": QColor(255, 215, 0, 100), "bg": QColor(50, 40, 10, 180), "outer": QColor(255, 165, 0)},
            "neon": {"main": QColor(255, 0, 128), "glow": QColor(255, 0, 128, 100), "bg": QColor(50, 10, 40, 180), "outer": QColor(0, 255, 255)}
        }

        self.init_ui()

        # Thread-safe Signal Bağlantıları
        ui_bridge.chat_append_signal.connect(self.append_chat)
        ui_bridge.status_signal.connect(self.set_status)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

        self.drag_position = None

    def init_ui(self):
        # Sohbet kutusunu orb'un sağ tarafına ferah bir şekilde hizalıyoruz
        self.chat_container = QFrame(self)
        self.chat_container.setGeometry(580, 10, 370, 500)

        layout = QVBoxLayout(self.chat_container)
        layout.setContentsMargins(15, 15, 15, 15)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-family: 'Consolas', 'Segoe UI';
                font-size: 13px;
            }
        """)
        layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"{ASISTAN_ADI} için mesaj yazın...")
        self.input_field.returnPressed.connect(self.send_text_message)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Gönder")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.send_text_message)
        input_layout.addWidget(self.send_button)

        layout.addLayout(input_layout)

        self.update_chat_style()

    def update_chat_style(self):
        if self.current_theme == "rgb":
            rgb_color = QColor.fromHsv(self.rgb_hue, 255, 255).name()
            bg_color = "rgba(15, 23, 42, 0.85)"
            border_color = rgb_color
            btn_bg = rgb_color
        elif self.current_theme == "bordo":
            bg_color = "rgba(15, 23, 42, 0.85)"
            border_color = "#1ea0e6"
            btn_bg = "#8c0a23"
        else:
            theme = self.themes.get(self.current_theme, self.themes["bordo"])
            main_color = theme["main"].name()
            bg_color = f"rgba({theme['bg'].red()}, {theme['bg'].green()}, {theme['bg'].blue()}, 0.85)"
            border_color = main_color
            btn_bg = main_color

        self.chat_container.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 15px;
            }}
        """)

        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(30, 41, 59, 0.9);
                border: 1px solid {border_color};
                border-radius: 8px;
                color: #ffffff;
                padding: 8px;
                font-family: 'Consolas', 'Segoe UI';
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {border_color};
            }}
        """)

        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: #ffffff;
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: bold;
                font-family: 'Consolas';
            }}
        """)

    def append_chat(self, gonderen, mesaj):
        renk = "#00e6ff" if gonderen in ["Siz", "Siz (Ses)"] else "#00ff78"
        html = f"<div style='margin-bottom: 8px; background-color: rgba(15, 23, 42, 0.5); padding: 5px 8px; border-radius: 6px;'><b style='color: {renk};'>{gonderen}:</b> <span style='color: #ffffff;'>{mesaj}</span></div>"
        self.chat_history.append(html)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def send_text_message(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.append_chat("Siz", text)
            threading.Thread(target=yazili_komut_isle, args=(text,), daemon=True).start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def set_status(self, mode, text=""):
        self.status_mode = mode
        if text:
            self.status_text = text
            if mode == "SPEAKING":
                self.last_msg = text

    def set_theme(self, tema_adi):
        if tema_adi in self.themes or tema_adi == "rgb":
            self.current_theme = tema_adi
            self.update_chat_style()

    def animate(self):
        speed = 2 if self.status_mode == "LISTENING" else (5 if self.status_mode in ["THINKING", "CALL"] else 3)
        self.angle = (self.angle + speed) % 360
        self.rgb_hue = (self.rgb_hue + 3) % 360

        if self.current_theme == "rgb":
            self.update_chat_style()

        if self.status_mode in ["SPEAKING", "CALL"]:
            self.pulse = random.uniform(4, 14)
        else:
            self.pulse += 0.3 * self.pulse_dir
            if self.pulse > 6 or self.pulse < 0:
                self.pulse_dir *= -1

        self.cpu_usage = psutil.cpu_percent()
        self.ram_usage = psutil.virtual_memory().percent

        for i in range(self.num_bars):
            if self.status_mode in ["SPEAKING", "CALL"]:
                target = random.randint(20, 55)
            elif self.status_mode == "THINKING":
                target = random.randint(8, 25)
            else:
                target = random.randint(3, 10)
            
            self.bar_heights[i] += (target - self.bar_heights[i]) * 0.3

        self.update()

    def draw_circular_gauge(self, painter, x, y, radius, label, percent, color, bg_color):
        pen_bg = QPen(bg_color, 3)
        painter.setPen(pen_bg)
        painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

        pen_active = QPen(color, 4)
        pen_active.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_active)
        span_angle = int((percent / 100.0) * 360 * 16)
        painter.drawArc(x - radius, y - radius, radius * 2, radius * 2, 90 * 16, -span_angle)

        pen_sub = QPen(color, 1)
        painter.setPen(pen_sub)
        sub_r = radius - 8
        painter.drawArc(x - sub_r, y - sub_r, sub_r * 2, sub_r * 2, int(-self.angle * 16), 100 * 16)

        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.drawText(x - radius, y - 10, radius * 2, 15, Qt.AlignCenter, label)
        
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QPen(color))
        painter.drawText(x - radius, y + 5, radius * 2, 15, Qt.AlignCenter, f"%{int(percent)}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = 270
        center_y = self.height() // 2 - 20

        if self.status_mode == "CALL":
            main_color = QColor(255, 50, 50)
            glow_color = QColor(255, 50, 50, 120)
            dark_bg = QColor(60, 10, 10, 200)
            outer_color = QColor(255, 100, 0)
        elif self.current_theme == "rgb":
            main_color = QColor.fromHsv(self.rgb_hue, 255, 255)
            outer_color = QColor.fromHsv((self.rgb_hue + 180) % 360, 255, 255)
            glow_color = QColor.fromHsv(self.rgb_hue, 200, 255, 120)
            dark_bg = QColor(20, 20, 30, 180)
        else:
            # DOST CANLISI BORDO-MAVİ TEMA
            if self.status_mode == "LISTENING":
                main_color = QColor(0, 210, 255)         # Canlı Açık Turkuaz Mavi (Dinliyor)
                glow_color = QColor(0, 210, 255, 140)
                dark_bg = QColor(5, 25, 45, 220)
                outer_color = QColor(0, 160, 230)
            elif self.status_mode == "PROCESSING":
                main_color = QColor(255, 195, 0)         # Sıcak Yumuşak Sarı (Düşünüyor)
                glow_color = QColor(255, 195, 0, 150)
                dark_bg = QColor(35, 30, 10, 220)
                outer_color = QColor(230, 170, 0)
            elif self.status_mode == "SPEAKING":
                main_color = QColor(0, 180, 255)         # Ana Göstergeler Parlak Mavi (Konuşuyor)
                glow_color = QColor(140, 20, 60, 160)     # Arkadaki Parıltı Tatlı Bordo Glow
                dark_bg = QColor(30, 10, 25, 220)         # Arka Plan Yumuşak Bordo-Mor Derinlik
                outer_color = QColor(180, 30, 70)        # Dış Halka İnce Bordo Detay
            else:
                # HAZIR BEKLEME
                main_color = QColor(0, 180, 240)
                glow_color = QColor(0, 180, 240, 100)
                dark_bg = QColor(10, 15, 30, 220)
                outer_color = QColor(0, 150, 220)

        # Arka Plan Panel Çerçevesi
        painter.setBrush(QBrush(QColor(10, 15, 25, 230)))
        painter.setPen(QPen(main_color, 1))
        painter.drawRoundedRect(10, 10, 530, 580, 20, 20)

        orange_speed = QColor(255, 165, 0) if self.status_mode != "PROCESSING" else QColor(255, 215, 0)

        # 1. Dış Halka (Dönüş Hızı Düşünürken Artar)
        pen_outer = QPen(outer_color, 4)
        painter.setPen(pen_outer)
        radius_outer = 190
        painter.drawArc(center_x - radius_outer, center_y - radius_outer, radius_outer * 2, radius_outer * 2, int(self.angle * 16), 140 * 16)
        painter.drawArc(center_x - radius_outer, center_y - radius_outer, radius_outer * 2, radius_outer * 2, int((self.angle + 180) * 16), 140 * 16)

        # 2. Dış Ticks (Çizgili Radar Halka)
        pen_tick = QPen(glow_color, 2)
        painter.setPen(pen_tick)
        tick_radius_in = 165
        tick_radius_out = 175
        for i in range(0, 360, 10):
            rad = math.radians(i)
            x1 = center_x + int(tick_radius_in * math.cos(rad))
            y1 = center_y + int(tick_radius_in * math.sin(rad))
            x2 = center_x + int(tick_radius_out * math.cos(rad))
            y2 = center_y + int(tick_radius_out * math.sin(rad))
            painter.drawLine(x1, y1, x2, y2)

        # 3. Turuncu Hız Arc (Sonsuz Akıcı Dönüş)
        pen_orange = QPen(orange_speed, 6)
        pen_orange.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_orange)
        radius_speed = 150
        
        # Açı hesaplamasını sürekli dönecek şekilde yumuşatıyoruz (360 moduna tam sayı olarak sokuyoruz)
        start_angle = int((self.angle * 2) % 360) * 16
        span_angle = 100 * 16
        painter.drawArc(center_x - radius_speed, center_y - radius_speed, radius_speed * 2, radius_speed * 2, start_angle, span_angle)

        # 4. Ses Frekans Çizgileri (Visualizer)
        visualizer_radius = 110 + int(self.pulse * 0.5)
        pen_bar = QPen(main_color, 3)
        pen_bar.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bar)

        for i in range(self.num_bars):
            angle_deg = (i * (360 / self.num_bars) + self.angle) % 360
            rad = math.radians(angle_deg)
            h = self.bar_heights[i]

            x1 = center_x + int(visualizer_radius * math.cos(rad))
            y1 = center_y + int(visualizer_radius * math.sin(rad))
            x2 = center_x + int((visualizer_radius + h) * math.cos(rad))
            y2 = center_y + int((visualizer_radius + h) * math.sin(rad))

            painter.drawLine(x1, y1, x2, y2)

        # 5. İç Çekirdek Daire (Videodaki Neon Glowing Core Efekti)
        core_radius = 95 + int(self.pulse)
        
        # Merkezden dışa doğru parıldayan gradyan oluştur
        radial_gradient = QRadialGradient(center_x, center_y, core_radius)
        radial_gradient.setColorAt(0.0, QColor(main_color.red(), main_color.green(), main_color.blue(), 160)) # Merkez canlı
        radial_gradient.setColorAt(0.7, QColor(main_color.red(), main_color.green(), main_color.blue(), 40))  # Kenara doğru şeffaf
        radial_gradient.setColorAt(1.0, dark_bg) # Dış sınır

        painter.setBrush(QBrush(radial_gradient))
        painter.setPen(QPen(main_color, 2))
        painter.drawEllipse(center_x - core_radius, center_y - core_radius, core_radius * 2, core_radius * 2)

        # 6. Dairesel CPU ve RAM Göstergeleri (Sol Panelle Çakışmayacak Konum)
        self.draw_circular_gauge(painter, center_x - 155, center_y - 105, 36, "CPU", self.cpu_usage, main_color, glow_color)
        self.draw_circular_gauge(painter, center_x + 155, center_y - 105, 36, "RAM", self.ram_usage, main_color, glow_color)

        # 7. Merkez Başlık Yazısı
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Consolas", 18, QFont.Bold))
        text = "INCOMING CALL" if self.status_mode == "CALL" else HUD_BASLIK
        fm = QFontMetrics(painter.font())
        text_w = fm.width(text)
        text_h = fm.height()
        painter.drawText(center_x - (text_w // 2), center_y + (text_h // 4), text)

        # 8. Alt Durum Yazısı (Renklendirilmiş)
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.setPen(QPen(main_color))
        painter.drawText(center_x - 200, center_y + 220, 400, 30, Qt.AlignCenter, f"STATUS: {self.status_text}")

        # ===================================================
        # SOL PANEL: JARVIS BİLGİ KARTLARI (ÇAKIŞMASIZ & KÖŞELİ)
        # ===================================================
        x_left = 20
        y_left = 30
        panel_w = 95  # Genişlik CPU dairesine çarpmayacak şekilde daraltıldı

        # --- 1. SAAT KART ---
        suanki_zaman = QDateTime.currentDateTime()
        saat_str = suanki_zaman.toString("hh:mm:ss")
        tarih_str = suanki_zaman.toString("dd.MM.yyyy")

        # Şeffaf Arka Plan
        painter.setBrush(QBrush(QColor(10, 20, 35, 140)))
        painter.setPen(QPen(QColor(0, 0, 0, 0))) # Çerçevesiz
        painter.drawRect(x_left, y_left, panel_w, 50)

        # Jarvis Köşe Çizgileri (┌ ┐ └ ┘)
        pen_corner = QPen(main_color, 1)
        painter.setPen(pen_corner)
        cl = 6 # Köşe çizgi uzunluğu
        # Sol üst & Sağ üst
        painter.drawLine(x_left, y_left, x_left + cl, y_left)
        painter.drawLine(x_left, y_left, x_left, y_left + cl)
        painter.drawLine(x_left + panel_w, y_left, x_left + panel_w - cl, y_left)
        painter.drawLine(x_left + panel_w, y_left, x_left + panel_w, y_left + cl)
        # Sol alt & Sağ alt
        painter.drawLine(x_left, y_left + 50, x_left + cl, y_left + 50)
        painter.drawLine(x_left, y_left + 50, x_left, y_left + 50 - cl)
        painter.drawLine(x_left + panel_w, y_left + 50, x_left + panel_w - cl, y_left + 50)
        painter.drawLine(x_left + panel_w, y_left + 50, x_left + panel_w, y_left + 50 - cl)

        # Yazılar
        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        painter.setPen(QPen(main_color))
        painter.drawText(x_left + 5, y_left + 12, "TIME")
        
        painter.setFont(QFont("Consolas", 11, QFont.Bold))
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(x_left, y_left + 28, panel_w, 15, Qt.AlignCenter, saat_str)

        painter.setFont(QFont("Consolas", 6, QFont.Bold))
        painter.setPen(QPen(main_color))
        painter.drawText(x_left, y_left + 42, panel_w, 10, Qt.AlignCenter, tarih_str)

        # --- 2. HAVA DURUMU KARTI ---
        y_left += 60
        painter.setBrush(QBrush(QColor(10, 20, 35, 140)))
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.drawRect(x_left, y_left, panel_w, 45)

        # Köşeler
        painter.setPen(pen_corner)
        painter.drawLine(x_left, y_left, x_left + cl, y_left)
        painter.drawLine(x_left, y_left, x_left, y_left + cl)
        painter.drawLine(x_left + panel_w, y_left, x_left + panel_w - cl, y_left)
        painter.drawLine(x_left + panel_w, y_left, x_left + panel_w, y_left + cl)
        painter.drawLine(x_left, y_left + 45, x_left + cl, y_left + 45)
        painter.drawLine(x_left, y_left + 45, x_left, y_left + 45 - cl)
        painter.drawLine(x_left + panel_w, y_left + 45, x_left + panel_w - cl, y_left + 45)
        painter.drawLine(x_left + panel_w, y_left + 45, x_left + panel_w, y_left + 45 - cl)

        hava_derece = getattr(self, "hava_durumu_temp", "22°C")
        hava_durum = getattr(self, "hava_durumu_text", "İSTANBUL")

        painter.setFont(QFont("Consolas", 7, QFont.Bold))
        painter.setPen(QPen(main_color))
        painter.drawText(x_left + 5, y_left + 12, "WEATHER")

        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        painter.setPen(QPen(QColor(255, 195, 0)))
        painter.drawText(x_left, y_left + 26, panel_w, 15, Qt.AlignCenter, hava_derece)

        painter.setFont(QFont("Consolas", 6, QFont.Bold))
        painter.setPen(QPen(QColor(180, 210, 255)))
        painter.drawText(x_left, y_left + 38, panel_w, 10, Qt.AlignCenter, hava_durum)

import re

# ===================================================
# 4. YARDIMCI VE SES FONKSİYONLARI
# ===================================================
hud = None
class AsistanDurumu:
    def __init__(self):
        self.force_listen_flag = False
        self.active_call_detected = False
        self.call_platform = ""
        self.caller_name = ""
        self.gece_isigi_sorusu_bekleniyor = False
        # Sesli mesaj yazma akışı için:
        self.mesaj_akisi_durumu = None  # None | "uygulama_bekleniyor" | "icerik_bekleniyor" | "gonder_bekleniyor"
        self.mesaj_akisi_kisi = ""
        self.mesaj_akisi_uygulama = ""
        # Gelen mesaja yanıt akışı için:
        self.yanit_sorusu_bekleniyor = False
        self.yanit_uygulama = ""
        self.yanit_kisi = ""
        # Çok adımlı bir akış (mesaj yazma, gece ışığı sorusu, arama kabul/red) sürerken
        # bildirim duyurularının araya girmemesi için:
        self.mesgul = False

durum = AsistanDurumu()

SES_KILIDI = threading.Lock()

def temel_konus(metin, sesli=True):
    print(f"\n{ASISTAN_ADI.upper()}: {metin}")
    if hud:
        if hud.status_mode != "CALL":
            ui_bridge.status_signal.emit("SPEAKING", metin)
        ui_bridge.chat_append_signal.emit(ASISTAN_ADI.upper(), metin)

    if not sesli:
        if hud and hud.status_mode != "CALL":
            ui_bridge.status_signal.emit("LISTENING", "SYSTEM READY // LISTENING...")
        return

    # EMOJİ TEMİZLEME MOTORU (Hatasız Unicode Formatı)
    emoji_deseni = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # İfadeler
        "\U0001F300-\U0001F5FF"  # Semboller & Nesneler
        "\U0001F680-\U0001F6FF"  # Ulaşım
        "\U0001F1E0-\U0001F1FF"  # Bayraklar
        "\u2702-\u27B0"          # Semboller (4 Hızlı Unicode)
        "\u24C2-\u2500"
        "]+", 
        flags=re.UNICODE
    )
    ses_metni = emoji_deseni.sub('', metin).strip()

    # Eğer emojiler temizlendikten sonra okunacak metin kalmadıysa çık
    if not ses_metni:
        return

    # Dosya yolunu Masaüstü yerine Windows Temp klasörüne yönlendiriyoruz
    temp_dir = tempfile.gettempdir()
    dosya = os.path.join(temp_dir, f"temp_voice_{int(time.time()*1000)}.mp3")

    async def ses_üret():
        communicate = edge_tts.Communicate(ses_metni, "tr-TR-AhmetNeural")
        await communicate.save(dosya)

    try:
        asyncio.run(ses_üret())
        with SES_KILIDI:
            pygame.mixer.init()
            pygame.mixer.music.load(dosya)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.music.unload()
            pygame.mixer.quit()

        # Oynatma tamamlanınca geçici dosyayı temizle
        if os.path.exists(dosya):
            os.remove(dosya)
    except Exception as e:
        print(f"Ses hatası: {e}")

    if hud and hud.status_mode != "CALL":
        ui_bridge.status_signal.emit("LISTENING", "SYSTEM READY // LISTENING...")

import io
import sounddevice as sd
import numpy as np
import wave
import os

def _cevap_dinle(toplam_sure_saniye=8, parca_sure=3, hassas=False):
    """Belirtilen toplam süre içinde kullanıcıdan sesli bir cevap gelmesini bekler,
    gelen ilk anlamlı metni döndürür. Süre dolarsa None döner.
    hassas=True: daha yavaş ama daha doğru bir Whisper modeli kullanır (mesaj içeriği gibi
    doğruluğun hızdan önemli olduğu yerlerde)."""
    baslangic = time.time()
    while time.time() - baslangic < toplam_sure_saniye:
        cevap = groq_whisper_dinle(max_sure=parca_sure, hassas=hassas)
        if cevap and cevap.strip():
            return cevap.strip()
    return None

def groq_whisper_dinle(max_sure=10.0, sessizlik_limit=0.6, rms_esik=70, hassas=False):
    """
    Dinamik Ses Algılama (VAD) ve RAM-üzerinden Ultra Hızlı Whisper Kaydı.
    Konuşma bittiği an (sessizlik_limit dolunca) kaydı anında keser.
    """
    try:
        sample_rate = 16000
        chunk_duration = 0.1  # 100ms'lik bloklar halinde dinle
        chunk_samples = int(sample_rate * chunk_duration)
        
        frames = []
        sessiz_sure = 0.0
        konusma_basladi = False
        toplam_sure = 0.0

        # Dinamik Kayıt Akışı
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
            while toplam_sure < max_sure:
                data, overflow = stream.read(chunk_samples)
                frames.append(data)
                toplam_sure += chunk_duration

                # RMS Ses Şiddeti Hesapla
                audio_float = data.astype(np.float32)
                rms = np.sqrt(np.mean(audio_float**2))

                if rms > rms_esik:
                    konusma_basladi = True
                    sessiz_sure = 0.0  # Konuşma devam ediyorsa sessizlik sayacını sıfırla
                else:
                    if konusma_basladi:
                        sessiz_sure += chunk_duration
                        # Konuşma başladıktan sonra belirlediğimiz süre kadar sessizlik olursa KAYDI BİTİR
                        if sessiz_sure >= sessizlik_limit:
                            break
            
        if not konusma_basladi or len(frames) == 0:
            return None

        # Ses verilerini birleştir
        audio_bytes = np.concatenate(frames, axis=0).tobytes()

        # Disk yerine doğrudan RAM (Memory) üzerinde WAV buffer oluştur (Hız kazandırır)
        wav_buffer = io.BytesIO()
        wav_buffer.name = "audio.wav"
        
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)
            
        wav_buffer.seek(0)

        # Groq Whisper API - Doğrudan RAM üzerindeki veriyi gönder
        transcription = groq_client.audio.transcriptions.create(
            file=(wav_buffer.name, wav_buffer.read()),
            model="whisper-large-v3" if hassas else "whisper-large-v3-turbo",
            language="tr",
            temperature=0.0
        )

        metin = transcription.text.strip()
        metin_lower = metin.lower()

        # Halüsinasyon Filtresi
        yasakli_halusinasyonlar = [
            "altyazı", "m.k", "izlediğiniz için", "teşekkürler", "oh", "ister", 
            "abone", "beğenmeyi", "yayınlanan", "altyazılar", "seslendiren"
        ]
        
        if any(metin_lower == y or metin_lower.startswith(y) for y in yasakli_halusinasyonlar):
            return None
            
        if len(metin) < 2:
            return None

        return metin

    except Exception as e:
        print(f"Whisper Hatası: {e}")
        return None

import time
import datetime
import psutil
from PyQt5.QtCore import QThread, pyqtSignal

class OtonomInisiyatifThread(QThread):
    # Arayüze veya ses motoruna mesaj göndermek için sinyal
    inisiyatif_sinyali = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.son_cpu_uyari_zamani = 0
        self.gece_uyarisi_yapildi = False
# Otonom İnisiyatif Motorunu Başlat
        self.otonom_thread = OtonomInisiyatifThread()
        self.otonom_thread.inisiyatif_sinyali.connect(self.temel_konus)  # Veya sesli yanıt fonksiyonun
        self.otonom_thread.start()

    def run(self):
        while self.running:
            try:
                su_an = datetime.datetime.now()
                simdiki_zaman = time.time()

                # 1. SİSTEM YÜKÜ KONTROLÜ (Aşırı İşlemci / RAM Kullanımı)
                cpu_yuzde = psutil.cpu_percent(interval=1)
                ram_yuzde = psutil.virtual_memory().percent

                # Eğer CPU veya RAM %88'in üzerindeyse ve son uyarının üzerinden 10 dakika geçtiyse
                if (cpu_yuzde > 88 or ram_yuzde > 90) and (simdiki_zaman - self.son_cpu_uyari_zamani > 600):
                    self.inisiyatif_sinyali.emit(
                        f"Efendim, sistem kaynakları biraz zorlanıyor. İşlemci kullanımı %{int(cpu_yuzde)}, "
                        f"bellek kullanımı ise %{int(ram_yuzde)} seviyesinde. Arka planı rahatlatmamı ister misiniz?"
                    )
                    self.son_cpu_uyari_zamani = simdiki_zaman

                # 2. GECE MODU VE MOLA UYARISI (Gece 01:00 - 04:00 arası)
                if su_an.hour in [1, 2, 3] and not self.gece_uyarisi_yapildi:
                    self.inisiyatif_sinyali.emit(
                        "Efendim, saat epey geç oldu. Geç saatlere kadar çalıştığınızı fark ettim, "
                        "göz sağlığınız için dinlenmenizi veya ekranı gece moduna almamı ister misiniz?"
                    )
                    self.gece_uyarisi_yapildi = True

                # Gün değiştiğinde gece uyarısını sıfırla
                if su_an.hour == 12:
                    self.gece_uyarisi_yapildi = False

            except Exception as e:
                print(f"Otonom motor hatası: {e}")

            # Her 30 saniyede bir kontrolleri tekrarla
            time.sleep(30)

    def stop(self):
        self.running = False

def ses_degistir(islem, miktar=5):
    if islem == "yukselt":
        for _ in range(miktar): pyautogui.press("volumeup")
    elif islem == "dusur":
        for _ in range(miktar): pyautogui.press("volumedown")
    elif islem == "sessiz":
        pyautogui.press("volumemute")

# Müzik/Sistem sesini geçici kısıp eski haline getirme
eski_ses_seviyesi = None

def arka_plan_sesini_kis():
    # Klavye simülasyonu ile sesi hızlıca 10 kademe düşürür
    for _ in range(10):
        pyautogui.press("volumedown")

def arka_plan_sesini_ac():
    # Sesi tekrar 10 kademe eski seviyesine yükseltir
    for _ in range(10):
        pyautogui.press("volumeup")

def hava_durumu_al(sehir="Istanbul"):
    try:
        # Ücretsiz ve anahtarsız open-meteo API kullanımı
        url = f"https://api.open-meteo.com/v1/forecast?latitude=41.0082&longitude=28.9784&current_weather=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            temp = round(data["current_weather"]["temperature"])
            return f"{temp}°C ISTANBUL"
    except Exception:
        return "22°C ISTANBUL"  # Bağlantı koparsa varsayılan gösterge

import psutil

GECE_ISIGI_KAYIT_YOLU = (
    r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current"
    r"\default$windows.data.bluelightreduction.bluelightreductionstate"
    r"\windows.data.bluelightreduction.bluelightreductionstate"
)

def _gece_isigi_veri_oku():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, GECE_ISIGI_KAYIT_YOLU, 0, winreg.KEY_READ)
    try:
        data, _ = winreg.QueryValueEx(key, "Data")
        return bytearray(data)
    finally:
        winreg.CloseKey(key)

def _gece_isigi_veri_yaz(data):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, GECE_ISIGI_KAYIT_YOLU, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, "Data", 0, winreg.REG_BINARY, bytes(data))
    finally:
        winreg.CloseKey(key)

def gece_isigi_acik_mi():
    try:
        data = _gece_isigi_veri_oku()
        return data[18] == 0x15
    except Exception as e:
        print(f"Gece ışığı durumu okunamadı: {e}")
        return None

def gece_isigi_ayarla(ac=True):
    """Windows Gece Işığı'nı açar/kapatır. Kayıt defterindeki ikili veriyi
    nightlight-cli projesindeki mantıkla değiştirir."""
    try:
        mevcut = gece_isigi_acik_mi()
        if mevcut is None:
            return False
        if mevcut == ac:
            return True  # zaten istenen durumda

        data = _gece_isigi_veri_oku()

        if mevcut:  # açık -> kapatılacak
            yeni = bytearray(41)
            yeni[0:22] = data[0:22]
            yeni[23:23 + (43 - 25)] = data[25:43]
            yeni[18] = 0x13
        else:  # kapalı -> açılacak
            yeni = bytearray(43)
            yeni[0:22] = data[0:22]
            yeni[25:25 + (41 - 23)] = data[23:41]
            yeni[18] = 0x15
            yeni[23] = 0x10
            yeni[24] = 0x00

        # Zaman damgasını ilerlet (Windows'un değişikliği kabul etmesi için gerekli)
        for i in range(10, 15):
            if yeni[i] != 0xFF:
                yeni[i] += 1
                break

        _gece_isigi_veri_yaz(yeni)
        return True
    except Exception as e:
        print(f"Gece ışığı ayarlanamadı: {e}")
        return False

BILDIRIM_IZIN_VERILDI = False
TAKIP_EDILECEK_BILDIRIM_UYGULAMALARI = ["whatsapp", "teams", "telefon", "your phone", "phone link", "bağlantısı", "instagram"]
BILDIRIM_HARIC_TUTMA_KELIMELERI = [
    "pil düzeyi", "pil seviyesi", "şarj", "batarya", "battery",
    "indirim", "kampanya", "fırsat", "% indirim", "sms ret",
    "youtube", "abone", "yayında", "izlenme",
]
gorulen_bildirim_icerikleri = {}  # id -> son görülen içerik metni (güncellenen bildirimleri de yakalamak için)
bildirim_ilk_tarama_yapildi = False

def bildirim_dinleyici_izin_al():
    """Windows'tan bildirimleri okuma izni ister. Program açılırken bir kere çağrılır,
    Windows ekrana bir izin penceresi çıkarır (kullanıcı kabul etmeli)."""
    global BILDIRIM_IZIN_VERILDI
    if not WINSDK_MEVCUT:
        return False
    try:
        listener = unlm.UserNotificationListener.current

        async def _izin_iste():
            return await listener.request_access_async()

        access_status = asyncio.run(_izin_iste())
        BILDIRIM_IZIN_VERILDI = (access_status == unlm.UserNotificationListenerAccessStatus.ALLOWED)
        if BILDIRIM_IZIN_VERILDI:
            print("Bildirim dinleme izni verildi.")
        else:
            print(f"Bildirim dinleme izni verilmedi: {access_status}. Ayarlar > Sistem > Bildirimler > Bildirim erişimi'nden manuel izin verebilirsin.")
        return BILDIRIM_IZIN_VERILDI
    except Exception as e:
        print(f"Bildirim izni alınırken hata: {e}")
        return False

def yeni_bildirimleri_kontrol_et():
    """Şu an Windows'ta bekleyen bildirimlerden yeni olanları VEYA içeriği değişmiş
    olanları (örn. aynı konuşmaya art arda gelen mesajlarla güncellenen bildirimler)
    (uygulama_adi, baslik, icerik) üçlüleri olarak döndürür."""
    global gorulen_bildirim_icerikleri, bildirim_ilk_tarama_yapildi
    if not WINSDK_MEVCUT or not BILDIRIM_IZIN_VERILDI:
        return []

    yeni = []
    try:
        listener = unlm.UserNotificationListener.current

        async def _bildirimleri_getir():
            return await listener.get_notifications_async(un.NotificationKinds.TOAST)

        bildirimler = asyncio.run(_bildirimleri_getir())
        guncel_idler = set()

        for bildirim in bildirimler:
            guncel_idler.add(bildirim.id)

            uygulama_adi = (bildirim.app_info.display_info.display_name or "").lower()
            if not any(k in uygulama_adi for k in TAKIP_EDILECEK_BILDIRIM_UYGULAMALARI):
                continue

            baslik, icerik = "", ""
            try:
                binding = bildirim.notification.visual.get_binding(un.KnownNotificationBindings.toast_generic)
                metinler = binding.get_text_elements()
                if len(metinler) > 0:
                    baslik = metinler[0].text
                if len(metinler) > 1:
                    icerik = " ".join(m.text for m in metinler[1:])
            except Exception as e:
                print(f"Bildirim içeriği okunamadı: {e}")

            birlesik_metin = f"{baslik} {icerik}".lower()

            # İLK TARAMA: program yeni açıldı, ekranda duran eski bildirimleri
            # sadece "görüldü" olarak kaydet, seslendirme.
            if not bildirim_ilk_tarama_yapildi:
                gorulen_bildirim_icerikleri[bildirim.id] = birlesik_metin
                continue

            onceki_icerik = gorulen_bildirim_icerikleri.get(bildirim.id)
            if onceki_icerik == birlesik_metin:
                continue  # bu bildirimi bu haliyle zaten duyurduk

            gorulen_bildirim_icerikleri[bildirim.id] = birlesik_metin

            # İçerik bazlı hariç tutma (pil uyarısı, reklam, YouTube vb. sistem/spam bildirimleri)
            if any(k in birlesik_metin for k in BILDIRIM_HARIC_TUTMA_KELIMELERI):
                continue

            yeni.append((bildirim.app_info.display_info.display_name, baslik, icerik))

        if not bildirim_ilk_tarama_yapildi:
            bildirim_ilk_tarama_yapildi = True

        # Artık ekranda olmayan (kapanmış/okunmuş) bildirimleri kayıttan temizle
        for eski_id in list(gorulen_bildirim_icerikleri.keys()):
            if eski_id not in guncel_idler:
                del gorulen_bildirim_icerikleri[eski_id]

    except Exception as e:
        print(f"Bildirim listesi okuma hatası: {e}")

    return yeni

def uygulama_kapat(uygulama_adi):
    """Verilen uygulama adına ait çalışan süreçleri sonlandırır."""
    bulundu = False
    uygulama_adi = uygulama_adi.lower().strip()
    
    # Sık kullanılan uygulamaların işlem adları haritası
    uygulama_haritasi = {
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "chrome": "chrome.exe",
        "tarayıcı": "chrome.exe",
        "not defteri": "notepad.exe",
        "oyun": "solitaire.exe", # Örnek
        "riot": "RiotClientServices.exe",
        "riotu": "RiotClientServices.exe",
        "valorant": "VALORANT.exe",
        "league of legends": "LeagueClient.exe",
        "netflix": "Netflix.exe",
        "steam": "steam.exe",
        "whatsapp": "WhatsApp.exe",
        "teams": "ms-teams.exe"
    }
    
    hedef_exe = uygulama_haritasi.get(uygulama_adi, f"{uygulama_adi}.exe")
    
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == hedef_exe.lower():
                proc.terminate()
                bulundu = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    return bulundu

def youtube_direkt_sarki_ac(sorgu):
    try:
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(sorgu)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(search_url, headers=headers, timeout=5)
        
        video_ids = re.findall(r"watch\?v=(\w{11})", response.text)
        if video_ids:
            direkt_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
            webbrowser.open(direkt_url)
            return True
        else:
            webbrowser.open(search_url)
            return False
    except Exception as e:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(sorgu)}")
        return False

def haber_ara(sorgu="Türkiye gündem"):
    """internette_ara'dan farklı olarak DDGS'nin HABER-özel arama uç noktasını kullanır.
    Bu, genel web aramasının aksine (ki genelde haber portalının tanıtım metnini bulur)
    gerçek başlık + kaynak + kısa özet döndürür."""
    try:
        sonuclar = []
        with DDGS() as ddgs:
            haber_gen = ddgs.news(sorgu, region='tr-tr', max_results=6, timelimit='d')
            if haber_gen:
                for h in haber_gen:
                    baslik = h.get('title', '')
                    ozet = h.get('body', '')
                    kaynak = h.get('source', '')
                    if baslik:
                        sonuclar.append(f"- {baslik} ({kaynak}): {ozet}")
        return "\n".join(sonuclar) if sonuclar else ""
    except Exception as e:
        # "No results found" gibi durumlar normaldir (dar bir sorguda haber çıkmayabilir),
        # bu yüzden sessizce boş döndürüyoruz - üst katman zaten genel habere düşecek.
        return ""

def internette_ara(sorgu):
    try:
        results = []
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(sorgu, region='tr-tr', max_results=5)
            if ddgs_gen:
                for r in ddgs_gen:
                    if isinstance(r, dict):
                        results.append(r.get('body', '') or r.get('title', ''))
                    elif hasattr(r, 'body'):
                        results.append(r.body)
                    else:
                        results.append(str(r))
        return " ".join(results) if results else ""
    except Exception as e:
        print(f"Arama hatası: {e}")
        return ""

# Hafıza Veritabanı Bağlantısı
def hafiza_baglantisi():
    conn = sqlite3.connect("temel_hafiza.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hafiza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anahtar TEXT UNIQUE,
            deger TEXT
        )
    """)
    conn.commit()
    return conn

# Bilgi Kaydetme
def hafizaya_yaz(anahtar, deger):
    conn = hafiza_baglantisi()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO hafiza (anahtar, deger) VALUES (?, ?)", (anahtar, deger))
    conn.commit()
    conn.close()

# Bilgi Okuma
def hafizadan_oku(anahtar):
    conn = hafiza_baglantisi()
    cursor = conn.cursor()
    cursor.execute("SELECT deger FROM hafiza WHERE anahtar = ?", (anahtar,))
    sonuc = cursor.fetchone()
    conn.close()
    return sonuc[0] if sonuc else None

import json
from google import genai
from PIL import Image, ImageDraw

def dinamik_butona_tikla(hedef_oge):
    try:
        key_dosyasi = "gemini_key.txt"
        if os.path.exists(key_dosyasi):
            with open(key_dosyasi, "r") as f:
                anahtar = f.read().strip().replace('"', '')
        else:
            return f"Hata: API anahtar dosyası ({key_dosyasi}) bulunamadı."
        
        # Yeni SDK Client kurulumu
        client = genai.Client(api_key=anahtar)
        
        # Ekran görüntüsü al
        ekran = pyautogui.screenshot()
        ekran.save("vision_temp.png")
        img = Image.open("vision_temp.png")
        
        prompt = f"""
        Bu ekran görüntüsünde '{hedef_oge}' ögesini/butonunu bul.
        Bana SADECE ve SADECE şu JSON formatında yanıt ver, başka hiçbir metin veya açıklama ekleme:
        {{"x_yuzde": 85, "y_yuzde": 90}}
        """
        
        # Güncel model adı
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[prompt, img]
        )
        
        temiz_cevap = response.text.strip().replace("```json", "").replace("```", "").strip()
        veri = json.loads(temiz_cevap)
        
        ekran_w, ekran_h = pyautogui.size()
        target_x = int((veri["x_yuzde"] / 100) * ekran_w)
        target_y = int((veri["y_yuzde"] / 100) * ekran_h)
        
        pyautogui.click(target_x, target_y)
        return f"Ekranda '{hedef_oge}' bulundu ve tıklandı."
    except Exception as e:
        return f"Öge ekranda tespit edilemedi veya hata oluştu: {e}"

def uygulama_veya_oyun_ac(isim):
    isim = isim.lower().strip()

    for oy_adi, app_id in STEAM_OYUNLARI.items():
        if oy_adi in isim:
            os.system(f"start steam://rungameid/{app_id}")
            return True

    apps = {
        "opera gx": "start launcher.exe", "opera": "start launcher.exe",
        "steam": "start steam:", "teams": "start msteams:",
        "discord": "start discord:", "spotify": "start spotify:",
        "whatsapp": "start whatsapp:",
        "chrome": "start chrome", "edge": "start msedge",
        "not defteri": "start notepad", "hesap makinesi": "start calc",
        "görev yöneticisi": "start taskmgr", "paint": "start mspaint", "cmd": "start cmd"
    }

    if "opera" in isim:
        opera_path = os.path.expanduser("~") + r"\AppData\Local\Programs\Opera GX\launcher.exe"
        if os.path.exists(opera_path):
            os.system(f'"{opera_path}"')
            return True

    for key, command in apps.items():
        if key in isim:
            os.system(command)
            return True

    # Yukarıdakilerde bulunamadıysa masaüstü kısayolu (.lnk) olarak dene
    # (Instagram, Netflix, CapCut gibi URI protokolü olmayan/PWA uygulamalar için)
    masaustu_kisayollari = {
        "discord": "Discord.lnk", "teams": "Microsoft Teams.lnk",
        "microsoft teams": "Microsoft Teams.lnk", "spotify": "Spotify.lnk",
        "skype": "Skype.lnk", "whatsapp": "WhatsApp.lnk",
        "prime video": "Prime Video.lnk", "prime": "Prime Video.lnk",
        "instagram": "Instagram.lnk", "netflix": "Netflix.lnk",
        "zoom": "ZoomInstaller.lnk", "capcut": "CapCut.lnk",
    }
    masaustu_yolu = os.path.join(os.path.expanduser("~"), "Desktop")
    for key, kisayol_adi in masaustu_kisayollari.items():
        if key in isim:
            dosya_yolu = os.path.join(masaustu_yolu, kisayol_adi)
            if os.path.exists(dosya_yolu):
                try:
                    os.startfile(dosya_yolu)
                    return True
                except Exception as e:
                    print(f"Masaüstü kısayolu ile açma hatası: {e}")

    return False

spotify_client = None

def spotify_baglan():
    """Spotify istemcisini bir kere kurar (lazy init). İlk çağrıda tarayıcıdan bir kerelik izin ister,
    sonrasında yerel bir önbellek dosyasında token'ı hatırlar."""
    global spotify_client
    if not SPOTIPY_MEVCUT:
        return None
    if spotify_client is None:
        try:
            spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
                scope="user-read-currently-playing user-read-playback-state"
            ))
        except Exception as e:
            print(f"Spotify bağlantı hatası: {e}")
            return None
    return spotify_client

def spotify_su_an_ne_caliyor():
    sp = spotify_baglan()
    if not sp:
        return "Spotify'a bağlanamadım. Kurulum ayarlarını (Client ID/Secret) kontrol eder misiniz?"
    try:
        veri = sp.current_user_playing_track()
        if not veri or not veri.get("item"):
            return "Şu an Spotify'da bir şey çalmıyor."
        sarki = veri["item"]["name"]
        sanatcilar = ", ".join(s["name"] for s in veri["item"]["artists"])
        calisiyor_mu = veri.get("is_playing", False)
        durum = "çalıyor" if calisiyor_mu else "duraklatılmış durumda"
        return f"{sanatcilar} - {sarki}, şu an {durum}."
    except Exception as e:
        print(f"Spotify okuma hatası: {e}")
        return "Şu an çalan şarkıyı öğrenemedim."

def _tomtom_koordinat_bul(yer_adi):
    """Bir adres/yer ismini (enlem, boylam) koordinatına çevirir. Bulamazsa None döner."""
    if not TOMTOM_API_KEY:
        return None
    try:
        url = f"https://api.tomtom.com/search/2/geocode/{requests.utils.quote(yer_adi)}.json"
        params = {"key": TOMTOM_API_KEY, "limit": 1, "countrySet": "TR"}
        res = requests.get(url, params=params, timeout=8).json()
        sonuclar = res.get("results", [])
        if not sonuclar:
            return None
        konum = sonuclar[0]["position"]
        return konum["lat"], konum["lon"]
    except Exception as e:
        print(f"TomTom geocoder hatası: {e}")
        return None

def trafik_durumu_sor(baslangic, bitis):
    """İki nokta arasındaki güncel trafik durumuna göre tahmini süre ve mesafeyi bildirir."""
    if not TOMTOM_API_KEY:
        return "Trafik özelliği için TomTom API anahtarı henüz ayarlı değil efendim."

    baslangic_koordinat = _tomtom_koordinat_bul(baslangic)
    bitis_koordinat = _tomtom_koordinat_bul(bitis)

    if not baslangic_koordinat:
        return f"{baslangic} konumunu bulamadım efendim."
    if not bitis_koordinat:
        return f"{bitis} konumunu bulamadım efendim."

    try:
        enlem1, boylam1 = baslangic_koordinat
        enlem2, boylam2 = bitis_koordinat
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{enlem1},{boylam1}:{enlem2},{boylam2}/json"
        params = {"key": TOMTOM_API_KEY, "traffic": "true"}
        res = requests.get(url, params=params, timeout=10)
        veri = res.json()

        ozet = veri["routes"][0]["summary"]
        mesafe_km = ozet["lengthInMeters"] / 1000
        sure_dk = ozet["travelTimeInSeconds"] / 60

        return (f"{baslangic.capitalize()}'den {bitis.capitalize()}'e araçla yaklaşık "
                f"{mesafe_km:.0f} kilometre, şu anki trafik durumuna göre tahmini "
                f"{sure_dk:.0f} dakika sürüyor.")
    except Exception as e:
        print(f"TomTom router hatası: {e}")
        return "Trafik durumunu hesaplarken bir sorun oluştu, efendim."

def hava_durumu_getir(sehir="Istanbul"):
    try:
        sehir_temiz = sehir.lower().replace("’", "'")
        for ek in ["'de", "'da", "'te", "'ta", "de", "da", "te", "ta"]:
            if sehir_temiz.endswith(ek): sehir_temiz = sehir_temiz[:-len(ek)]
        
        char_map = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
        for tr, en in char_map.items(): sehir_temiz = sehir_temiz.replace(tr, en)
        sehir_temiz = sehir_temiz.strip() or "Istanbul"

        url = f"https://wttr.in/{sehir_temiz}?format=j1"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            su_an = data['current_condition'][0]
            sicaklik = su_an['temp_C']
            durum_en = su_an['weatherDesc'][0]['value'].strip().lower()

            durum_map = {
                "clear": "açık ve güneşli", "sunny": "güneşli", "partly cloudy": "parçalı bulutlu",
                "cloudy": "bulutlu", "overcast": "çok bulutlu", "mist": "sisli", "fog": "sisli",
                "light rain": "hafif yağmurlu", "heavy rain": "şiddetli yağmurlu"
            }
            if durum_en in durum_map:
                durum_tr = durum_map[durum_en]
            else:
                # Sözlükte olmayan bir ifade gelirse İngilizce kalmasın, hızlıca çevir
                durum_tr = _hizli_cevir(durum_en, hedef="tr")
            return f"{sehir_temiz.capitalize()} için hava şu an {sicaklik} derece ve {durum_tr}."
        return "Hava durumu bilgisi alınamadı."
    except Exception as e:
        return "Hava durumu sunucusuna bağlanırken hata oluştu."

def zamanlayici_baslat(dakika, hatirlatma_metni=""):
    toplam_saniye = int(dakika * 60)
    time.sleep(toplam_saniye)
    try:
        for _ in range(6):
            winsound.Beep(1000, 300)
            time.sleep(0.1)
    except Exception:
        pass
    mesaj = f"Süreniz doldu efendim! {hatirlatma_metni}".strip()
    temel_konus(mesaj, sesli=True)
    return f"{dakika} dakikalık zamanlayıcı bitti."

def _vision_tamamla(mesajlar, max_tokens=20):
    """groq_client üzerinden vision tamamlama isteği yapar; dakikalık token limitine (429)
    takılırsa kısa bir bekleyip bir kez daha dener - çoğu zaman limit birkaç saniyede açılır."""
    for deneme in range(2):
        try:
            return groq_client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=mesajlar,
                temperature=0.1,
                max_tokens=max_tokens,
                reasoning_effort="none"
            )
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                print("Vision rate limit hatası, kısa bekleyip tekrar deneniyor...")
                time.sleep(2)
                continue
            raise
    # Son deneme de patlarsa hatayı çağırana bırak (dış try/except zaten yakalıyor)
    return groq_client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=mesajlar,
        temperature=0.1,
        max_tokens=max_tokens,
        reasoning_effort="none"
    )

def _grid_ciz(resim_yolu, satir=8, sutun=8):
    """Görüntünün üzerine etiketli bir ızgara (A1, B3 gibi) çizer ve yeni dosya yolunu,
    her hücrenin piksel boyutunu döndürür. Modelin ondalık yüzde tahmin etmesi yerine
    bir hücre etiketi söylemesi, konum isabetini belirgin şekilde artırır."""
    img = Image.open(resim_yolu).convert("RGB")
    draw = ImageDraw.Draw(img)
    genislik, yukseklik = img.size
    hucre_g = genislik / sutun
    hucre_y = yukseklik / satir

    for i in range(1, sutun):
        x = int(i * hucre_g)
        draw.line([(x, 0), (x, yukseklik)], fill=(255, 0, 0), width=2)
    for j in range(1, satir):
        y = int(j * hucre_y)
        draw.line([(0, y), (genislik, y)], fill=(255, 0, 0), width=2)

    for i in range(sutun):
        for j in range(satir):
            etiket = f"{chr(65 + i)}{j + 1}"
            x = int(i * hucre_g) + 4
            y = int(j * hucre_y) + 4
            draw.rectangle([x - 2, y - 2, x + 22, y + 14], fill=(255, 255, 255))
            draw.text((x, y), etiket, fill=(255, 0, 0))

    yeni_yol = resim_yolu.rsplit(".", 1)[0] + "_grid.png"
    img.save(yeni_yol)
    return yeni_yol, hucre_g, hucre_y

def _grid_etiketini_coz(etiket, hucre_g, hucre_y):
    """'C4' gibi bir ızgara etiketini, o hücrenin merkez piksel koordinatına çevirir."""
    eslesme = re.match(r'([A-Za-z])(\d+)', etiket.strip())
    if not eslesme:
        return None
    sutun_harfi, satir_no = eslesme.group(1).upper(), int(eslesme.group(2))
    sutun_index = ord(sutun_harfi) - ord('A')
    satir_index = satir_no - 1
    merkez_x = int((sutun_index + 0.5) * hucre_g)
    merkez_y = int((satir_index + 0.5) * hucre_y)
    return merkez_x, merkez_y

def _tiklama_sonucunu_dogrula(hedef):
    """Tıklamadan sonra yeni bir ekran görüntüsü alıp gerçekten ne olduğunu vision'a sorar.
    (basarili: bool, mesaj: str) döner - başarılıysa mesaj sadece bilgi amaçlıdır, konuşulması
    gerekmez; başarısızsa mesaj kullanıcıya söylenmesi gereken açıklamadır."""
    temp_img = os.path.join(tempfile.gettempdir(), f"temel_dogrulama_{int(time.time()*1000)}.png")
    try:
        pyautogui.screenshot(temp_img)
        with open(temp_img, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')

        completion = _vision_tamamla([{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    f"Az önce ekranda '{hedef}' üzerine tıklandı. Bu ekran görüntüsüne bakarak "
                    "sonucun doğru olup olmadığını değerlendir. Eğer beklendiği gibi doğru bir "
                    "şey olduysa TAM OLARAK sadece 'EVET' yaz, başka hiçbir şey ekleme. Eğer "
                    "yanlış/beklenmeyen bir şey olduysa 'HAYIR: ' ile başlayıp SADECE TÜRKÇE ve "
                    "EN FAZLA 1 KISA CÜMLEYLE ne olduğunu anlat. Düşünme adımı yazma."
                )},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
            ]
        }], max_tokens=100)
        aciklama = completion.choices[0].message.content.strip()
        if "</think>" in aciklama:
            aciklama = aciklama.split("</think>")[-1].strip()

        if aciklama.upper().startswith("EVET"):
            return True, f"{hedef} bulundu ve tıklandı."
        else:
            return False, aciklama.split(":", 1)[-1].strip() if ":" in aciklama else aciklama
    except Exception as e:
        print(f"Tıklama doğrulama hatası: {e}")
        return True, f"{hedef} bulup tıkladım ama sonucu doğrulayamadım."
    finally:
        if os.path.exists(temp_img):
            os.remove(temp_img)

def _hassas_konum_bul(hedef, kaba_x, kaba_y, genislik, yukseklik):
    """Kaba tahmin etrafında küçük bir bölge kırpıp büyüterek ikinci kez sorar; küçük ve net
    görüntüde model çok daha isabetli tahmin eder. Sorun olursa kaba tahmine geri döner."""
    tam_ekran_yolu = None
    kirpilmis_yol = None
    grid_yol = None
    try:
        kirpma_genislik = genislik // 4
        kirpma_yukseklik = yukseklik // 4

        sol = max(0, kaba_x - kirpma_genislik // 2)
        ust = max(0, kaba_y - kirpma_yukseklik // 2)
        sag = min(genislik, sol + kirpma_genislik)
        alt = min(yukseklik, ust + kirpma_yukseklik)

        tam_ekran_yolu = os.path.join(tempfile.gettempdir(), f"temel_full_{int(time.time()*1000)}.png")
        pyautogui.screenshot(tam_ekran_yolu)

        img = Image.open(tam_ekran_yolu)
        kirpilmis = img.crop((sol, ust, sag, alt))
        kirpilmis = kirpilmis.resize((kirpilmis.width * 3, kirpilmis.height * 3))

        kirpilmis_yol = os.path.join(tempfile.gettempdir(), f"temel_crop_{int(time.time()*1000)}.png")
        kirpilmis.save(kirpilmis_yol)

        grid_yol, hucre_g, hucre_y = _grid_ciz(kirpilmis_yol, satir=8, sutun=8)

        with open(grid_yol, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')

        completion = _vision_tamamla([{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    f"Bu, ekranın yakınlaştırılmış bir bölümü, üzerinde kırmızı çizgilerle bir "
                    "ızgara ve her hücrenin sol üst köşesinde bir etiket (A1, B3, C7 gibi) var. "
                    f"'{hedef}' burada görünüyor. TAM OLARAK şu formatta cevap ver, başka hiçbir "
                    "şey yazma: KONUM <hücre_etiketi> (öğenin TAM MERKEZİNİN içinde olduğu "
                    "hücrenin etiketi, örn: KONUM D5)."
                )},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
            ]
        }], max_tokens=20)
        cevap = completion.choices[0].message.content.strip()

        eslesme = re.search(r'([A-Za-z]\d+)', cevap)
        if eslesme:
            konum_hucre = _grid_etiketini_coz(eslesme.group(1), hucre_g, hucre_y)
            if konum_hucre:
                yerel_x, yerel_y = konum_hucre
                hassas_x = sol + int(yerel_x / 3)  # kırpılmış görüntü 3 kat büyütülmüştü
                hassas_y = ust + int(yerel_y / 3)
                return hassas_x, hassas_y
    except Exception as e:
        print(f"Hassas konum bulma hatası: {e}")
    finally:
        for dosya in (tam_ekran_yolu, kirpilmis_yol, grid_yol):
            if dosya and os.path.exists(dosya):
                os.remove(dosya)

    return kaba_x, kaba_y

def web_sitesi_ac(site_adi_veya_url):
    """Bir web sitesini varsayılan tarayıcıda açar. Kısa bilinen isimleri (youtube, google vb.)
    tam URL'e çevirir; zaten http(s):// ile başlıyorsa doğrudan kullanır."""
    bilinen_siteler = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "twitter": "https://twitter.com",
        "x": "https://twitter.com",
        "amazon": "https://www.amazon.com.tr",
        "ekşi": "https://eksisozluk.com",
        "eksisozluk": "https://eksisozluk.com",
        "instagram": "https://www.instagram.com",
        "netflix": "https://www.netflix.com",
    }
    site_temiz = site_adi_veya_url.strip().lower()

    if site_temiz.startswith("http://") or site_temiz.startswith("https://"):
        url = site_adi_veya_url.strip()
    elif site_temiz in bilinen_siteler:
        url = bilinen_siteler[site_temiz]
    else:
        # Bilinmeyen bir isimse basitçe .com ekleyip dene
        url = f"https://www.{site_temiz.replace(' ', '')}.com"

    try:
        webbrowser.open(url)
        return f"{site_adi_veya_url.capitalize()} tarayıcıda açılıyor."
    except Exception as e:
        print(f"Web sitesi açma hatası: {e}")
        return f"{site_adi_veya_url} açılamadı."

def ekranda_bul_ve_tikla(hedef, maks_deneme=5):
    """Ekranda 'hedef' tarifine uyan bir öğeyi (metin/buton/ikon) vision modeliyle arar;
    bulamazsa aşağı kaydırıp tekrar dener, bulunca üzerine tıklar. Deneysel bir özellik -
    vision modelinin konum tahmini her zaman piksel hassasiyetinde doğru olmayabilir."""
    genislik, yukseklik = pyautogui.size()

    for deneme in range(maks_deneme):
        temp_img = os.path.join(tempfile.gettempdir(), f"temel_vision_{int(time.time()*1000)}.png")
        grid_img = None
        try:
            pyautogui.screenshot(temp_img)
            grid_img, hucre_g, hucre_y = _grid_ciz(temp_img, satir=8, sutun=8)
            with open(grid_img, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')

            completion = _vision_tamamla([{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        f"Bu ekran görüntüsünün üzerinde kırmızı çizgilerle bir ızgara ve her "
                        "hücrenin sol üst köşesinde bir etiket (A1, B3, C7 gibi - harf sütunu, "
                        f"sayı satırı belirtir) var. '{hedef}' yazısını/ikonunu/butonunu arıyorum. "
                        "Eğer görüyorsan TAM OLARAK şu formatta cevap ver, başka hiçbir kelime "
                        "ekleme: BULUNDU <hücre_etiketi> (öğenin TAM MERKEZİNİN içinde olduğu "
                        "hücrenin etiketi, örn: BULUNDU D5). Görmüyorsan sadece BULUNAMADI yaz."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
                ]
            }], max_tokens=20)
            cevap = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Vision arama hatası: {e}")
            cevap = ""
        finally:
            for dosya in (temp_img, grid_img):
                if dosya and os.path.exists(dosya):
                    os.remove(dosya)

        eslesme = re.search(r'BULUNDU\s+([A-Za-z]\d+)', cevap)
        if eslesme:
            konum = _grid_etiketini_coz(eslesme.group(1), hucre_g, hucre_y)
            if konum:
                kaba_x, kaba_y = konum

                # 2. AŞAMA: kaba tahminin etrafını kırpıp büyüterek tekrar sor (isabeti artırır)
                hassas_x, hassas_y = _hassas_konum_bul(hedef, kaba_x, kaba_y, genislik, yukseklik)

                # PyAutoGUI'nin köşeye gidince devreye giren güvenlik durdurmasını (fail-safe) tetiklememek
                # için koordinatları ekranın tam kenarından/köşesinden birkaç piksel içeri çekiyoruz
                hassas_x = max(3, min(genislik - 4, hassas_x))
                hassas_y = max(3, min(yukseklik - 4, hassas_y))

                try:
                    pyautogui.moveTo(hassas_x, hassas_y, duration=0.3)
                    pyautogui.click()
                except pyautogui.FailSafeException:
                    print("PyAutoGUI fail-safe tetiklendi (köşeye çok yakın konum), tıklama atlandı.")
                    pyautogui.scroll(-600)
                    time.sleep(0.8)
                    continue

                time.sleep(1.2)  # tıklama sonrası ekranın güncellenmesi için kısa bekleme
                return _tiklama_sonucunu_dogrula(hedef)

        # Bulamadıysa aşağı kaydır ve tekrar dene
        pyautogui.scroll(-600)
        time.sleep(0.8)

    return False, f"{hedef} ekranda bulamadım, {maks_deneme} kez aradım efendim."

def ekran_goruntusu_al():
    try:
        masaustu = os.path.join(os.path.expanduser("~"), "Desktop")
        tarih_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dosya_yolu = os.path.join(masaustu, f"ekran_goruntusu_{tarih_str}.png")
        pyautogui.screenshot(dosya_yolu)
        return "Ekran görüntüsü Masaüstüne kaydedildi."
    except Exception as e:
        return f"Ekran görüntüsü alınırken hata oluştu: {e}"

def tema_degistir(tema_adi):
    if hud:
        if tema_adi in ["bordo", "kırmızı", "yeşil", "mor", "mavi", "rgb", "sarı", "neon"]:
            hud.set_theme(tema_adi)
            return f"Tema {tema_adi} olarak değiştirildi."
        else:
            return f"{tema_adi} adında bir tema bulunamadı."
    return "Arayüz yüklenemedi."

def ses_seviyesi_ayarla(seviye):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL, CoInitialize
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        # Windows COM arayüzünü güvenli şekilde başlat
        try:
            CoInitialize()
        except Exception:
            pass

        # Yeni ve eski PyCaw sürümleri için çift katmanlı erişim
        speakers = AudioUtilities.GetSpeakers()
        
        # Eğer yeni sürümse direkt EndpointVolume kullan
        if hasattr(speakers, 'EndpointVolume'):
            volume = speakers.EndpointVolume
        else:
            # Eski sürümse Activate ile dönüştür
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))

        target_vol = max(0.0, min(1.0, seviye / 100.0))
        volume.SetMasterVolumeLevelScalar(target_vol, None)
        return f"Ses seviyesi %{seviye} yapıldı."
    except Exception as e:
        return f"Ses ayarlanamadı: {e}"

def sistem_sesini_ayarla(yuzde):
    return ses_seviyesi_ayarla(yuzde)

def sistem_komutu_calistir(islem, parametre=""):
    try:
        if islem == "ses_kis":
            pyautogui.press("volumedown", presses=5)
            return "Ses kısıldı."
        elif islem == "ses_ac":
            pyautogui.press("volumeup", presses=5)
            return "Ses açıldı."
        elif islem == "sessiz":
            pyautogui.press("volumemute")
            return "Ses durumu değiştirildi."
        # BURAYI BÖYLE GÜNCELLE:
        elif islem == "medya_durdur_baslat":
            pyautogui.press("playpause")
            return "Müzik durduruldu veya başlatıldı."
        elif islem == "pencere_kapat":
            pyautogui.hotkey("alt", "f4")
            return "Aktif pencere kapatıldı."
        elif islem == "masaustu_goster":
            pyautogui.hotkey("win", "d")
            return "Masaüstü gösterildi."
        elif islem == "teams_arama_ac":
            ekran_genislik, ekran_yukseklik = pyautogui.size()
            buton_x = ekran_genislik - 100
            buton_y = ekran_yukseklik - 110
            pyautogui.click(buton_x, buton_y)
            return "Teams araması tıklandı ve yanıtlandı."

        elif islem == "teams_arama_kapat":
            ekran_genislik, ekran_yukseklik = pyautogui.size()
            buton_x = ekran_genislik - 45
            buton_y = ekran_yukseklik - 110
            pyautogui.click(buton_x, buton_y)
            return "Teams araması reddedildi."

        elif islem == "sonraki_sarki":
            pyautogui.press("nexttrack")
            return "Sonraki şarkıya geçildi."
        elif islem == "onceki_sarki":
            pyautogui.press("prevtrack")
            return "Önceki şarkıya geçildi."
        elif islem == "bilgisayari_kapat":
            dakika = int(parametre) if parametre.isdigit() else 0
            saniye = dakika * 60
            os.system(f"shutdown /s /t {saniye}")
            return f"Bilgisayar {dakika} dakika sonra kapatılmak üzere ayarlandı." if dakika > 0 else "Bilgisayar kapatılıyor."
        elif islem == "kapatmayi_iptal_et":
            os.system("shutdown /a")
            return "Kapatma işlemi iptal edildi."
    except Exception as e:
        return f"Sistem komutu çalıştırılamadı: {e}"

def gunun_ozeti_getir():
    ozet_metin = "Günaydın efendim! Günün özetini hazırladım, hemen paylaşıyorum: "
    try:
        hava = hava_durumu_getir("Istanbul")
        ozet_metin += f"Hava durumu: {hava} "
    except Exception:
        pass

    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        res = requests.get(url, timeout=5).json()
        usd = res['rates']['TRY']
        
        url_eur = "https://api.exchangerate-api.com/v4/latest/EUR"
        res_eur = requests.get(url_eur, timeout=5).json()
        eur = res_eur['rates']['TRY']
        
        ozet_metin += f"Piyasalarda Dolar {usd:.2f} Lira, Euro ise {eur:.2f} Lira seviyesinde. "
    except Exception:
        ozet_metin += "Döviz bilgisi alınamadı. "

    try:
        # Önce kullanıcının bilinen ilgi alanlarıyla (varsa) özel bir arama dene
        kullanici_bilgileri = KALICI_HAFIZA.get("kullanici_bilgileri", {})
        ilgi_alanlari = " ".join(str(v) for v in kullanici_bilgileri.values() if isinstance(v, str))

        haberler = haber_ara(ilgi_alanlari) if ilgi_alanlari else ""
        kisisellestirilmis = bool(haberler)

        # Kişisel arama boş döndüyse (bulunamadıysa) sessizce ülke geneli güncel haberlere geç
        if not haberler:
            haberler = haber_ara("Türkiye gündem son dakika")

        if haberler:
            if kisisellestirilmis:
                prompt = (
                    f"Aşağıda kullanıcının ilgi alanlarıyla (şunlar: {ilgi_alanlari}) ilgili gerçek haber "
                    "başlıkları ve kısa özetleri var. En önemli 2 tanesini seç ve her biri için 1 kısa "
                    "Türkçe cümle yaz. Tanıtım/reklam gibi görünen başlıkları ELEME:\n" + haberler
                )
            else:
                prompt = (
                    "Aşağıda Türkiye gündeminden gerçek haber başlıkları ve kısa özetleri var. "
                    "En önemli 2 tanesini seç ve her biri için 1 kısa Türkçe cümle yaz. "
                    "Tanıtım/reklam gibi görünen başlıkları ELEME:\n" + haberler
                )
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=GROQ_MODEL,
                temperature=0.2
            )
            ozet_haber = chat_completion.choices[0].message.content.strip()
            ozet_metin += f"Öne çıkan haberler ise şöyle: {ozet_haber}"
        else:
            ozet_metin += "Şu an güncel haber bulamadım."
    except Exception:
        ozet_metin += "Haber detayları alınamadı."

    return ozet_metin

def _hizli_cevir(metin, hedef="en"):
    """Küçük ve hızlı bir modelle metni çevirir. Çeviri başarısız olursa orijinal metni döner."""
    try:
        hedef_dil_adi = "English" if hedef == "en" else "Turkish"
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the given text into natural, fluent {hedef_dil_adi}. Output ONLY the translation, nothing else — no notes, no quotes."},
                {"role": "user", "content": metin}
            ],
            temperature=0.2
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Çeviri hatası: {e}")
        return metin

def yapay_zekaya_sor(soru):
    global SOHBET_HAFIZASI, KALICI_HAFIZA
    try:
        if hud: ui_bridge.status_signal.emit("THINKING", "THINKING...")

        # BİLGİSAYARIN ANLIK GERÇEK TARİHİ VE SAATİ
        simdi = datetime.datetime.now()
        bugun_str = simdi.strftime("%d %B %Y %A, Saat: %H:%M")

        # KALICI BİLGİLER VE GEÇMİŞ GÜNLERİN ÖZETİ (uzun vadeli hafıza)
        kullanici_bilgileri_str = json.dumps(KALICI_HAFIZA.get("kullanici_bilgileri", {}), ensure_ascii=False)
        son_ozetler = KALICI_HAFIZA.get("gunluk_ozetler", {})
        son_ozetler_str = "\n".join(f"- {tarih}: {ozet}" for tarih, ozet in sorted(son_ozetler.items())[-7:])

        # TEMEL - JARVIS KİŞİLİK VE ZEKA PROMPT'U
        SYSTEM_PROMPT = f"""
{KIMLIK_CUMLESI}
Kullanıcının kişisel, ultra hızlı, son derece zeki, pratik ve esprili yapay zekâ asistanısın.
Bugünün Tarihi ve Saati: {bugun_str}

Kullanıcı hakkında bildiğin ARKA PLAN bilgileri (SADECE doğrudan ilgili bir soru/durum olduğunda kullan,
aksi halde bunlardan hiç bahsetme, sohbete kendiliğinden sokma): {kullanici_bilgileri_str}
Son günlerin özeti (SADECE gerekirse hatırlatma amaçlı kullan, aksi halde hiç bahsetme):
{son_ozetler_str if son_ozetler_str else "(henüz özet yok)"}

KİŞİLİK VE TAVIR:
1. Tony Stark'ın Jarvis'i gibi son derece sadık, saygılı ama yeri geldiğinde ince espriler ve zeki taşlamalar yapan bir kişiliğe sahipsin.
2. Karadeniz pratikliğine ve samimiyetine sahipsin; Bordo-Mavi ruhunu taşırsın.
3. Hitaplarında Jarvis gibi doğal ol. Her cevabın başında kelime kuralı gibi "Efendim" deme. Sadece konuşmanın akışına uygun yerlerde (onay verirken, detay aktarırken veya soru sorarken) doğal biçimde "efendim" kullan. "Patron", "kaptan" gibi ifadeler kullanma.
4. CEVAP UZUNLUĞUNU KULLANICININ MESAJINA GÖRE AYARLA: Kullanıcı "naber", "selam", "iyi misin" gibi kısa/gündelik bir şey söylerse SEN DE kısa ve gündelik cevap ver (tek cümle, bazen tek kelime yeterlidir) - liste, öneri veya "size nasıl yardımcı olabilirim" gibi menü tarzı ekler YAPMA. İnisiyatif alma ve öneri sunma sadece kullanıcı gerçekten bir görev/karar bekliyorsa veya konu buna uygunsa geçerlidir, her mesajda değil.
5. Cevapların kısa, dinamik, sesli konuşmaya uygun ve akıcı olsun. Gereksiz doldurma cümlesi kurma.
6. Kullanıcı kendisiyle ilgili kalıcı bir bilgi paylaşırsa (ismi, mesleği, evcil hayvanı, favori bir şeyi, doğum günü gibi) bunu sohbetin akışını bozmadan kullanici_bilgisi_kaydet aracıyla kaydet.
7. ARKA PLAN bilgilerini (ilgi alanları, geçmiş özetler) SADECE kullanıcı o konuyu AÇIKÇA sorduğunda kullan. Kullanıcının mesajı belirsiz, anlaşılmaz, çok kısa ya da ses tanımadan kaynaklı bozuk/garip görünüyorsa, ASLA arka plan bilgisinden konu üretip cevap uydurma (örn. anlamsız bir girdiye spor sonucu, haber ya da ilgi alanıyla ilgili bir şey söyleme) - bunun yerine kısaca "Anlayamadım, tekrar eder misiniz?" gibi bir netleştirme sorusu sor.
8. Sohbet geçmişinde daha önce yapılmış bir işlem/görev (örn. birine mesaj gönderilmesi) geçiyorsa, kullanıcı o işlemi AÇIKÇA sormadığı sürece bunu yeni ve alakasız bir soruya kendiliğinden karıştırma veya örnek/hatırlatma olarak kullanma. Her soruyu, aksi belirtilmedikçe kendi bağlamında, önceki işlemlerden bağımsız değerlendir.
9. İSTİSNA: Kullanıcı az önce belirli bir konum/kişi/şey belirtmişse (örn. "Esenyurt'tan Üsküdar'a nasıl giderim") ve hemen ardından aynı konuda eksik bilgiyle bir takip sorusu sorarsa (örn. "trafik nasıl", "orada trafik var mı"), yeniden sormak yerine sohbet geçmişindeki o bilgiyi (Esenyurt/Üsküdar gibi) kullan - bu, 8. maddedeki "alakasız konuya karıştırma" kuralının istisnasıdır, çünkü burada konu zaten aynı ve doğrudan devam ediyor.
"""


        # EKRAN OKUMA / VISION TETİKLEYİCİSİ (KISA ÖZET + SORU SORMA)
        ekran_tetikleyicileri = ["ekranda ne var", "ekrana bak", "ekranı oku", "ekranımı analiz et", "bu resimde ne var"]
        if any(k in soru.lower() for k in ekran_tetikleyicileri):
            temp_img = os.path.join(tempfile.gettempdir(), "vision_screen.png")
            try:
                pyautogui.screenshot(temp_img)

                with open(temp_img, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

                completion = _vision_tamamla([
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"SADECE EKRANDA NE GÖRDÜĞÜNÜ MAKSİMUM 2 KISA CÜMLEYLE ÖZETLE. Düşünme adımlarını yazma. Soru: {soru}"
                            },
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                        ]
                    }
                ], max_tokens=200)

                cevap = completion.choices[0].message.content.strip()
                if "</think>" in cevap:
                    cevap = cevap.split("</think>")[-1].strip()

                # Soru ekleme ve takip moduna işaret koyma
                cevap += " Ekrandaki içerikle ilgili bir sorunuz veya yardımcı olmamı istediğiniz bir şey var mı?"
                return cevap
            except Exception as e:
                print(f"Ekran okuma (vision) hatası: {e}")
                return "Ekranı analiz ederken bir sorun yaşadım, tekrar dener misiniz?"
            finally:
                if os.path.exists(temp_img):
                    os.remove(temp_img)

        # NORMAL SOHBET / GENEL CEVAP BLOĞU
        # Güncel bilgi gerektiren konularda gerçek internet araması yap (Groq'un kendi web aramasına bağımlı değil)
        guncel_anahtar_kelimeler = [
            "son", "güncel", "yeni", "çıkan", "kimdir", "fiyatı", "fiyat", "bilet",
            "ücret", "kaç", "dolar", "euro", "sterlin", "altın", "kur", "borsa",
            "haber", "transfer", "ne kadar", "trabzonspor", "beşiktaş",
            "fenerbahçe", "galatasaray", "süper lig", "şampiyon", "kazandı", "puan durumu",
            "maç", "dün", "bugün", "oynandı"
        ]
        arama_ozeti = ""
        if any(k in soru.lower() for k in guncel_anahtar_kelimeler):
            bugun_tarih_str = datetime.datetime.now().strftime("%d %B %Y")
            arama_sorgusu = f"{soru} skor sonuç {bugun_tarih_str}"
            arama_ozeti = internette_ara(arama_sorgusu)
            print(f"[DEBUG] Arama sorgusu: {arama_sorgusu}")
            print(f"[DEBUG] Arama sonucu: {arama_ozeti[:300] if arama_ozeti else '(boş döndü)'}")

        # Groq modelleri İngilizce'de daha güçlü olduğu için soruyu İngilizce'ye çevirip gönderiyoruz
        soru_en = _hizli_cevir(soru, hedef="en")

        sistem_en_ek = "\n\nIMPORTANT: Write your reply in English. It will be translated back to Turkish afterward, so keep the tone and personality described above, but write in English. If you are given live search results below, use them and do not invent facts, scores, or dates — if the search results don't answer it, say you couldn't find reliable current information."
        messages_payload = [{"role": "system", "content": SYSTEM_PROMPT + sistem_en_ek}]
        if 'SOHBET_HAFIZASI' in globals() and SOHBET_HAFIZASI:
            messages_payload.extend(SOHBET_HAFIZASI)

        kullanici_mesaji = soru_en
        if arama_ozeti:
            kullanici_mesaji += f"\n\n[Live search results (may be in Turkish): {arama_ozeti}]"
        messages_payload.append({"role": "user", "content": kullanici_mesaji})

        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages_payload,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7
        )

        response_msg = completion.choices[0].message

        # FUNCTION CALLING YÖNETİMİ
        if response_msg.tool_calls:
            for tool_call in response_msg.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if fn_name == "hava_durumu_getir":
                    return hava_durumu_getir(args.get("sehir", "Istanbul"))
                elif fn_name == "uygulama_veya_oyun_ac":
                    hedef = args.get("isim", "")
                    ok = uygulama_veya_oyun_ac(hedef)
                    if ok:
                        return f"{hedef.capitalize()} başlatılıyor."
                    else:
                        # Model yanlış aracı seçmiş olabilir (örn. bir dizi adını uygulama sanmış).
                        # Kullanıcının orijinal cümlesiyle ekranda arama deneyerek toparlan.
                        _, mesaj = ekranda_bul_ve_tikla(soru)
                        return mesaj
                elif fn_name == "youtube_direkt_sarki_ac":
                    sorgu = args.get("sorgu", "")
                    youtube_direkt_sarki_ac(sorgu)
                    return f"{sorgu.capitalize()} YouTube üzerinde açılıyor..."
                elif fn_name == "zamanlayici_baslat":
                    dk = args.get("dakika", 1)
                    notu = args.get("hatirlatma_metni", "")
                    threading.Thread(target=zamanlayici_baslat, args=(dk, notu), daemon=True).start()
                    return f"{int(dk)} dakikalık zamanlayıcı kuruldu."
                elif fn_name == "ekran_goruntusu_al":
                    return ekran_goruntusu_al()
                elif fn_name == "tema_degistir":
                    return tema_degistir(args.get("tema_adi", "bordo"))
                elif fn_name == "ses_seviyesi_ayarla":
                    return ses_seviyesi_ayarla(args.get("seviye", 50))
                elif fn_name == "sistem_komutu_calistir":
                    return sistem_komutu_calistir(args.get("islem", ""), args.get("parametre", ""))
                elif fn_name == "kullanici_bilgisi_kaydet":
                    return kullanici_bilgisi_kaydet(args.get("anahtar", ""), args.get("deger", ""))
                elif fn_name == "ekranda_bul_ve_tikla":
                    _, mesaj = ekranda_bul_ve_tikla(args.get("hedef", ""))
                    return mesaj
                elif fn_name == "web_sitesi_ac":
                    return web_sitesi_ac(args.get("site_adi_veya_url", ""))
                elif fn_name == "get_traffic_route":
                    return trafik_durumu_sor(args.get("baslangic", ""), args.get("bitis", ""))

        cevap_en = response_msg.content.strip()
        if "</think>" in cevap_en:
            cevap_en = cevap_en.split("</think>")[-1].strip()

        cevap = _hizli_cevir(cevap_en, hedef="tr")

        # Sohbet geçmişine kaydet (kalıcı hafızaya yaz)
        SOHBET_HAFIZASI.append({"role": "user", "content": soru})
        SOHBET_HAFIZASI.append({"role": "assistant", "content": cevap})

        if len(SOHBET_HAFIZASI) > MAX_HAFIZA_UZUNLUGU:
            SOHBET_HAFIZASI = SOHBET_HAFIZASI[-MAX_HAFIZA_UZUNLUGU:]

        KALICI_HAFIZA["sohbet_gecmisi"] = SOHBET_HAFIZASI
        hafiza_kaydet(KALICI_HAFIZA)

        return cevap

    except Exception as e:
        print(f"Yapay zeka hatası: {e}")
        return "Efendim, sistemlerimde ufak bir aksama yaşandı, tekrar eder misiniz?"

def gunluk_ozet_olustur():
    """Bugüne kadar biriken sohbet geçmişini kısa bir özete çevirip KALICI_HAFIZA'ya
    tarihiyle kaydeder. SOHBET_HAFIZASI en fazla son 10 mesajı tuttuğu için, gün bittiğinde
    o günün özünü kalıcı hale getirmiş oluyoruz."""
    global KALICI_HAFIZA
    try:
        if not SOHBET_HAFIZASI:
            return  # o gün hiç konuşma olmamışsa özet çıkarmaya gerek yok

        konusma_metni = "\n".join(
            f"{m['role']}: {m['content']}" for m in SOHBET_HAFIZASI if m.get("content")
        )

        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Aşağıdaki konuşmayı, ileride hatırlanması gereken kalıcı noktalara odaklanarak SADECE TÜRKÇE ve en fazla 2 kısa cümleyle özetle. Sıradan/önemsiz konuşmaları atla."},
                {"role": "user", "content": konusma_metni}
            ],
            temperature=0.3,
            max_tokens=150
        )
        ozet = completion.choices[0].message.content.strip()
        if "</think>" in ozet:
            ozet = ozet.split("</think>")[-1].strip()

        bugun = datetime.datetime.now().strftime("%Y-%m-%d")
        KALICI_HAFIZA.setdefault("gunluk_ozetler", {})[bugun] = ozet

        # Son 30 günden eskisini sil ki dosya şişmesin
        tum_tarihler = sorted(KALICI_HAFIZA["gunluk_ozetler"].keys())
        if len(tum_tarihler) > 30:
            for eski in tum_tarihler[:-30]:
                del KALICI_HAFIZA["gunluk_ozetler"][eski]

        hafiza_kaydet(KALICI_HAFIZA)
    except Exception as e:
        print(f"Günlük özet oluşturma hatası: {e}")

UYGULAMA_MESAJ_NAVIGASYONU = {
    # Bazı uygulamalar açılışta doğrudan kişi listesini göstermez, önce bir ekstra
    # sekmeye/simgeye gitmek gerekir. Değer bir liste; her öğe ya:
    #   - bir metin tarifi (vision ile aranıp tıklanır), ya da
    #   - ("tab_enter", N) tuple'ı (N kere Tab'a basıp Enter'a basar - klavye navigasyonu)
    "instagram": [("tab_enter", 4)],
}

def _mesaj_gonderme_akisi(kisi, uygulama=None):
    """Kişiye mesaj yazma/gönderme akışının TAMAMINI, kesintisiz tek bir fonksiyonda yürütür.
    Uyandırma kelimesine veya 'takip modu'nun kesilmemesine bağımlı değildir - her soru burada
    doğrudan dinlenir. Hem 'X'e mesaj yazmak istiyorum' akışında hem gelen mesaja yanıt akışında
    ortak kullanılır (yanıt akışında uygulama ve kişi zaten bilindiği için soru sorulmaz)."""
    durum.mesgul = True
    try:
        if not uygulama:
            temel_konus(f"{kisi.capitalize()}'e mesaj yazmak için hangi uygulamayı kullanmak istersiniz?", sesli=True)
            uygulama = _cevap_dinle(toplam_sure_saniye=10)
            if not uygulama:
                temel_konus("Yanıt alamadım, işlemi iptal ediyorum.", sesli=True)
                return

        temel_konus(f"{uygulama.capitalize()} açılıyor.", sesli=True)
        acildi = uygulama_veya_oyun_ac(uygulama)
        if not acildi:
            # Kurulu bir masaüstü uygulaması olarak bulunamadıysa web sitesi olarak dene
            # (Instagram gibi resmi Windows uygulaması olmayanlar için)
            web_sitesi_ac(uygulama)
        time.sleep(4)  # uygulamanın tam açılıp klavye odağını alması için yeterli süre

        # Bazı uygulamalarda (örn. Instagram) önce mesajlar bölümüne gitmek gerekir
        for ara_adim in UYGULAMA_MESAJ_NAVIGASYONU.get(uygulama.lower().strip(), []):
            if isinstance(ara_adim, tuple) and ara_adim[0] == "tab_enter":
                for _ in range(ara_adim[1]):
                    pyautogui.press("tab")
                    time.sleep(0.15)
                pyautogui.press("enter")
                time.sleep(1)
            else:
                ara_basarili, ara_sonuc = ekranda_bul_ve_tikla(ara_adim)
                if not ara_basarili:
                    temel_konus(ara_sonuc, sesli=True)
                    return
                time.sleep(1)

        # Kişinin sohbetini açmayı 3 kez dene (yanlış tıklarsa tekrar arayıp dener)
        basarili = False
        sonuc = ""
        for deneme in range(2):
            basarili, sonuc = ekranda_bul_ve_tikla(kisi)
            if basarili:
                break
            time.sleep(1)

        if not basarili:
            temel_konus(f"{kisi.capitalize()} ile sohbeti açamadım, {sonuc}", sesli=True)
            return  # bulunamadıysa/yanlışsa akışı burada durdur, "mesajınız nedir" diye sormanın anlamı yok

        temel_konus("Mesajınız nedir?", sesli=True)
        mesaj = _cevap_dinle(toplam_sure_saniye=15, hassas=True)
        if not mesaj:
            temel_konus("Mesaj alamadım, işlemi iptal ediyorum.", sesli=True)
            return

        pyautogui.write(mesaj, interval=0.08)
        temel_konus("Yazdım, gönderelim mi?", sesli=True)

        onay = _cevap_dinle(toplam_sure_saniye=8)
        if onay and any(k in onay.lower() for k in ["evet", "gönder", "tamam", "olur"]):
            pyautogui.press("enter")
            temel_konus("Mesaj gönderildi.", sesli=True)
        else:
            temel_konus("Mesajı göndermedim, iptal ettim.", sesli=True)
    finally:
        durum.mesgul = False

def yazili_komut_isle(komut):
    if not komut: 
        return
    
    # Tanımsız değişken hatasını çözen kısım:
    komut_temiz = komut.lower().strip()
    komut_lower = komut_temiz

    # -------------------------------------------------------------
    # SESLİ MESAJ YAZMA AKIŞI (artık tek, kesintisiz fonksiyonda yürütülüyor)
    # -------------------------------------------------------------
    if any(k in komut_temiz for k in ["mesaj yazmak istiyorum", "mesaj atmak istiyorum", "mesaj göndermek istiyorum"]):
        kisi = re.sub(r'mesaj (yazmak|atmak|göndermek) istiyorum', '', komut_temiz).strip()
        kisi = kisi.strip(" .,!?")  # Whisper'ın eklediği noktalama işaretlerini temizle
        kisi = re.sub(r"(’|')?\s*(e|a|ye|ya|ne|na)$", '', kisi).strip()

        if kisi:
            _mesaj_gonderme_akisi(kisi)
        else:
            temel_konus("Kime mesaj yazmak istediğinizi anlayamadım efendim.", sesli=True)
        return

   # -------------------------------------------------------------
    # MEDYA KONTROLLERİ (Tek Çalışma Garantili)
    # -------------------------------------------------------------
    if any(k in komut_temiz for k in ["müziği durdur", "müziği kapat", "müzik durdur", "videoyu durdur", "diziyi durdur", "filmi durdur", "durdur"]):
        pyautogui.press("playpause")
        temel_konus("Durduruldu.", sesli=True)
        return  # <-- BURA ÇOK ÖNEMLİ: Kodun devam edip 2. kez tetiklenmesini önler

    elif any(k in komut_temiz for k in ["ss al", "ekran görüntüsü al", "ekranın fotoğrafını al", "ekran görüntüsü"]):
        cevap = ekran_goruntusu_al()
        temel_konus(cevap, sesli=True)
        return

    elif any(k in komut_temiz for k in ["ne çalıyor", "hangi şarkı çalıyor", "şu an ne dinliyorum", "çalan şarkı"]):
        cevap = spotify_su_an_ne_caliyor()
        temel_konus(cevap, sesli=True)
        return

    # -------------------------------------------------------------
    # KLAVYE YAZMA (çoğunlukla mesaj yazmak için - aktif metin kutusuna yazar)
    # -------------------------------------------------------------
    elif "yaz" in komut_temiz.split() and not any(x in komut_temiz for x in ["yazılım", "yazı tura", "yazı"]):
        orijinal_kelimeler = komut.split()
        kelimeler = komut_temiz.split()
        yaz_index = kelimeler.index("yaz")

        gonder_de = any(g in komut_temiz for g in ["gönder", "yolla"])

        # "yaz" başta ise (yaz: X / şunu yaz X) -> içerik SONRASINDA
        # "yaz" sonda/ortada ise (X yaz / X yaz gönder) -> içerik ÖNCESİNDE
        if yaz_index == 0 or (yaz_index == 1 and kelimeler[0] in ["şunu", "bunu"]):
            mesaj = " ".join(orijinal_kelimeler[yaz_index + 1:])
        else:
            mesaj = " ".join(orijinal_kelimeler[:yaz_index])

        mesaj = mesaj.replace("gönder", "").replace("yolla", "").strip(" :,.").strip()

        if mesaj:
            pyautogui.write(mesaj, interval=0.08)
            if gonder_de:
                pyautogui.press("enter")
                temel_konus("Yazdım ve gönderdim.", sesli=True)
            else:
                temel_konus("Yazdım.", sesli=True)
        else:
            temel_konus("Ne yazmamı istediğinizi anlayamadım efendim.", sesli=True)
        return

    elif komut_temiz.strip() in ["gönder", "şimdi gönder", "mesajı gönder"]:
        pyautogui.press("enter")
        temel_konus("Gönderildi.", sesli=True)
        return

    # -------------------------------------------------------------
    # FARE KONTROLÜ
    # -------------------------------------------------------------
    elif any(k in komut_temiz for k in ["fareyi", "imleci"]) and any(k in komut_temiz for k in [
            "ortasına", "ortaya", "orta", "sol üst", "sağ üst", "sol alt", "sağ alt",
            "sağa taşı", "sola taşı", "yukarı taşı", "aşağı taşı", "sağa götür", "sola götür",
            "yukarı götür", "aşağı götür"]):
        genislik, yukseklik = pyautogui.size()
        sayilar = re.findall(r'\d+', komut_temiz)
        mesafe = int(sayilar[0]) if sayilar else 150  # yön komutlarında piksel mesafesi

        if any(k in komut_temiz for k in ["ortasına", "ortaya", "orta"]):
            pyautogui.moveTo(genislik // 2, yukseklik // 2, duration=0.3)
            temel_konus("Fareyi ekranın ortasına götürdüm.", sesli=True)
        elif "sol üst" in komut_temiz:
            pyautogui.moveTo(20, 20, duration=0.3)
            temel_konus("Fareyi sol üst köşeye götürdüm.", sesli=True)
        elif "sağ üst" in komut_temiz:
            pyautogui.moveTo(genislik - 20, 20, duration=0.3)
            temel_konus("Fareyi sağ üst köşeye götürdüm.", sesli=True)
        elif "sol alt" in komut_temiz:
            pyautogui.moveTo(20, yukseklik - 20, duration=0.3)
            temel_konus("Fareyi sol alt köşeye götürdüm.", sesli=True)
        elif "sağ alt" in komut_temiz:
            pyautogui.moveTo(genislik - 20, yukseklik - 20, duration=0.3)
            temel_konus("Fareyi sağ alt köşeye götürdüm.", sesli=True)
        elif "sağa" in komut_temiz:
            pyautogui.moveRel(mesafe, 0, duration=0.2)
            temel_konus("Fareyi sağa taşıdım.", sesli=True)
        elif "sola" in komut_temiz:
            pyautogui.moveRel(-mesafe, 0, duration=0.2)
            temel_konus("Fareyi sola taşıdım.", sesli=True)
        elif "yukarı" in komut_temiz:
            pyautogui.moveRel(0, -mesafe, duration=0.2)
            temel_konus("Fareyi yukarı taşıdım.", sesli=True)
        elif "aşağı" in komut_temiz:
            pyautogui.moveRel(0, mesafe, duration=0.2)
            temel_konus("Fareyi aşağı taşıdım.", sesli=True)
        return

    elif "çift tıkla" in komut_temiz:
        pyautogui.doubleClick()
        temel_konus("Çift tıklandı.", sesli=True)
        return

    elif "sağ tıkla" in komut_temiz:
        pyautogui.rightClick()
        temel_konus("Sağ tıklandı.", sesli=True)
        return

    elif komut_temiz.strip() in ["tıkla", "tıklat", "tıkla efendim"] or "şimdi tıkla" in komut_temiz:
        pyautogui.click()
        temel_konus("Tıklandı.", sesli=True)
        return

    elif any(k in komut_temiz for k in ["müziği başlat", "müziği aç", "devam et", "şarkıyı başlat", "şarkıyı oynat", "şarkı başlat", "şarkı oynat", "parçayı başlat", "parçayı oynat"]):
        pyautogui.press("playpause")
        temel_konus("Başlatıldı.", sesli=True)
        return

# UYGULAMA KAPATMA KONTROLÜ
    # Fonksiyona gelen parametre adını otomatik tespit eder (metin/komut/soru)
    gelen_metin = locals().get('komut') or locals().get('text') or locals().get('metin') or locals().get('soru') or ""

    kapat_tetikleyicileri = ["kapat", "sonlandır", "çık"]
    if gelen_metin and any(kelime in gelen_metin.lower() for kelime in kapat_tetikleyicileri):
        uygulama = gelen_metin.lower()
        for kelime in kapat_tetikleyicileri + ["'ı", "'i", "'u", "'ü", "uygulamasını", "programını"]:
            uygulama = uygulama.replace(kelime, "")

        uygulama = uygulama.strip()

        if uygulama:
            sonuc = uygulama_kapat(uygulama)
            if sonuc:
                temel_konus(f"{uygulama.capitalize()} uygulamasını sonlandırdım efendim.", sesli=True)
            else:
                temel_konus(f"Arka planda çalışan bir {uygulama} uygulaması bulamadım efendim.", sesli=True)
            return

    # -------------------------------------------------------------
    # OYUN BAŞLATMA MODÜLÜ
    # -------------------------------------------------------------
    elif any(k in komut_temiz for k in ["oyun aç", "oyun başlat", "oyun oyna"]) or any(o in komut_temiz for o in ["valorant", "minecraft", "roblox", "cs2", "counter strike", "craftrise", "gang beasts", "beyond two souls", "monument valley", "peak", "ghost watchers", "geoguessr", "one armed cook", "goose goose duck"]):

        # Oyun adı ve masaüstündeki kısayol eşleşmeleri
        oyunlar = {
            "valorant": "VALORANT.lnk",
            "minecraft": "Legacy Launcher.lnk",  # Minecraft Dungeons için "Minecraft Dungeons.lnk"
            "craftrise": "CraftRise.exe.lnk",
            "roblox": "Roblox Player.lnk",
            "roblox studio": "Roblox Studio.lnk",
            "cs2": "Counter-Strike 2.lnk",
            "counter strike": "Counter-Strike 2.lnk",
            "gang beasts": "Gang Beasts.lnk",
            "beyond two souls": "Beyond Two Souls.lnk",
            "monument valley": "Monument Valley II.lnk",
            "peak": "PEAK.lnk",
            "ghost watchers": "Ghost Watchers.lnk",
            "geoguessr": "GeoGuessr Steam Edition.lnk",
            "one armed cook": "One-armed cook.lnk",
            "goose goose duck": "Goose Goose Duck.lnk"
        }

        masaustu_yolu = os.path.join(os.path.expanduser("~"), "Desktop")
        oyun_bulundu = False

        for oyun_anahtar, kisayol_adi in oyunlar.items():
            if oyun_anahtar in komut_temiz:
                dosya_yolu = os.path.join(masaustu_yolu, kisayol_adi)
                try:
                    os.startfile(dosya_yolu)
                    temel_konus(f"{oyun_anahtar.capitalize()} başlatılıyor, iyi oyunlar!", sesli=True)
                    oyun_bulundu = True
                    break
                except Exception as e:
                    temel_konus(f"{oyun_anahtar.capitalize()} kısayolu masaüstünde bulunamadı.", sesli=True)
                    print(f"Oyun Açma Hatası: {e}")
                    oyun_bulundu = True
                    break

        if not oyun_bulundu:
            temel_konus("Hangi oyunu açmak istediğinizi anlayamadım.", sesli=True)
        return

    # -------------------------------------------------------------
    # MASAÜSTÜ UYGULAMA BAŞLATMA MODÜLÜ
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # WEB SİTESİ AÇMA (tarayıcıdan açar, exe/uygulama olarak aramaz)
    # -------------------------------------------------------------
    elif ("aç" in komut_temiz.split() or "aç" in komut_temiz) and any(
            site in komut_temiz for site in ["youtube", "google", "gmail", "twitter", "x.com", "amazon", "ekşi", "eksisozluk"]):
        web_siteleri = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "twitter": "https://twitter.com",
            "x.com": "https://twitter.com",
            "amazon": "https://www.amazon.com.tr",
            "ekşi": "https://eksisozluk.com",
            "eksisozluk": "https://eksisozluk.com",
        }
        for site_adi, url in web_siteleri.items():
            if site_adi in komut_temiz:
                webbrowser.open(url)
                temel_konus(f"{site_adi.capitalize()} tarayıcıda açılıyor.", sesli=True)
                break
        return

    elif any(k in komut_temiz for k in ["uygulama aç", "program aç"]) or any(u in komut_temiz for u in ["discord", "teams", "spotify", "skype", "whatsapp", "prime video", "instagram", "netflix", "zoom", "capcut"]):
        # Uygulama adı ve Masaüstü kısayol isimleri
        uygulamalar = {
            "discord": "Discord.lnk",
            "teams": "Microsoft Teams.lnk",
            "microsoft teams": "Microsoft Teams.lnk",
            "spotify": "Spotify.lnk",
            "skype": "Skype.lnk",
            "whatsapp": "WhatsApp.lnk",
            "prime video": "Prime Video.lnk",
            "prime": "Prime Video.lnk",
            "instagram": "Instagram.lnk",
            "netflix": "Netflix.lnk",
            "zoom": "ZoomInstaller.lnk",
            "capcut": "CapCut.lnk"
        }

        masaustu_yolu = os.path.join(os.path.expanduser("~"), "Desktop")
        uygulama_bulundu = False

        for uyg_anahtar, kisayol_adi in uygulamalar.items():
            if uyg_anahtar in komut_temiz:
                dosya_yolu = os.path.join(masaustu_yolu, kisayol_adi)
                try:
                    os.startfile(dosya_yolu)
                    temel_konus(f"{uyg_anahtar.capitalize()} uygulaması açılıyor.", sesli=True)
                    uygulama_bulundu = True
                    break
                except Exception as e:
                    temel_konus(f"{uyg_anahtar.capitalize()} kısayolu masaüstünde bulunamadı.", sesli=True)
                    print(f"Uygulama Açma Hatası: {e}")
                    uygulama_bulundu = True
                    break

        if not uygulama_bulundu:
            temel_konus("Hangi uygulamayı açmak istediğinizi anlayamadım.", sesli=True)
        return 

    # -------------------------------------------------------------
    # UYGULAMA AÇMA / KAPATMA
    # -------------------------------------------------------------
    elif "opera" in komut_temiz:
        if any(k in komut_temiz for k in ["kapat", "sonlandır"]):
            os.system("taskkill /f /im opera.exe")
            temel_konus("Opera kapatıldı.", sesli=True)
        else:
            os.system("start opera")
            temel_konus("Opera açılıyor.", sesli=True)
        return

    elif any(k in komut_temiz for k in ["pencereyi kapat", "uygulamayı kapat"]):
        pyautogui.hotkey("alt", "f4")
        temel_konus("Aktif pencere kapatıldı.", sesli=True)
        return

    # -------------------------------------------------------------
    # İZLEME GEÇMİŞİNDEN İLK VİDEOYU AÇMA VE TAM EKRAN YAPMA
    # -------------------------------------------------------------
    elif any(k in komut_temiz for k in ["son videoyu aç", "kaldığım videoyu aç", "son izlediğim videoyu aç", "kaldığım yerden devam et"]):
        temel_konus("Son izlediğiniz video açılıyor.", sesli=True)
        
        # 1. YouTube İzleme Geçmişini Aç
        webbrowser.open("https://www.youtube.com/feed/history")
        time.sleep(3.0)  # Sayfanın yüklenmesini bekle
        
        # 2. Tarayıcıyı Tam Ekran Yap (F11)
        pyautogui.press("f11")
        time.sleep(1)
        
        # 3. "Videolar" Filtre Butonuna Tıkla (Shorts'ları gizler)
        pyautogui.click(x=537, y=147)
        time.sleep(2.0)  # Listenin yenilenmesini bekle
        
        # 4. Shorts'suz listede en üstteki İlk Videoya Tıkla
        pyautogui.click(x=542, y=290)
        time.sleep(2.0)  # Videonun oynatıcısının yüklenmesini bekle
        
        # 5. Videoyu Tam Ekran Oynat (F tuşu)
        pyautogui.press("f")
        return

    # -------------------------------------------------------------
    # NETFLIX KOORDİNAT TABANLI DOĞRUDAN TIKLAMA MODÜLÜ
    # -------------------------------------------------------------
    elif "netflix" in komut_temiz and any(k in komut_temiz for k in ["aç", "izlet", "başlat", "ara"]):

        dizi_adi = komut_temiz.replace("netflix", "").replace("aç", "").replace("izlet", "").replace("başlat", "").replace("ara", "").replace("te", "").replace("ta", "").strip()

        masaustu_yolu = os.path.join(os.path.expanduser("~"), "Desktop")
        try:
            os.startfile(os.path.join(masaustu_yolu, "Netflix.lnk"))
            temel_konus("Netflix açılıyor.", sesli=True)
            time.sleep(4)

            # Ekranı tam ekran yapmak için (Garanti odaklama)
            pyautogui.hotkey("win", "up")
            time.sleep(1)

            if dizi_adi:
                # 1. Sağ üstteki Arama Büyüteç Simgesine Tıkla (Örn: X=1750, Y=40)
                # Kendi ekran çözünürlüğüne göre bu koordinatları güncelleyebilirsin
                pyautogui.click(x=1693, y=71) 
                time.sleep(0.5)

                # 2. Dizi Adını Yaz ve Enter'a Bas
                pyautogui.write(dizi_adi, interval=0.1)
                pyautogui.press("enter")
                time.sleep(2)

                # 3. İlk Çıkan Sonuç Kartına Tıkla (Örn: X=273, Y=232)
                pyautogui.click(x=273, y=232)
                time.sleep(1.5)

                # 4. Oynat Butonuna Tıkla (Örn: X=594, Y=528)
                pyautogui.click(x=594, y=528)
                temel_konus(f"{dizi_adi.title()} başlatılıyor.", sesli=True)

        except Exception as e:
            temel_konus("Netflix işleminde bir hata oluştu.", sesli=True)
            print(f"Netflix Hatası: {e}")
        return
    # -------------------------------------------------------------
    # MS TEAMS ARAMA KABUL ETME (Görsel Arama Modülü)
    # -------------------------------------------------------------
    elif any(k in komut_temiz for k in ["aramayı aç", "teams aç", "çağrıyı yanıtla", "telefonu aç"]):
        try:
            # Ekranda 'teams_kabul.png' görselini %80 benzerlik toleransıyla tarar
            resim_konumu = pyautogui.locateOnScreen('teams_kabul.png', confidence=0.6)
            
            if resim_konumu:
                # Görsel bulunursa merkezine tıkla
                merkez_x, merkez_y = pyautogui.center(resim_konumu)
                pyautogui.click(merkez_x, merkez_y)
                
                temel_konus("Teams araması kabul edildi.", sesli=True)
                print(f"Teams Kabul Butonu Bulundu: {merkez_x, merkez_y}")
            else:
                temel_konus("Ekranda Teams kabul butonu göremedim.", sesli=True)
                print("Hata: teams_kabul.png ekranda bulunamadı.")

        except Exception as e:
            temel_konus("Aramayı açarken bir sorun oluştu.", sesli=True)
            print(f"Görsel Arama Hatası: {e}")
        
        return  # Çift tetiklenmeyi ve LLM'e gitmesini engeller

    # -------------------------------------------------------------
    # PİL VE SİSTEM DURUMU RAPORLAMA
    # -------------------------------------------------------------
    elif any(k in komut_temiz for k in ["pil durumu", "şarjım kaç", "batarya", "pil"]):
        battery = psutil.sensors_battery()
        if battery:
            yuzde = int(battery.percent)
            plugged = "şarja takılı" if battery.power_plugged else "şarja takılı değil"
            temel_konus(f"Pil seviyeniz yüzde {yuzde} ve cihaz şu an {plugged}.", sesli=True)
        else:
            temel_konus("Pil bilgisi alınamadı, muhtemelen bir masaüstü bilgisayar kullanıyorsunuz.", sesli=True)
        return

    # -------------------------------------------------------------
    # SESLİ HATIRLATICI / ALARM
    # -------------------------------------------------------------
    elif "dakika sonra" in komut_temiz and any(k in komut_temiz for k in ["hatırlat", "alarm kur", "haber ver"]):
        try:
            # "10 dakika sonra hatırlat" ifadesinden sayıyı çeker
            kelimeler = komut_temiz.split()
            dk_index = kelimeler.index("dakika")
            dakika = float(kelimeler[dk_index - 1])

            # Hatırlatılacak notu yakala
            not_metni = komut_temiz.split("sonra")[-1].replace("hatırlat", "").replace("alarm kur", "").strip()
            if not not_metni:
                not_metni = "Süreniz doldu!"

            def zamanlayici_gorevi():
                time.sleep(dakika * 60)
                temel_konus(f"Hatırlatıcı zamanı geldi! Notunuz: {not_metni}", sesli=True)

            # Ana kilitlenmesin diye zamanlayıcıyı ayrı thread'de çalıştırıyoruz
            threading.Thread(target=zamanlayici_gorevi, daemon=True).start()
            temel_konus(f"Tamamdır, {int(dakika)} dakika sonra size haber vereceğim.", sesli=True)

        except Exception as e:
            temel_konus("Dakikayı anlayamadım, lütfen '5 dakika sonra su içmeyi hatırlat' şeklinde tekrar söyler misiniz?", sesli=True)
        return

    # -------------------------------------------------------------
    # SES SEVİYESİ KONTROLÜ
    # -------------------------------------------------------------
    elif "ses seviyesi" in komut_temiz or "sesi" in komut_temiz:
        # Metin içindeki sayıyı çek
        sayilar = [int(s) for s in komut_temiz.split() if s.isdigit()]
        if sayilar:
            yuzde = sayilar[0]
            mesaj = ses_seviyesi_ayarla(yuzde)
            temel_konus(mesaj, sesli=True)
            return  # <-- BURA ÇOK ÖNEMLİ

   # --- YÜZDELİK SES KONTROLÜ ---
    if "sesi" in komut_temiz and any(kelime in komut_temiz for kelime in ["yap", "ayarla", "getir", "çek"]):
        # Cümle içindeki tüm sayıları bulur (Örn: "sesi 50 yap" -> 50)
        sayilar = re.findall(r'\d+', komut_temiz)
        if sayilar:
            hedef_seviye = int(sayilar[0])
            cevap = sistem_sesini_ayarla(hedef_seviye)
            temel_konus(cevap, sesli=True)
            return

# --- SONRAKİ / ÖNCEKİ ŞARKI HIZLI TETİKLEYİCİLERİ ---
    if any(k in komut_temiz for k in ["sonraki şarkı", "sonraki sarki", "diğer şarkı", "şarkıyı değiştir", "sonraki parça"]):
        cevap = sistem_komutu_calistir("sonraki_sarki")
        temel_konus(cevap, sesli=True)
        return

    if any(k in komut_temiz for k in ["önceki şarkı", "onceki sarki", "geçen şarkı", "öncekine geç", "önceki"]):
        cevap = sistem_komutu_calistir("onceki_sarki")
        temel_konus(cevap, sesli=True)
        return

# --- DİNAMİK VİSİON TIKLAMA TETİKLEYİCİSİ ---
    if "tıkla" in komut_temiz or "tikla" in komut_temiz:
        # Ek takılarını ("ini", "ına", "a", "e") temizleyip net ismi alıyoruz
        hedef = komut_temiz.replace("tıkla", "").replace("tikla", "")
        hedef = hedef.replace("simgesini", "simgesi").replace("butonunu", "butonu").replace("kutusunu", "kutusu").strip()
        
        if hedef:
            temel_konus(f"Ekranda '{hedef}' aranıyor...", sesli=True)
            cevap = dinamik_butona_tikla(hedef)
            temel_konus(cevap, sesli=True)
            return

# --- HAFIZA TETİKLEYİCİSİ ---
    if "hatırla" in komut_temiz:
        bilgi = komut_temiz.replace("bunu hatırla", "").replace("hatırla", "").strip()
        if bilgi:
            hafizaya_yaz("kullanici_notu", bilgi)
            temel_konus(f"Aklıma kaydettim: {bilgi}", sesli=True)
        else:
            kayit = hafizadan_oku("kullanici_notu")
            if kayit:
                temel_konus(f"Aklımda kalan son bilgi: {kayit}", sesli=True)
            else:
                temel_konus("Hafızamda henüz kayıtlı bir bilgi yok.", sesli=True)
        return

# --- BİLGİSAYAR KAPATMA & ZAMANLI KAPATMA HIZLI TETİKLEYİCİ ---
    if any(k in komut_temiz for k in ["bilgisayarı kapat", "bilgisayari kapat", "sistemi kapat", "pc kapat"]):
        # Cümle içinde sayı/dakika var mı kontrol et (Örn: "30 dakikaya", "10 dakika sonra")
        sayilar = [int(s) for s in komut_temiz.split() if s.isdigit()]
        dakika = str(sayilar[0]) if sayilar else "0"
        
        # Süreli veya süresiz Windows kapatma komutunu gönder
        cevap = sistem_komutu_calistir("bilgisayari_kapat", dakika)
        temel_konus(cevap, sesli=True)
        return

    # --- TRABZON USULÜ TEMEL'İ KAPATMA (Zıbar & Yattara) ---
    if any(k in komut_temiz for k in ["zıbar", "yattara", "temel zıbar", "temel yattara"]):
        temel_konus("Ben çalımımı attım, yattım daa! Hadi ben kaçtum.", sesli=True)
        time.sleep(1)
        os._exit(0)
        return

# --- BİLGİSAYAR KAPATMAYI İPTAL ETME ---
    if any(k in komut_temiz for k in ["kapatmayı iptal et", "kapatmayi iptal et", "iptal et", "kapatma iptal", "vazgeç"]):
        cevap = sistem_komutu_calistir("kapatmayi_iptal_et")
        temel_konus(cevap, sesli=True)
        return

# --- PENCERE KAPATMA HIZLI TETİKLEYİCİ ---
    if any(k in komut_temiz for k in ["bu pencereyi kapat", "pencereyi kapat", "sekmeyi kapat", "uygulamayı kapat", "ekranı kapat"]):
        # Temel'in kendi ana penceresini değil, o an aktif olan pencereyi kapatır (Alt+F4)
        cevap = sistem_komutu_calistir("pencere_kapat")
        temel_konus(cevap, sesli=True)
        return
    
    # 1. Anlatımı kesme / Teşekkür kontrolü
    durdurma_kelimeleri = ["teşekkürler", "teşekkür ederim", "tamamdır", "yeterli", "dur", "sağol", "kes"]
    if any(kelime in komut_temiz for kelime in durdurma_kelimeleri):
        temel_konus("Rica ederim!", sesli=True)
        return

    # 2. Kapatma kontrolü
    if "kapat" in komut_temiz or "çıkış" in komut_temiz:
        temel_konus("Görüşmek üzere!", sesli=True)
        os._exit(0)

    elif any(k in komut_temiz for k in ["günaydın", "günün özeti", "sabah modu", "özeti ver"]):
        if hud: ui_bridge.status_signal.emit("THINKING", "GÜNÜN ÖZETİ HAZIRLANIYOR...")
        ozet = gunun_ozeti_getir()
        temel_konus(ozet, sesli=True)

    elif "sistem" in komut_temiz or "işlemci" in komut_temiz or "ram" in komut_temiz:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        temel_konus(f"İşlemci kullanımı yüzde {cpu}, bellek kullanımı yüzde {ram}.", sesli=True)

    elif "sesi yüzde" in komut_temiz or "ses düzeyini" in komut_temiz:
        ses_seviyesi_ayarla(komut_temiz)
    elif "sesi yükselt" in komut_temiz or "sesi aç" in komut_temiz:
        ses_degistir("yukselt", 8)
        temel_konus("Ses yükseltildi.", sesli=True)
    elif "sesi kıs" in komut_temiz or "sesi düşür" in komut_temiz:
        ses_degistir("dusur", 8)
        temel_konus("Ses kısıldı.", sesli=True)

    elif "oyun modu" in komut_temiz:
        temel_konus("Oyun modu açılıyor.", sesli=True)
        uygulama_veya_oyun_ac("steam")
        ses_degistir("yukselt", miktar=16)

    elif "çalışma modu" in komut_temiz or "ders modu" in komut_temiz:
        temel_konus("Çalışma modu açılıyor.", sesli=True)
        if os.path.exists(NOT_DOSYASI):
            os.system(f'start notepad "{NOT_DOSYASI}"')
        else:
            uygulama_veya_oyun_ac("not defteri")
        ses_degistir("dusur", miktar=10)

    elif "saat" in komut_temiz and len(komut_temiz.split()) <= 3:
        temel_konus(f"Şu an saat {datetime.datetime.now().strftime('%H:%M')}", sesli=True)

    else:
        cevap = yapay_zekaya_sor(komut_temiz)
        temel_konus(cevap, sesli=True)

# ==========================================
# 5. ARAMA ALGILAMA VE YÖNETİMİ
# ==========================================
def arama_yanitla_veya_reddet(platform, kabul_et=True):
    time.sleep(0.3)
    
    if platform == "WHATSAPP":
        # 1. Önce klavye kısayolunu dene (ekran çözünürlüğünden/pencere boyutundan etkilenmez)
        if kabul_et:
            pyautogui.hotkey("alt", "a")
        else:
            pyautogui.hotkey("alt", "d")
            pyautogui.press("escape")

        time.sleep(0.5)

        # 2. Garanti olsun diye koordinat tıklamayı da yedek olarak dene
        try:
            wa_pencereler = [w for w in pyautogui.getAllWindows() if "whatsapp" in w.title.lower() or "call" in w.title.lower() or "arama" in w.title.lower()]
            if wa_pencereler:
                pencere = wa_pencereler[0]
                pencere.activate()
                time.sleep(0.2)
                
                left, top, width, height = pencere.left, pencere.top, pencere.width, pencere.height
                
                if kabul_et:
                    target_x = left + int(width * 0.53)
                    target_y = top + int(height * 0.93)
                else:
                    target_x = left + int(width * 0.90)
                    target_y = top + int(height * 0.93)
                    
                pyautogui.click(target_x, target_y)
        except Exception as e:
            print(f"WhatsApp tıklama hatası: {e}")

    elif platform == "TEAMS":
        try:
            # Teams arama penceresini yakala
            teams_pencereler = [w for w in pyautogui.getAllWindows() if "teams" in w.title.lower() or "call" in w.title.lower() or "arıyor" in w.title.lower()]
            if teams_pencereler:
                pencere = teams_pencereler[0]
                pencere.activate()
                time.sleep(0.2)
        except Exception as e:
            print(f"Teams pencere odaklama hatası: {e}")

        # Microsoft Teams Resmi Klavye Kısayolları
        if kabul_et:
            # Aramayı Kabul Et: Ctrl + Shift + S
            pyautogui.hotkey("ctrl", "shift", "s")
        else:
            # Aramayı Reddet: Ctrl + Shift + D
            pyautogui.hotkey("ctrl", "shift", "d")

    elif platform == "DISCORD":
        if kabul_et:
            pyautogui.hotkey("ctrl", "enter")
        else:
            pyautogui.press("escape")


def ekran_arama_tarama():
    
    resimler = {
        "WHATSAPP": "whatsapp_arama.png",
        "DISCORD": "discord_arama.png",
        "TEAMS": "teams_arama.png"
    }

    # 1. Başlık Taraması (Teams Arama Penceresi / Pop-up) — hızlı ve sağlam, önce bunu dene
    try:
        for baslik in pyautogui.getAllTitles():
            b_kucuk = baslik.lower()
            if "teams" in b_kucuk or "microsoft teams" in b_kucuk:
                if any(k in b_kucuk for k in ["incoming", "arıyor", "call", "gelen arama"]):
                    durum.active_call_detected = True
                    durum.call_platform = "TEAMS"
                    
                    # İsmi pencere başlığından çekmeye çalış
                    parcalar = baslik.split("-")
                    if len(parcalar) > 1:
                        durum.caller_name = parcalar[0].strip()
                    else:
                        durum.caller_name = "Biri"
                    return True
    except Exception:
        pass

    # 2. Görsel Taraması (yedek — WhatsApp/Discord başlıktan anlaşılamadığı için hâlâ gerekli)
    for platform, resim in resimler.items():
        if os.path.exists(resim):
            try:
                konum = pyautogui.locateOnScreen(resim, confidence=0.5, grayscale=True)
                if konum:
                    durum.active_call_detected = True
                    durum.call_platform = platform
                    durum.caller_name = "Biri"
                    return True
            except Exception:
                pass

    return False

def kisayol_dinleyici():
    while True:
        try:
            keyboard.wait("ctrl+alt+t")
            durum.force_listen_flag = True
        except Exception as e:
            print(f"Kısayol dinleyici hatası: {e}")

# ==========================================
# 6. MİKROFON DÖNGÜSÜ
# ==========================================
PROAKTIF_ZAMANLAR = {
    "09:00": "Günaydın! Yeni bir gün başlıyor, sistemler hazır.",
    "13:00": "Öğle oldu, biraz mola vermek ister misin?",
    "23:00": "Saat geç oldu, dinlenmeyi unutma.",
}

RESOURCE_ESIKLERI = {
    "CPU": 90,
    "RAM": 90,
    "DISK": 90,
}
RESOURCE_COOLDOWN_SANIYE = 900  # 15 dakika - aynı uyarıyı bu süre içinde tekrar etme

UZUN_SURE_ESIK_SAAT = 3
UZUN_SURE_TAKIP_LISTESI = ["chrome.exe", "msedge.exe", "discord.exe", "spotify.exe"]

GECE_ISIGI_SORU_SAATI = "00:30"
GUNLUK_OZET_SAATI = "23:55"

def bildirim_tarama_dongusu():
    """WhatsApp/Teams/Telefon bildirimlerini ayrı ve sık (5 saniyede bir) kontrol eder.
    Proaktif konuşma döngüsünden ayrı tutulma sebebi: art arda gelen mesajları
    30 saniyelik döngüye göre çok daha hızlı yakalasın."""
    while True:
        try:
            if durum.mesgul:
                # Temel şu an başka bir akışla (mesaj yazma, gece ışığı sorusu, arama vb.) meşgul.
                # Bildirimleri şimdi işleme/duyurma - "görüldü" olarak işaretlemeden bir sonraki
                # müsait tura bırak, yoksa akışların üstüne biner ve karışıklık yaratır.
                time.sleep(5)
                continue

            for uygulama_adi, baslik, icerik in yeni_bildirimleri_kontrol_et():
                if icerik:
                    temel_konus(f"{uygulama_adi} üzerinden bir mesaj geldi. {baslik}: {icerik}")
                    # Gerçek bir mesajsa (gönderen + içerik var), yanıt sorusu için bayrak kaldır
                    # (mikrofon çakışmasın diye soru-cevap kısmını asistan_dongusu yürütecek)
                    durum.yanit_sorusu_bekleniyor = True
                    durum.yanit_uygulama = uygulama_adi
                    durum.yanit_kisi = baslik
                else:
                    temel_konus(f"{uygulama_adi} üzerinden yeni bir bildirim var: {baslik}")
            time.sleep(5)
        except Exception as e:
            print(f"Bildirim tarama döngüsü hatası: {e}")
            time.sleep(5)

def proaktif_konusma_dongusu():
    soylenenler = set()
    son_uyari_zamani = {}
    uzun_sure_uyarilanlar = set()
    while True:
        try:
            simdi = datetime.datetime.now()
            bugun = simdi.strftime("%Y-%m-%d")
            saat_dk = simdi.strftime("%H:%M")

            for zaman, mesaj in PROAKTIF_ZAMANLAR.items():
                anahtar = f"{bugun}_{zaman}"
                if saat_dk == zaman and anahtar not in soylenenler:
                    temel_konus(mesaj)
                    soylenenler.add(anahtar)

            # Gece ışığı sorusu - günde bir kez, saati asistan_dongusu'na bayrakla haber ver
            # (mikrofon çakışmasın diye soru-cevap kısmını asistan_dongusu yürütüyor)
            gece_isigi_anahtari = f"{bugun}_geceisigi"
            if saat_dk == GECE_ISIGI_SORU_SAATI and gece_isigi_anahtari not in soylenenler:
                durum.gece_isigi_sorusu_bekleniyor = True
                soylenenler.add(gece_isigi_anahtari)

            ozet_anahtari = f"{bugun}_gunlukozet"
            if saat_dk == GUNLUK_OZET_SAATI and ozet_anahtari not in soylenenler:
                gunluk_ozet_olustur()
                soylenenler.add(ozet_anahtari)

            # Gün değiştiyse eski kayıtları temizle (hafıza şişmesin)
            soylenenler = {k for k in soylenenler if k.startswith(bugun)}
            uzun_sure_uyarilanlar = {k for k in uzun_sure_uyarilanlar if k.startswith(bugun)}

            # Sistem kaynak kontrolü (CPU / RAM / Disk)
            kaynaklar = {
                "CPU": psutil.cpu_percent(interval=1),
                "RAM": psutil.virtual_memory().percent,
                "DISK": psutil.disk_usage("C:\\").percent,
            }

            for isim, deger in kaynaklar.items():
                if deger >= RESOURCE_ESIKLERI[isim]:
                    son = son_uyari_zamani.get(isim, 0)
                    if time.time() - son > RESOURCE_COOLDOWN_SANIYE:
                        temel_konus(f"{isim} kullanımı yüzde {int(deger)}'e ulaştı, dikkatli olalım.")
                        son_uyari_zamani[isim] = time.time()

            # Uzun süredir açık kalan uygulamalar
            for proc in psutil.process_iter(['name', 'create_time']):
                try:
                    pname = proc.info['name']
                    if pname and pname.lower() in UZUN_SURE_TAKIP_LISTESI:
                        acik_kalma_saat = (time.time() - proc.info['create_time']) / 3600
                        anahtar = f"{bugun}_{pname.lower()}"
                        if acik_kalma_saat >= UZUN_SURE_ESIK_SAAT and anahtar not in uzun_sure_uyarilanlar:
                            temel_konus(f"{pname} yaklaşık {int(acik_kalma_saat)} saattir açık, göz atmak ister misin?")
                            uzun_sure_uyarilanlar.add(anahtar)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            time.sleep(30)
        except Exception as e:
            print(f"Proaktif konuşma hatası: {e}")
            time.sleep(30)


def asistan_dongusu():
    time.sleep(1)
    temel_konus("Sistemler ve sohbet paneli aktif. Dinliyorum.")

    while True:
        try:
            duyulan_metin = None  # <-- ÇÖKMEYİ ENGELLEYEN KRİTİK EKLENDİ (Her döngü başında sıfırlanır)

            # Gece ışığı sorusu bekleniyorsa önce onu sor (mikrofon tek bir yerden yönetilsin)
            if durum.gece_isigi_sorusu_bekleniyor:
                durum.gece_isigi_sorusu_bekleniyor = False
                durum.mesgul = True
                temel_konus("Saat oldukça geç oldu, gece ışığını açayım mı?")

                cevap_alindi = False
                baslangic = time.time()
                while not cevap_alindi and (time.time() - baslangic < 10):
                    cevap = groq_whisper_dinle(max_sure=3)
                    if cevap:
                        cevap_temiz = cevap.lower().strip()
                        if any(k in cevap_temiz for k in ["evet", "aç", "açabilirsin", "olur", "tamam"]):
                            if gece_isigi_ayarla(ac=True):
                                temel_konus("Gece ışığını açtım.")
                            else:
                                temel_konus("Gece ışığını açarken bir sorun oldu.")
                            cevap_alindi = True
                        elif any(k in cevap_temiz for k in ["hayır", "istemiyorum", "kalsın", "açma"]):
                            temel_konus("Tamam, açmıyorum.")
                            cevap_alindi = True

                if not cevap_alindi:
                    temel_konus("Yanıt alamadım, gece ışığına dokunmuyorum.")

                durum.mesgul = False
                continue

            # Gelen mesaja yanıt sorusu bekleniyorsa sor (mikrofon tek bir yerden yönetilsin)
            if durum.yanit_sorusu_bekleniyor:
                durum.yanit_sorusu_bekleniyor = False
                durum.mesgul = True
                temel_konus(f"{durum.yanit_kisi} isimli kişiden gelen mesaja yanıt vermek ister misiniz?")

                cevap = _cevap_dinle(toplam_sure_saniye=8)
                if cevap and any(k in cevap.lower() for k in ["evet", "tamam", "olur", "yaz"]):
                    _mesaj_gonderme_akisi(durum.yanit_kisi, durum.yanit_uygulama)  # kendi içinde mesgul'u yönetir
                else:
                    temel_konus("Tamam, yanıt vermiyorum.")
                    durum.mesgul = False

                continue

            if not durum.active_call_detected:
                ekran_arama_tarama()

            if durum.active_call_detected:
                arka_plan_sesini_kis()

                if hud:
                    ui_bridge.status_signal.emit("CALL", f"{durum.call_platform}: {durum.caller_name}")
            
                temel_konus(f"{durum.call_platform} üzerinden {durum.caller_name} arıyor. Açayım mı?")
            
                decided = False
                start_time = time.time()
            
                while not decided and (time.time() - start_time < 10):
                    cevap = groq_whisper_dinle(max_sure=3)
                    if cevap:
                        cevap_temiz = cevap.lower().strip()
                        if any(k in cevap_temiz for k in ["açma", "reddet", "kapat", "hayır", "meşgule", "istemiyorum"]):
                            temel_konus("Arama reddediliyor.")
                            arama_yanitla_veya_reddet(durum.call_platform, kabul_et=False)
                            decided = True
                        elif any(k in cevap_temiz for k in ["aç", "yanıtla", "evet", "kabul", "bağlan", "cevapla"]):
                            temel_konus("Arama yanıtlanıyor.")
                            arama_yanitla_veya_reddet(durum.call_platform, kabul_et=True)
                            decided = True
            
                if not decided:
                    temel_konus("Yanıt alamadım, aramayı reddediyorum.")
                    arama_yanitla_veya_reddet(durum.call_platform, kabul_et=False)

                durum.active_call_detected = False
                if hud:
                    ui_bridge.status_signal.emit("LISTENING", "SYSTEM READY // LISTENING...")
            
                arka_plan_sesini_ac()
                time.sleep(10)

            else:
                if hud:
                    ui_bridge.status_signal.emit("LISTENING", "SYSTEM READY // LISTENING...")
            
                if durum.force_listen_flag:
                    durum.force_listen_flag = False
                    duyulan_metin = TETIKLEYICI_KELIMELER[0]
                else:
                    duyulan_metin = groq_whisper_dinle()

            # None veya boş metin kontrolü (Artık UnboundLocalError vermez)
            if not duyulan_metin:
                continue

            tetikleyici_kelimeler = TETIKLEYICI_KELIMELER
            if any(k in duyulan_metin.lower() for k in tetikleyici_kelimeler):
                komut = duyulan_metin.lower()
                for k in tetikleyici_kelimeler: 
                    komut = komut.replace(k, "")
                komut = komut.strip()

                # Sadece isim söylendiyse dinle
                if not komut or len(komut) < 2:
                    temel_konus("Efendim, dinliyorum?")
                    komut = groq_whisper_dinle()
                
                    if not komut or len(komut.strip()) < 2:
                        print("Sessizlik algılandı, dinleme sonlandırıldı.")
                        continue

                # SÜREKLİ TAKİP DİNLENMESİ
                while komut:
                    if hud:
                        ui_bridge.chat_append_signal.emit("Siz (Ses)", komut)

                    yazili_komut_isle(komut)

                    if hud:
                        ui_bridge.status_signal.emit("LISTENING", "SİZİ DİNLİYORUM (TAKİP)...")

                    takip_sesi = groq_whisper_dinle()

                    if takip_sesi:
                        takip_temiz = takip_sesi.lower().strip()
                        durdurma = ["tamam", "tamamdır", "teşekkür", "teşekkürler", "sağol", "yeterli", "kapat"]
                    
                        if any(d in takip_temiz for d in durdurma):
                            komut = None
                        else:
                            komut = takip_sesi
                    else:
                        komut = None
        except Exception as e:
            print(f"Asistan döngüsü hatası: {e}")
            time.sleep(1)
            continue
# ==========================================
# 7. BAŞLATICI
# ==========================================
TELEFON_SIFRE = os.getenv("TEMEL_TELEFON_SIFRE", "")

TELEFON_SAYFA_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>T.E.M.E.L. Kontrol</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, Segoe UI, Roboto, sans-serif;
            background: linear-gradient(180deg, #0d0d0f 0%, #1a0a0d 100%);
            color: #f2f2f2; padding: 24px 18px; margin: 0; min-height: 100vh;
        }
        h2 { text-align: center; color: #c9a84a; letter-spacing: 2px; font-weight: 600; margin-bottom: 24px; }
        input, button {
            font-size: 17px; padding: 14px; width: 100%; border-radius: 10px; border: none; margin-top: 12px;
        }
        input { background: #1e1e22; color: #fff; border: 1px solid #333; }
        input::placeholder { color: #888; }
        button {
            background: linear-gradient(135deg, #7a0019, #4a0010); color: white; font-weight: 600;
            letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(122,0,25,0.4);
        }
        button:active { transform: scale(0.98); }
        #mikrofon {
            background: linear-gradient(135deg, #2a2a2e, #151517); font-size: 24px; padding: 16px;
            display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        #mikrofon.dinliyor { background: linear-gradient(135deg, #c9a84a, #8a6f1f); animation: nabiz 1s infinite; }
        @keyframes nabiz { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
        #cevap {
            margin-top: 20px; padding: 14px; background: #1a1a1d; border-radius: 10px;
            min-height: 44px; border-left: 3px solid #c9a84a; line-height: 1.4;
        }
    </style>
</head>
<body>
    <h2>T.E.M.E.L.</h2>
    <input type="password" id="sifre" placeholder="Şifre">
    <input type="text" id="komut" placeholder="Komutunu yaz veya mikrofona konuş...">
    <button id="mikrofon" onclick="sesleDinle()">🎙️ Sesli Komut</button>
    <button onclick="gonder()">Gönder</button>
    <div id="cevap">Hazır efendim.</div>
    <script>
        // Şifreyi telefonda hatırla, her seferinde yazmaya gerek kalmasın
        window.onload = () => {
            const kayitli = localStorage.getItem('temel_sifre');
            if (kayitli) document.getElementById('sifre').value = kayitli;
        };

        function gonder() {
            const sifre = document.getElementById('sifre').value;
            const komut = document.getElementById('komut').value;
            if (!komut) return;
            localStorage.setItem('temel_sifre', sifre);
            document.getElementById('cevap').innerText = "Gönderiliyor...";
            fetch('/komut', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sifre: sifre, komut: komut})
            })
            .then(r => r.json())
            .then(data => { document.getElementById('cevap').innerText = data.cevap; })
            .catch(e => { document.getElementById('cevap').innerText = "Bağlantı hatası: " + e; });
        }

        document.getElementById('komut').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') gonder();
        });

        // Sesli komut (Android Chrome'un yerleşik ses tanıma özelliği)
        function sesleDinle() {
            const Tanima = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!Tanima) {
                document.getElementById('cevap').innerText = "Bu tarayıcı sesli komutu desteklemiyor.";
                return;
            }
            const tanima = new Tanima();
            tanima.lang = 'tr-TR';
            tanima.interimResults = false;

            const buton = document.getElementById('mikrofon');
            buton.classList.add('dinliyor');
            buton.innerText = "🎙️ Dinliyorum...";

            tanima.onresult = (event) => {
                const metin = event.results[0][0].transcript;
                document.getElementById('komut').value = metin;
                gonder();
            };
            tanima.onerror = () => {
                document.getElementById('cevap').innerText = "Ses tanıma hatası, tekrar dener misin?";
            };
            tanima.onend = () => {
                buton.classList.remove('dinliyor');
                buton.innerText = "🎙️ Sesli Komut";
            };
            tanima.start();
        }
    </script>
</body>
</html>
"""

if FLASK_MEVCUT:
    telefon_app = Flask(__name__)

    @telefon_app.route("/")
    def telefon_ana_sayfa():
        return TELEFON_SAYFA_HTML.replace("T.E.M.E.L.", HUD_BASLIK)

    @telefon_app.route("/komut", methods=["POST"])
    def telefon_komut_al():
        veri = request.get_json(force=True, silent=True) or {}
        gelen_sifre = str(veri.get("sifre") or "")
        if not TELEFON_SIFRE or not hmac.compare_digest(
                gelen_sifre.encode("utf-8"), TELEFON_SIFRE.encode("utf-8")):
            time.sleep(1)  # kaba kuvvet denemelerini yavaşlat
            return jsonify({"cevap": "Şifre yanlış."}), 401

        komut = (veri.get("komut") or "").strip()
        if not komut:
            return jsonify({"cevap": "Boş komut."}), 400

        try:
            threading.Thread(target=yazili_komut_isle, args=(komut,), daemon=True).start()
            return jsonify({"cevap": f"'{komut}' komutu asistana iletildi. Cevabı bilgisayarın hoparlöründen duyacaksın."})
        except Exception as e:
            return jsonify({"cevap": f"Hata: {e}"}), 500

TAILSCALE_MAGICDNS_ADI = os.getenv("TAILSCALE_MAGICDNS_ADI", "")
SERTIFIKA_DOSYASI = f"{TAILSCALE_MAGICDNS_ADI}.crt" if TAILSCALE_MAGICDNS_ADI else ""
ANAHTAR_DOSYASI = f"{TAILSCALE_MAGICDNS_ADI}.key" if TAILSCALE_MAGICDNS_ADI else ""

def telefon_sunucusunu_baslat():
    if not FLASK_MEVCUT:
        print("Flask kurulu olmadığı için telefon kontrol sunucusu başlatılamadı.")
        return

    if not TELEFON_SIFRE:
        print("TEMEL_TELEFON_SIFRE tanımlı değil; güvenlik için telefon kontrol sunucusu başlatılmadı.")
        return

    # TEMEL_TELEFON_HOST: varsayılan 127.0.0.1. Tailscale IP'ni (100.x.x.x) yazarsan sadece o ağdan erişilir.
    host = os.getenv("TEMEL_TELEFON_HOST", "127.0.0.1")

    if SERTIFIKA_DOSYASI and os.path.exists(SERTIFIKA_DOSYASI) and os.path.exists(ANAHTAR_DOSYASI):
        telefon_app.run(host=host, port=5005, debug=False, use_reloader=False,
                         ssl_context=(SERTIFIKA_DOSYASI, ANAHTAR_DOSYASI))
    else:
        print(f"Sertifika dosyaları ({SERTIFIKA_DOSYASI}) bulunamadı, HTTPS olmadan (http) başlatılıyor. "
              "'tailscale cert' komutunu çalıştırıp dosyaları temel.py ile aynı klasöre koy.")
        telefon_app.run(host=host, port=5005, debug=False, use_reloader=False)

if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    hud = TemelJarvisHUD()
    hud.show()

    bildirim_dinleyici_izin_al()  # İlk açılışta Windows izin penceresi çıkar (bir kerelik)

    kisayol_thread = threading.Thread(target=kisayol_dinleyici, daemon=True)
    kisayol_thread.start()

    asistan_thread = threading.Thread(target=asistan_dongusu, daemon=True)
    asistan_thread.start()

    proaktif_thread = threading.Thread(target=proaktif_konusma_dongusu, daemon=True)
    proaktif_thread.start()

    telefon_thread = threading.Thread(target=telefon_sunucusunu_baslat, daemon=True)
    telefon_thread.start()

    bildirim_thread = threading.Thread(target=bildirim_tarama_dongusu, daemon=True)
    bildirim_thread.start()

    sys.exit(qt_app.exec_())
