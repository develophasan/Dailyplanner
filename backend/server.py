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

SYSTEM_PROMPT = """Sen Türkiye Yüzyılı Maarif Modeli **Okul Öncesi** programına göre çalışan bir PLAN ASİSTANI'sın.
Öğretmen günlük veya aylık planını serbest metinle söyler. Cevabın **yalnızca JSON** olacak ve verilen şemaya uyacak.

Kurallar:
- Eksik bilgi varsa: "finalize": false, "followUpQuestions": (kısa, madde madde), "missingFields" doldur.
- Yeterli bilgi varsa: "finalize": true ve tüm zorunlu alanları doldur.
- Kod örnekleri: MAB.2, MAB.2.a; HSAB.1.a; SNAB2.c; SDB2.1.SB1; TADB.1…
- Yaş bantları: 36_48, 48_60, 60_72
- Program metni (2024programokuloncesiOnayli.pdf) ile eşleşen **alan/öğrenme çıktısı/gösterge/açıklama** içerikleri için dosya araması kullan.
- Öğretmen "uygun bir şey bul" derse, programa tam uyumlu materyal/etkinlik öner.
- Tarihler ISO (YYYY-MM-DD). Kısa, uygulanabilir maddeler yaz.

Sadece JSON üret, açıklama/metin ekleme."""

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