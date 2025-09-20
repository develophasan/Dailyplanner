from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import hashlib
import jwt
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import asyncio
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Environment variables
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
JWT_SECRET = os.environ.get('JWT_SECRET', 'maarif-secret-key-2024')

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# FastAPI app
app = FastAPI(title="MaarifPlanner API", version="1.0.0")

# CORS Configuration - COMPLETE RESET - MOVED TO TOP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Global OPTIONS handler for all routes
@app.options("/{path:path}")
async def options_handler(path: str):
    return {"message": "OK"}

api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Pydantic Models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    school: Optional[str] = None
    className: Optional[str] = None
    ageDefault: Optional[str] = "60_72"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    school: Optional[str]
    className: Optional[str]
    ageDefault: Optional[str]

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PlanGenerateRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    ageBand: str = "60_72"
    planType: str = "daily"  # "daily" or "monthly"

class DailyPlanCreate(BaseModel):
    date: str  # YYYY-MM-DD
    ageBand: str
    planJson: Dict[str, Any]
    title: Optional[str] = None

class MonthlyPlanCreate(BaseModel):
    month: str  # YYYY-MM
    ageBand: str
    planJson: Dict[str, Any]
    title: Optional[str] = None

class PortfolioPhotoCreate(BaseModel):
    planId: str
    activityTitle: str
    photoBase64: str
    description: Optional[str] = None

# Utility functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_jwt_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, jwt.DecodeError, Exception):
        raise HTTPException(status_code=401, detail="Invalid token")

# JSON Schema for AI responses
JSON_SCHEMA = {
    "type": "object",
    "required": ["finalize", "type", "ageBand", "date", "domainOutcomes", "blocks"],
    "properties": {
        "finalize": {"type": "boolean"},
        "type": {"enum": ["daily", "monthly"]},
        "ageBand": {"enum": ["36_48", "48_60", "60_72"]},
        "date": {"type": "string"},
        "domainOutcomes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {"type": "string"},
                    "indicators": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"}
                },
                "additionalProperties": True
            }
        },
        "conceptualSkills": {"type": "array", "items": {"type": "string"}},
        "dispositions": {"type": "array", "items": {"type": "string"}},
        "crossComponents": {"type": "object"},
        "contentFrame": {"type": "object"},
        "blocks": {
            "type": "object",
            "properties": {
                "startOfDay": {"type": "string"},
                "learningCenters": {"type": "array", "items": {"type": "string"}},
                "activities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {
                            "title": {"type": "string"},
                            "location": {"type": "string"},
                            "materials": {"type": "array", "items": {"type": "string"}},
                            "steps": {"type": "array", "items": {"type": "string"}},
                            "mapping": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "mealsCleanup": {"type": "array", "items": {"type": "string"}},
                "assessment": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["startOfDay", "activities", "assessment"]
        },
        "notes": {"type": "string"},
        "followUpQuestions": {"type": "array", "items": {"type": "string"}},
        "missingFields": {"type": "array", "items": {"type": "string"}}
    },
    "additionalProperties": True
}

