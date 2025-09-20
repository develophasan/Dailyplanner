from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
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
Öğretmen isteklerini TAM KAPSAMLI günlük planına dönüştürürsün. Cevabın **yalnızca JSON** olacak ve verilen şemaya mükemmel uyacak.

**MUTLAK KURALLAR:**
- Eksik bilgi varsa: "finalize": false, "followUpQuestions", "missingFields" doldur.
- Yeterli bilgi varsa: "finalize": true ve **TÜM alanları detayca doldur**.
- **HİÇBİR ALAN BOŞ BIRAKILMAYACAK** - Her bölüm zengin içerikle dolu olmalı.

**KAPSAMLI GÜNLÜK PLAN YAPISI (Zorunlu Tüm Alanlar):**

**1. PLAN BİLGİLERİ:**
- Tarih (ISO format)
- Yaş bandı (36_48, 48_60, 60_72)
- Tema/konu (eğer belirtilmişse)

**2. HEDEFLENEN ALANLAR (domainOutcomes) - MİNİMUM 4-5 ALAN:**
- **TADB (Türkçe):** TADB.1, TADB.2, TADB.3 vb.
- **MAB (Matematik):** MAB.1, MAB.2, MAB.3 vb.
- **HSAB (Fen):** HSAB.1, HSAB.2, HSAB.3 vb.
- **SNAB (Sanat):** SNAB.1, SNAB.2, SNAB.3 vb.
- **SDB (Sosyal-Duygusal):** SDB.1, SDB.2, SDB.3 vb.
- **MHB (Hareket):** MHB.1, MHB.2, MHB.3 vb.

Her alan için:
- "code": Alan kodu (örn: "TADB.1")
- "indicators": Detaylı göstergeler listesi (min 2-3 gösterge)
- "notes": Uygulama notları

**3. KAVRAMSAL BECERİLER (conceptualSkills) - 3-4 beceri:**
Örn: ["Genelleme yapma", "Sınıflandırma", "Sebep-sonuç ilişkisi kurma", "Karşılaştırma"]

**4. EĞİLİMLER (dispositions) - 3-4 eğilim:**
Örn: ["Meraklılık", "Yaratıcılık", "İş birliği", "Sorumluluk"]

**5. GÜNLÜK PROGRAM BLOKLARI (blocks) - HER BÖLÜM DETAYLI:**

**a) Güne Başlama (startOfDay):**
- Açılış rutin aktiviteleri
- Yoklama/devam
- Günün planını tanıtma
- Sohbet zamanı
- Min. 3-4 cümle detay

**b) Öğrenme Merkezleri (learningCenters) - 5-6 merkez:**
Örn: ["Matematik merkezi", "Türkçe merkezi", "Sanat merkezi", "Fen merkezi", "Oyun merkezi", "Müzik merkezi"]

**c) Etkinlikler (activities) - MİNİMUM 3-4 ETKİNLİK:**
Her etkinlik için ZORUNLU alanlar:
- "title": Etkinlik adı
- "location": Nerede yapılacak
- "duration": Süre (dakika)
- "materials": Malzeme listesi (5-8 malzeme)
- "steps": Detaylı adımlar (6-10 adım)
- "mapping": Hangi kodlarla eşleşiyor
- "objectives": Hedefler
- "differentiation": Bireysel farklılıklar için uyarlama

**d) Beslenme/Temizlik (mealsCleanup) - 4-5 madde:**
Örn: ["Kahvaltı öncesi el yıkama", "Kahvaltı zamanı sohbet", "Öğle yemeği masa düzeni", "Atıştırmalık paylaşımı", "Günlük temizlik rutin"]

**e) Değerlendirme (assessment) - 5-6 yöntem:**
Örn: ["Gözlem formu", "Anekdot kayıt", "Fotoğraf dokümantasyonu", "Çocuk ile bireysel sohbet", "Çalışma örnekleri", "Akran değerlendirmesi"]

**6. EK ALANLAR:**
- "notes": Genel notlar (2-3 cümle)
- "crossComponents": Çapraz bileşenler
- "contentFrame": İçerik çerçevesi