SYSTEM_PROMPT = """Sen Türkiye Yüzyılı Maarif Modeli **Okul Öncesi** programına göre çalışan uzman bir PLAN ASİSTANI'sın.
Öğretmen isteklerini PROFESYONEL KALITEDE, MEB onaylı günlük planına dönüştürürsün. Yüklediğin PDF örneğindeki kaliteye ve detay seviyesine eşit planlar üreteceksin.

**MUTLAK KURALLAR:**
- Eksik bilgi varsa: "finalize": false, "followUpQuestions", "missingFields" doldur.
- Yeterli bilgi varsa: "finalize": true ve **HER BÖLÜMÜ PROFESYONEL SEVIYEDE** doldur.
- **GERÇEK ÖĞRETMEN PLANINA UYGUN** - Uygulanabilir, detaylı ve eğitim bilimsel temellerle hazırlanmış.
- **HER ETKİNLİK TAMAMEN GELİŞTİRİLMİŞ** olacak, sadece başlık değil tam içerik.

**TUTARLILIK VE BİRLİK KURALLARI:**
- **TÜM VERİLER TUTARLI VE BİRBİRİYLE İLİŞKİLİ OLMALI** - Etkinlikler, malzemeler, alan kodları, değerlendirme yöntemleri birbiriyle uyumlu
- **TEMA BÜTÜNLÜĞÜ** - Tüm etkinlikler aynı tema etrafında organize edilmeli
- **YAŞ GRUBUNA UYGUNLUK** - Tüm etkinlikler, malzemeler ve hedefler yaş grubuna uygun
- **SÜREKLİLİK** - Etkinlikler mantıklı sıra ve akışta, birbiriyle bağlantılı
- **GERÇEKÇİLİK** - Malzemeler ve etkinlikler okul ortamında uygulanabilir

**MEB GÜNLÜK PLAN YAPISI (Türkiye Yüzyılı Maarif Modeli):**

**1. PLAN TEMEL BİLGİLERİ:**
- Tarih (ISO format)
- Yaş bandı (36_48: 36-48 ay, 48_60: 48-60 ay, 60_72: 60-72 ay)
- Ana tema/konu
- Günlük süre (Tam gün/Yarım gün)

**2. ALAN BECERİLERİ (domainOutcomes) - MİNİMUM 3-4 FARKLI ALAN:**

**Türkçe Alanı (TAE):**
- TAEOB1: Erken Okuryazarlık Becerileri
- TAEOB2: Dinleme Becerileri  
- TAEOB3: Konuşma Becerileri
- TAEOB4: Öncül Yazma Becerileri

**Matematik Alanı (MAB):**
- MAB1: Sayı ve İşlemler
- MAB2: Ölçme
- MAB3: Geometri ve Mekân
- MAB4: Veri İşleme

**Fen Alanı (HSAB):**
- HSAB1: Canlılar Dünyası
- HSAB2: Madde ve Değişim
- HSAB3: Fiziksel Olaylar
- HSAB4: Dünya ve Evren

**Sanat Alanı (SNAB):**
- SNAB1: Sanatsal İfade
- SNAB2: Sanatsal Üretim
- SNAB3: Sanatsal Değerlendirme
- SNAB4: Sanatsal Uygulama Yapma

**Müzik Alanı (MHB):**
- MHB1: Müziksel Algı
- MHB2: Müziksel İfade
- MHB3: Müziksel Yaratıcılık
- MHB4: Müziksel Hareket Becerisi

**Sosyal-Duygusal Öğrenme (SDB):**
- SDB1: Sosyal Beceriler
- SDB2: İletişim Becerileri
- SDB3: Duygusal Beceriler

Her alan için zorunlu alanlar:
- "code": TAM alan kodu (örn: "TAEOB1", "MAB2", "SNAB4")
- "indicators": O alana özel 2-3 spesifik gösterge
- "notes": Nasıl destekleneceğine dair uygulama notu

**3. KAVRAMSAL BECERİLER (conceptualSkills) - 2-3 ana beceri:**
- KB2.9: Genelleme Becerisi
- KB2.1: Sınıflandırma Becerisi  
- KB2.5: Sebep-Sonuç İlişkisi Kurma
- KB2.3: Karşılaştırma Yapma
- KB2.7: Çıkarım Yapma

**4. EĞİLİMLER (dispositions) - 2-3 eğilim:**
- E1: Benlik Eğilimleri (merak, öz güven, girişimcilik)
- E2: Çevreyle İlgili Eğilimler (doğa sevgisi, çevre bilinci)
- E3: Entelektüel Eğilimler (odaklanma, yaratıcılık, eleştirel düşünme)
- E4: Sosyal Eğilimler (empati, iş birliği, adalet)

**5. DEĞERLER (values) - 2-3 değer:**
- D3: Çalışkanlık
- D19: Vatanseverlik
- D1: Adalet
- D5: Dostluk
- D12: Saygı

**6. PROGRAMLAR ARASI BİLEŞENLER (crossComponents):**
- Sosyal-Duygusal Öğrenme Becerileri (SDB)
- Değerler eğitimi
- Beceri temelli öğrenme

**7. ÖĞRENME ÇIKTILARI VE SÜREÇ BİLEŞENLERİ:**
Her alan için detaylı öğrenme çıktıları ve süreç bileşenleri

**8. İÇERİK ÇERÇEVESİ (contentFrame):**
- Kavramlar (büyük-küçük, başlangıç-bitiş, vb.)
- Sözcükler (tema ile ilgili)
- Materyaller (fotoğraflı isim kartları, etiketler, vb.)

**9. ÖĞRENME-ÖĞRETME YAŞANTILARI (blocks) - HER BÖLÜM DETAYLI:**

**a) Güne Başlama Zamanı (startOfDay):**
- Açılış rutini ve sohbet
- Yoklama/devam (yaratıcı yöntemlerle)
- Günün planının tanıtımı
- Merkez seçimi ve organizasyon
- 4-5 cümle detaylı açıklama

**b) Öğrenme Merkezlerinde Oyun (learningCenters) - 6-8 merkez:**
["Matematik merkezi", "Türkçe merkezi", "Sanat merkezi", "Fen keşif merkezi", "Oyun merkezi", "Müzik merkezi", "Yaşam becerileri merkezi", "Kitap merkezi"]

**c) Etkinlikler (activities) - MİNİMUM 3-4 KAPSAMLI ETKİNLİK:**

Her etkinlik için ZORUNLU detaylı alanlar:
- "title": Yaratıcı ve açıklayıcı etkinlik adı
- "location": Hangi merkez/alan (spesifik)
- "duration": Gerçekçi süre (dakika olarak)
- "materials": 8-12 spesifik malzeme listesi
- "steps": 8-12 detaylı, uygulanabilir adım
- "mapping": İlgili alan kodları (3-4 kod)
- "objectives": 3-4 spesifik öğretimsel hedef
- "differentiation": Bireysel farklılıklar için detaylı uyarlama önerileri

**d) Beslenme, Toplanma, Temizlik (mealsCleanup) - 5-6 rutin:**
Günlük yaşam becerileri ve sosyal öğrenmeyi destekleyici rutinler

**e) Değerlendirme (assessment) - 5-7 çeşitli yöntem:**
- Gözlem formları
- Anekdot kayıtları
- Fotoğraf dokümantasyonu
- Çocukla bireysel görüşme
- Portfolyo çalışması
- Akran değerlendirmesi
- Öz değerlendirme

**10. FARKLILAŞTIRMA:**
- "enrichment": Zenginleştirme etkinlikleri
- "support": Destek gereken çocuklar için uyarlama

**11. AİLE/TOPLUM KATILIMI:**
- Ailenin sürece katılım önerileri
- Ev etkinlikleri
- Toplumsal bağlantılar

**ÖRNEK PROFESYONEL GÜNLÜK PLAN:**
```json
{
  "finalize": true,
  "type": "daily",
  "ageBand": "60_72",
  "date": "2025-09-20",
  "theme": "İsimler ve Kimlik",
  "domainOutcomes": [
    {
      "code": "TAEOB1",
      "indicators": ["Sözcüklerin harflerden oluştuğunu fark eder", "Büyük ve küçük harfleri ayırt eder", "İsminin harflerini tanır"],
      "notes": "Fotoğraflı isim kartları ile somutlaştırılır"
    },
    {
      "code": "SNAB4", 
      "indicators": ["Bireysel sanat etkinliğinde aktif rol alır", "Yaratıcı ürünler oluşturur", "Sanatsal çalışmasını sergiler"],
      "notes": "Otoportre çizimi ile desteklenir"
    },
    {
      "code": "MHB4",
      "indicators": ["Müzik eşliğinde hareket eder", "Ritim tutarak dans eder", "Şarkı söylerken hareket eder"],
      "notes": "İsim şarkıları ve hareketli oyunlarla"
    },
    {
      "code": "SDB2",
      "indicators": ["Grup iletişimine katılır", "Fikirlerini arkadaşları ile paylaşır", "Sohbet kurallarına uyar"],
      "notes": "İsim paylaşım etkinlikleriyle"
    }
  ],
  "conceptualSkills": ["KB2.9: Genelleme Becerisi"],
  "dispositions": ["E1: Benlik Eğilimleri (merak)", "E3: Entelektüel Eğilimler (odaklanma, yaratıcılık)"],
  "values": ["D3: Çalışkanlık", "D19: Vatanseverlik"],
  "crossComponents": {
    "socialEmotionalLearning": "SDB2.1: İletişim Becerisi - grup iletişimine katılma",
    "values": ["D3: Çalışkanlık", "D19: Vatanseverlik"],
    "literacy": "Erken okuryazarlık becerileri"
  },
  "learningOutcomes": {
    "turkish": "Sözcüklerin harflerden oluştuğunu fark etme, büyük-küçük harfleri ayırt etme",
    "art": "Bireysel veya grup çalışması içinde sanat etkinliklerinde aktif rol alma",
    "music": "Hareket ve dans etme becerilerini geliştirme"
  },
  "contentFrame": {
    "concepts": ["büyük-küçük", "başlangıç-bitiş", "benzer-farklı"],
    "vocabulary": ["isim", "harf", "sözcük", "başlangıç"],
    "materials": ["fotoğraflı isim kartları", "etiketler", "boyama malzemeleri", "müzik aleti"]
  },
  "blocks": {
    "startOfDay": "Güne fotoğraflı isim kartları ile başlarız. Her çocuk kendi kartını bulur ve ismini yüksek sesle söyler. İsim kartlarında harfleri incelenir, büyük-küçük harfler tanıtılır. Sınıf içinde isim kartları ile düzenleme yapılır. Günün etkinlikleri tanıtılarak çocuklar merkez seçimi yapar.",
    "learningCenters": ["Matematik merkezi", "Türkçe merkezi", "Sanat merkezi", "Fen keşif merkezi", "Oyun merkezi", "Müzik merkezi", "Yaşam becerileri merkezi", "Kitap merkezi"],
    "activities": [
      {
        "title": "Fotoğraflı İsim Kartları ile Harf Keşfi",
        "location": "Türkçe merkezi ve sohbet halısı",
        "duration": "30 dakika",
        "materials": ["Fotoğraflı isim kartları", "Büyük boyutlu harfler", "Magnifier", "Renkli kalemler", "Büyük kağıtlar", "Harf damgaları", "İsim etiketleri", "Sınıf listesi", "Ayna", "Harf puzzle'ları"],
        "steps": [
          "Çocuklar halı üzerinde daire şeklinde oturur",
          "Her çocuk kendi fotoğraflı isim kartını bulur",
          "İsim kartlarındaki harfler magnifier ile incelenir",
          "Büyük ve küçük harfler karşılaştırılır ve ayrılır",
          "Her çocuk isminin ilk harfini büyük harfler arasından bulur",
          "Aynı harfle başlayan isimleri gruplarız",
          "İsim kartlarını alfabetik sıraya dizmeye çalışırız",
          "Her çocuk ismini harf damgaları ile büyük kağıda yazar",
          "İsimlerin uzunluğunu sayıp karşılaştırırız",
          "Ortak harfleri olan isimleri buluruz",
          "Her çocuk kendi ismini aynada söyleyerek kimlik bağlantısı kurar"
        ],
        "mapping": ["TAEOB1.a", "TAEOB1.b", "SDB2.a", "KB2.9"],
        "objectives": ["Harflerin sözcükleri oluşturduğunu kavrama", "Büyük-küçük harf ayrımı yapma", "İsim-kimlik bağlantısı oluşturma", "Alfabetik düzen kavramını geliştirme"],
        "differentiation": "İleri düzey çocuklar kendi isimlerini yazabilir, destek isteyen çocuklar harf çıkartmaları kullanabilir, özel gereksinimi olan çocuklar için dokunsal harf kartları kullanılır"
      },
      {
        "title": "Benliğimi Tanıyorum: Otoportre Çizimi",
        "location": "Sanat merkezi",
        "duration": "40 dakika",
        "materials": ["Büyük boyutlu kağıtlar", "Pastel boyalar", "Aynalar", "Renkli kalemler", "Sulu boyalar", "Fırçalar", "Fotoğraflar", "Kolaj malzemeleri", "Yuvarlak çerçeveler", "Makaslar", "Tutkallar"],
        "steps": [
          "Her çocuk kendi aynasına bakarak yüz özelliklerini inceler",
          "Göz, burun, ağız şekillerini aynada gözlemler",
          "Saç rengi ve şeklini fark eder, tanımlar",
          "Büyük kağıda kalem ile yüz şeklini çizer",
          "Göz, burun, ağız detaylarını ekler",
          "Saç şeklini ve rengini boyarla tamamlar",
          "Kendi fotoğrafı ile çizimini karşılaştırır",
          "Benzerlik ve farklılıkları arkadaşları ile paylaşır",
          "Çizimini pastel boyalar ile renklendirir",
          "Çerçeveleyerek özel hale getirir",
          "Her çocuk çalışmasını tanıtır ve sergiler"
        ],
        "mapping": ["SNAB4.a", "SNAB4.b", "E1.a", "SDB2.b"],
        "objectives": ["Benlik algısını güçlendirme", "Yaratıcı ifade becerilerini geliştirme", "Kendini tanıma ve tanıtma", "Sanatsal çalışmada özgüven kazanma"],
        "differentiation": "Çizim zorluğu yaşayan çocuklar kolaj tekniği kullanabilir, detaycı çocuklar gözlük, takı gibi aksesuar ekleyebilir, utangaç çocuklar partneri ile çalışabilir"
      },
      {
        "title": "İsimle Dans: Müzikli Hareket Atölyesi",
        "location": "Müzik merkezi ve açık alan", 
        "duration": "25 dakika",
        "materials": ["Ritim aletleri", "Müzik çalar", "İsim şarkıları", "Renkli eşarplar", "Davul", "Marakas", "Çıngırak", "Hareket kartları", "Tempo şarkıları"],
        "steps": [
          "Çocuklar daire şeklinde oturarak müzik dinler",
          "Her çocuk isminin hecelerini alkışlar",
          "İsmin hecesi kadar dans adımı atar",
          "Uzun isimli çocuklar tempo hızlı dans eder",
          "Kısa isimli çocuklar yavaş ve akıcı hareket eder",
          "İsim şarkısı söyleyerek grup dansı yapar",
          "Her çocuk kendi ismini şarkıya dönüştürür",
          "Ritim aleti seçerek ismini çalar",
          "Partneri ile isim şarkısı söyler",
          "Serbest dans ile müzik dinleme zamanı"
        ],
        "mapping": ["MHB4.a", "MHB4.b", "TAEOB3.a", "SDB2.c"],
        "objectives": ["Müzik ile hareket koordinasyonu", "İsim-ritim bağlantısı kurma", "Müziksel ifade geliştirme", "Grup etkinliğinde aktif katılım"],
        "differentiation": "Utangaç çocuklar küçük grup ile başlar, müzik yeteneği olan çocuklar liderlik yapar, hareket zorluğu olan çocuklar oturarak katılır"
      }
    ],
    "mealsCleanup": [
      "Kahvaltı öncesi el yıkama rutini ve sofra hazırlığı",
      "Kahvaltı sırasında sağlıklı beslenme ve isim paylaşım sohbeti",
      "Öğle yemeği öncesi masa sorumluları seçimi ve işbölümü",
      "Yemek sonrası kendi alanını temizleme sorumluluğu",
      "Atıştırmalık zamanında paylaşım kuralları ve nezaket",
      "Günlük sınıf temizliği işbirliği ile yapma"
    ],
    "assessment": [
      "Gözlem formu ile harf tanıma becerileri takibi",
      "Anekdot kayıtları ile sosyal etkileşim becerileri",
      "Fotoğraf dokümantasyonu ile sanat çalışması gelişimi",
      "Çocukla bireysel görüşme: 'Her şeyin bir ismi var mı?'",
      "Çalışma portfolyosu: otoportre gelişim takibi",
      "Akran değerlendirmesi: arkadaşının sanat çalışması hakkında",
      "Öz değerlendirme: 'Bugün ismim hakkında neler öğrendim?'"
    ]
  },
  "differentiation": {
    "enrichment": "Kelime atölyesi oluşturma, farklı dillerdeki isimler araştırması, aile isim ağacı projesi",
    "support": "Görsel destek kartları, dokunsal harf materyalleri, fotoğraflı adım kartları"
  },
  "familyCommunityInvolvement": "Ailelerden çocuğun isminin anlamı ve seçim öyküsü paylaşımı, ev ödevi: aile üyelerinin isimlerini öğrenme",
  "notes": "Hava durumu ve çocukların dikkat süresine göre etkinlik süreleri ayarlanabilir. Bireysel tempo farklılıkları dikkate alınır.",
  "duration": "Tam gün",
  "groupSize": "20 çocuk"
}
```

**Vector store'dan yararlanarak** gerçek Türkiye Yüzyılı Maarif Modeli içeriklerini kullan.
**SADECE JSON FORMATINDA CEVAP VER, HİÇBİR AÇIKLAMA YAPMA. TÜM ALANLAR PROFESYONEL SEVİYEDE DOLU OLMALI.**"""

# Auth Routes
@api_router.options("/auth/register")
async def register_options():
    return {}

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = {
        "email": user_data.email,
        "passwordHash": hash_password(user_data.password),
        "name": user_data.name,
        "school": user_data.school,
        "className": user_data.className,
        "ageDefault": user_data.ageDefault,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    token = create_jwt_token(str(result.inserted_id))
    
    return {
        "token": token,
        "user": {
            "id": str(result.inserted_id),
            "email": user_data.email,
            "name": user_data.name,
            "school": user_data.school,
            "className": user_data.className,
            "ageDefault": user_data.ageDefault
        }
    }

@api_router.options("/auth/login")
async def login_options():
    return {}

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_jwt_token(str(user["_id"]))
    
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "school": user.get("school"),
            "className": user.get("className"),
            "ageDefault": user.get("ageDefault", "60_72")
        }
    }

@api_router.options("/auth/me")
async def auth_me_options():
    return {"message": "OK"}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "name": current_user["name"],
        "school": current_user.get("school"),
        "className": current_user.get("className"),
        "ageDefault": current_user.get("ageDefault", "60_72")
    }

# AI Chat Routes
@api_router.options("/ai/chat")
async def chat_options():
    return {"message": "OK"}

@api_router.post("/ai/chat")
async def generate_plan(request: PlanGenerateRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Get user's default age band and today's date
        user_age_band = current_user.get("ageDefault", "60_72")
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Enhanced system prompt with user context
        enhanced_system_prompt = f"""{SYSTEM_PROMPT}

**BU PLAN İÇİN ZORUNLU CONTEXT:**
- **BUGÜNÜN TARİHİ**: {today_date} (bu tarihi kullan)
- **ÖĞRETMENİN YAŞ GRUBU**: {user_age_band} (bu yaş grubu için plan yap)
- **ÖĞRETMEN BİLGİLERİ**: {current_user.get('name', 'Öğretmen')} - {current_user.get('school', 'Okul')} - {current_user.get('className', 'Sınıf')}

**OTOMATIK KULLANIM:**
- Plan tarihini {today_date} olarak ayarla
- Yaş bandını {user_age_band} olarak ayarla
- Tema belirtilmemişse güncel eğitim konularından uygun tema seç
- Tüm etkinlikler birbiriyle tutarlı ve temaya uygun olsun"""

        # Initialize LLM chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"user_{current_user['_id']}_{datetime.utcnow().isoformat()}",
            system_message=enhanced_system_prompt
        ).with_model("openai", "gpt-4o")
        
        # Build conversation history
        conversation_text = ""
        for msg in request.history:
            conversation_text += f"{msg.role}: {msg.content}\n"
        conversation_text += f"user: {request.message}"
        
        # Send message to AI
        user_message = UserMessage(text=conversation_text)
        response_text = await chat.send_message(user_message)
        
        # Parse JSON response
        try:
            ai_response = json.loads(response_text)
        except json.JSONDecodeError:
            # Extract JSON from response if wrapped in text
            import re
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                ai_response = json.loads(match.group())
            else:
                raise HTTPException(status_code=500, detail="Invalid AI response format")
        
        # Save chat history
        chat_record = {
            "userId": ObjectId(current_user["_id"]),
            "message": request.message,
            "response": ai_response,
            "timestamp": datetime.utcnow(),
            "ageBand": request.ageBand,
            "planType": request.planType
        }
        await db.chat_history.insert_one(chat_record)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# Plan Routes