**ÖRNEK TAM YAPISIZ GÜNLÜK PLAN:**
```json
{
  "finalize": true,
  "type": "daily",
  "ageBand": "60_72",
  "date": "2025-09-20",
  "domainOutcomes": [
    {
      "code": "TADB.1",
      "indicators": ["Dinlediğini sözcüklerle ifade eder", "Dinlediklerini çizer", "Dinledikleri hakkında sorular sorar"],
      "notes": "Hikaye anlatım tekniği ile desteklenir"
    },
    {
      "code": "MAB.2",
      "indicators": ["1-20 arası sayıları tanır", "Somut nesnelerle sayma yapar", "Sayıları sıralar"],
      "notes": "Oyun malzemeleri ile somutlaştırılır"
    },
    {
      "code": "SNAB.3",
      "indicators": ["Çeşitli malzemeler ile yaratıcı çalışmalar yapar", "Renkleri karıştırır", "Çizgisel çalışmalar yapar"],
      "notes": "Doğal malzemeler tercih edilir"
    },
    {
      "code": "SDB.1",
      "indicators": ["Arkadaşları ile iş birliği yapar", "Duygularını ifade eder", "Sosyal kurallara uyar"],
      "notes": "Grup etkinlikleri ile desteklenir"
    }
  ],
  "conceptualSkills": ["Genelleme yapma", "Sınıflandırma", "Sebep-sonuç ilişkisi", "Karşılaştırma yapma"],
  "dispositions": ["Meraklılık", "Yaratıcılık", "İş birliği yapma", "Sorumluluk alma"],
  "blocks": {
    "startOfDay": "Günaydın şarkısı ile güne başlarız. Her çocuk ismini söyleyerek yoklamaya katılır. Bugünün tarihini ve hava durumunu konuşuruz. Günün planını çocuklarla birlikte gözden geçiririz. Serbest sohbet zamanı ile günün ruh halini değerlendiririz.",
    "learningCenters": ["Matematik merkezi", "Türkçe merkezi", "Sanat merkezi", "Fen keşif merkezi", "Oyun merkezi", "Müzik merkezi"],
    "activities": [
      {
        "title": "Sayılarla Hikaye Anlatma",
        "location": "Türkçe ve matematik merkezi",
        "duration": "25 dakika",
        "materials": ["Sayılı hikaye kartları", "Boyama kalemleri", "Büyük kağıtlar", "Sayı küpleri", "Hikaye kitabı", "Mıknatıslı tahta", "Hikaye karakterleri", "Sticker'lar"],
        "steps": [
          "Çocuklar daire şeklinde oturur",
          "Sayılı hikaye kartları tanıtılır",
          "Her çocuk bir sayı kartı seçer",
          "Kartlardaki sayıları birlikte sayarız",
          "Seçilen sayılar ile hikaye oluştururuz",
          "Her çocuk kendi kartı ile hikayeye katkı sağlar",
          "Oluşturulan hikaye büyük kağıda çizilir",
          "Hikaye sesli okunur",
          "Çocuklar hikayeyi tekrar anlatır",
          "Hikaye karakterleri ile rol yapma oyunu oynanır"
        ],
        "mapping": ["TADB.1.a", "MAB.2.b", "SDB.1.c"],
        "objectives": ["Dinleme becerisi geliştirme", "Sayıları tanıma ve kullanma", "Yaratıcı düşünce geliştirme"],
        "differentiation": "İleri düzey çocuklar hikayeyi yazabilir, destek isteyen çocuklar çizim ile desteklenir"
      },
      {
        "title": "Doğa Sanatı Atölyesi",
        "location": "Sanat merkezi ve bahçe",
        "duration": "35 dakika",
        "materials": ["Doğal malzemeler", "Toprak", "Yapraklar", "Taşlar", "Dal parçaları", "Kuş tüyleri", "Tutkal", "Karton", "Su kapları"],
        "steps": [
          "Bahçeye çıkarak doğal malzeme toplarız",
          "Toplanan malzemeler sınıflandırılır",
          "Her çocuk kendi sanat projesini planlar",
          "Doğal malzemeler ile kolaj çalışması yapılır",
          "Renkli yapraklar desenler oluşturur",
          "Taşlar boyama ve süsleme için kullanılır",
          "Su ile toprak karıştırılarak doğal boya elde edilir",
          "Projeler kurumaya bırakılır",
          "Her çocuk çalışmasını tanıtır",
          "Çalışmalar sergi panosuna asılır"
        ],
        "mapping": ["SNAB.3.a", "HSAB.1.b", "MHB.1.a"],
        "objectives": ["Doğal malzemelerle yaratıcılık", "Çevre bilinci geliştirme", "El becerilerini güçlendirme"],
        "differentiation": "Küçük kas becerisi gelişmemiş çocuklar için büyük malzemeler, ileri düzey çocuklar detaylı desenler yapabilir"
      },
      {
        "title": "Harpmü Ritim Atölyesi",
        "location": "Müzik merkezi",
        "duration": "20 dakika", 
        "materials": ["Davul", "Marakas", "Çıngırak", "Ritim çubukları", "Müzik çalar", "Şarkı kartları", "Eşarp", "Çember"],
        "steps": [
          "Çocuklar çember şeklinde otururlar",
          "Müzik aletleri tanıtılır",
          "Her çocuk bir müzik aleti seçer",
          "Basit ritimler öğretilir",
          "Müzik eşliğinde ritim tutulur",
          "Şarkı söyleyerek dans edilir",
          "Çiftler halinde müzik yapılır",
          "Serbest müzik ve hareket zamanı",
          "Müzik aletleri toplanır",
          "Sakin müzik eşliğinde nefes egzersizi"
        ],
        "mapping": ["MHB.2.a", "SDB.2.b", "TADB.3.c"],
        "objectives": ["Ritim duygusunu geliştirme", "Müzik ile ifade etme", "Sosyal etkileşimi artırma"], 
        "differentiation": "Utangaç çocuklar için eşli çalışma, müzik yeteneği olan çocuklar liderlik yapar"
      }
    ],
    "mealsCleanup": [
      "Kahvaltı öncesi eller yıkanır ve masa düzeni sağlanır",
      "Kahvaltı sırasında besin grupları hakkında sohbet edilir", 
      "Öğle yemeği öncesi masa sorumluları belirlenir",
      "Yemek sonrası çocuklar kendi yerlerini temizler",
      "Atıştırmalık zamanında paylaşım kuralları uygulanır",
      "Günlük sınıf temizliği birlikte yapılır"
    ],
    "assessment": [
      "Gözlem formu ile bireysel gelişim takibi",
      "Anekdot kayıtları ile özel anların belgelenmesi",
      "Fotoğraf ile etkinlik süreçlerinin dokümantasyonu", 
      "Çocukla bireysel görüşme ve yansıtma",
      "Çalışma örnekleri ile portfolyo oluşturma",
      "Akran değerlendirmesi ile sosyal becerileri gözlemleme",
      "Öz değerlendirme için çocukla sohbet"
    ]
  },
  "notes": "Hava durumu ve çocukların ilgisine göre etkinlik sırası değiştirilebilir. Bireysel ihtiyaçlara göre uyarlamalar yapılabilir.",
  "crossComponents": {"values": ["Dürüstlük", "Yardımseverlik"], "literacy": "Görsel okuryazarlık"},
  "contentFrame": {"theme": "Doğa ve sanat", "duration": "Tam gün", "groupSize": "15-20 çocuk"}
}
```

Program metni (2024programokuloncesiOnayli.pdf) ile eşleşen içerik için dosya araması kullan.
**SADECE JSON ÜRET, HİÇBİR AÇIKLAMA YAPMA. TÜM ALANLAR DOLU OLMALI.**"""

# Auth Routes
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
@api_router.post("/ai/chat")
async def generate_plan(request: PlanGenerateRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Initialize LLM chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"user_{current_user['_id']}_{datetime.utcnow().isoformat()}",
            system_message=SYSTEM_PROMPT
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

# Include router in app
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info("Database indexes created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()