@api_router.options("/plans/daily")
async def plans_daily_options():
    return {"message": "OK"}

@api_router.post("/plans/daily")
async def create_daily_plan(plan_data: DailyPlanCreate, current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Creating daily plan for user {current_user['_id']}: {plan_data}")
        
        # Validate date format
        try:
            plan_date = datetime.fromisoformat(plan_data.date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD format.")
        
        plan_dict = {
            "userId": ObjectId(current_user["_id"]),
            "date": plan_date,
            "ageBand": plan_data.ageBand,
            "planJson": plan_data.planJson,
            "title": plan_data.title or f"Günlük Plan - {plan_data.date}",
            "createdAt": datetime.utcnow(),
            "pdfUrl": None
        }
        
        result = await db.daily_plans.insert_one(plan_dict)
        plan_dict["_id"] = result.inserted_id
        
        logger.info(f"Daily plan created successfully with id: {result.inserted_id}")
        
        return {
            "id": str(result.inserted_id),
            "message": "Daily plan created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating daily plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating plan: {str(e)}")

@api_router.get("/plans/daily")
async def get_daily_plans(current_user: dict = Depends(get_current_user), 
                         from_date: Optional[str] = None, 
                         to_date: Optional[str] = None):
    query = {"userId": ObjectId(current_user["_id"])}
    
    if from_date and to_date:
        query["date"] = {
            "$gte": datetime.fromisoformat(from_date),
            "$lte": datetime.fromisoformat(to_date)
        }
    
    plans = await db.daily_plans.find(query).sort("date", -1).to_list(100)
    
    return [
        {
            "id": str(plan["_id"]),
            "date": plan["date"].isoformat(),
            "ageBand": plan["ageBand"],
            "title": plan.get("title", ""),
            "createdAt": plan["createdAt"].isoformat(),
            "pdfUrl": plan.get("pdfUrl")
        }
        for plan in plans
    ]

@api_router.get("/plans/daily/{plan_id}")
async def get_daily_plan(plan_id: str, current_user: dict = Depends(get_current_user)):
    try:
        plan = await db.daily_plans.find_one({
            "_id": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"])
        })
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        return {
            "id": str(plan["_id"]),
            "date": plan["date"].isoformat(),
            "ageBand": plan["ageBand"],
            "title": plan.get("title", ""),
            "planJson": plan["planJson"],
            "createdAt": plan["createdAt"].isoformat(),
            "pdfUrl": plan.get("pdfUrl")
        }
    except Exception as e:
        logger.error(f"Get plan error: {str(e)}")
        raise HTTPException(status_code=404, detail="Invalid plan ID")

@api_router.post("/plans/monthly")
async def create_monthly_plan(plan_data: MonthlyPlanCreate, current_user: dict = Depends(get_current_user)):
    plan_dict = {
        "userId": ObjectId(current_user["_id"]),
        "month": plan_data.month,
        "ageBand": plan_data.ageBand,
        "planJson": plan_data.planJson,
        "title": plan_data.title or f"Aylık Plan - {plan_data.month}",
        "createdAt": datetime.utcnow(),
        "pdfUrl": None
    }
    
    result = await db.monthly_plans.insert_one(plan_dict)
    
    return {
        "id": str(result.inserted_id),
        "message": "Monthly plan created successfully"
    }

@api_router.get("/plans/monthly")
async def get_monthly_plans(current_user: dict = Depends(get_current_user)):
    plans = await db.monthly_plans.find({"userId": ObjectId(current_user["_id"])}).sort("month", -1).to_list(100)
    
    return [
        {
            "id": str(plan["_id"]),
            "month": plan["month"],
            "ageBand": plan["ageBand"],
            "title": plan.get("title", ""),
            "createdAt": plan["createdAt"].isoformat(),
            "pdfUrl": plan.get("pdfUrl")
        }
        for plan in plans
    ]

# Matrix/Search Routes
@api_router.get("/matrix/search")
async def search_matrix(q: str = "", ageBand: str = ""):
    # This would search through the Maarif program data
    # For now, return mock data
    results = [
        {
            "code": "MAB.1",
            "title": "Matematik Alan Becerisi 1",
            "ageBand": "60_72",
            "description": "Sayıları tanır ve sayar"
        },
        {
            "code": "TADB.2.a",
            "title": "Türkçe Dil Becerileri",
            "ageBand": "60_72", 
            "description": "Dinlediğini anlar"
        }
    ]
    
    if q:
        results = [r for r in results if q.lower() in r["code"].lower() or q.lower() in r["title"].lower()]
    
    if ageBand:
        results = [r for r in results if r["ageBand"] == ageBand]
    
    return results

# Plan Delete Routes
@api_router.delete("/plans/daily/{plan_id}")
async def delete_daily_plan(plan_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = await db.daily_plans.delete_one({
            "_id": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"])
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        logger.info(f"Daily plan deleted: {plan_id} by user {current_user['_id']}")
        return {"message": "Plan deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting daily plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.delete("/plans/monthly/{plan_id}")
async def delete_monthly_plan(plan_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = await db.monthly_plans.delete_one({
            "_id": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"])
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        logger.info(f"Monthly plan deleted: {plan_id} by user {current_user['_id']}")
        return {"message": "Plan deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting monthly plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Portfolio Routes
@api_router.post("/plans/daily/{plan_id}/portfolio")
async def add_portfolio_photo(
    plan_id: str, 
    portfolio_data: PortfolioPhotoCreate,
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verify plan belongs to user
        plan = await db.daily_plans.find_one({
            "_id": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"])
        })
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        # Create portfolio entry
        portfolio_entry = {
            "_id": ObjectId(),
            "planId": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"]),
            "activityTitle": portfolio_data.activityTitle,
            "photoBase64": portfolio_data.photoBase64,
            "description": portfolio_data.description,
            "uploadedAt": datetime.utcnow()
        }
        
        # Insert into portfolio collection
        result = await db.portfolio_photos.insert_one(portfolio_entry)
        
        logger.info(f"Portfolio photo added to plan {plan_id} by user {current_user['_id']}")
        
        return {
            "id": str(result.inserted_id),
            "message": "Portfolio photo added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error adding portfolio photo: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/plans/daily/{plan_id}/portfolio")
async def get_portfolio_photos(plan_id: str, current_user: dict = Depends(get_current_user)):
    try:
        # Verify plan belongs to user
        plan = await db.daily_plans.find_one({
            "_id": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"])
        })
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        # Get portfolio photos
        photos = await db.portfolio_photos.find({
            "planId": ObjectId(plan_id),
            "userId": ObjectId(current_user["_id"])
        }).sort("uploadedAt", -1).to_list(length=100)
        
        return [
            {
                "id": str(photo["_id"]),
                "activityTitle": photo["activityTitle"],
                "photoBase64": photo["photoBase64"],
                "description": photo.get("description"),
                "uploadedAt": photo["uploadedAt"].isoformat()
            }
            for photo in photos
        ]
        
    except Exception as e:
        logger.error(f"Error getting portfolio photos: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.delete("/portfolio/{photo_id}")
async def delete_portfolio_photo(photo_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = await db.portfolio_photos.delete_one({
            "_id": ObjectId(photo_id),
            "userId": ObjectId(current_user["_id"])
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Portfolio photo not found")
            
        logger.info(f"Portfolio photo deleted: {photo_id} by user {current_user['_id']}")
        return {"message": "Portfolio photo deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting portfolio photo: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Include router in app
app.include_router(api_router)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.daily_plans.create_index([("userId", 1), ("date", -1)])
    await db.monthly_plans.create_index([("userId", 1), ("month", -1)])
    await db.chat_history.create_index([("userId", 1), ("timestamp", -1)])
    await db.portfolio_photos.create_index([("planId", 1), ("userId", 1)])
    await db.portfolio_photos.create_index([("userId", 1), ("uploadedAt", -1)])
    logger.info("Database indexes created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()