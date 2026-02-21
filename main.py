"""
╔═══════════════════════════════════════════════════════════════╗
║         HADITH APP - FastAPI Backend v1.1                     ║
╚═══════════════════════════════════════════════════════════════╝

تطبيق FastAPI احترافي للأحاديث النبوية الشريفة
مع دعم API كامل وبوت تيليجرام

التحديثات:
- FastAPI 0.128.6: استبدال on_event بـ lifespan
- Pydantic 2.12.5: استبدال @validator بـ @field_validator  
- معالجة شاملة واحترافية للأخطاء
"""

import json
import os
import random
import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from pydantic import BaseModel, EmailStr, Field, field_validator

from config import settings
from supabase_service import SupabaseService
from email_service import EmailService


# ============================================
# LOGGING CONFIGURATION
# ============================================
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hadith_app")


# ============================================
# RATE LIMITER SETUP
# ============================================
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ============================================
# DATA LOADING
# ============================================
def load_hadiths() -> List[Dict]:
    """تحميل بيانات الأحاديث من nawawi40_structured.json"""
    possible_paths = [
        "nawawi40_structured.json",
        "./nawawi40_structured.json",
        os.path.join(os.path.dirname(__file__), "nawawi40_structured.json"),
        "/app/nawawi40_structured.json",  # للـ Docker
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        logger.error(f"❌ ملف nawawi40_structured.json غير موجود في أي من المسارات: {possible_paths}")
        logger.error(f"📂 المجلد الحالي: {os.getcwd()}")
        logger.error(f"📄 محتويات المجلد: {os.listdir('.')}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            enriched_data = json.load(f)
            hadiths_raw = enriched_data.get("hadiths", [])
            
            if not hadiths_raw:
                logger.warning(f"⚠️ ملف {file_path} لا يحتوي على أحاديث!")
                return []
            
            # استخراج الراوي من النص العربي
            import re as _re
            def extract_narrator(arabic_text):
                m = _re.match(r'^عَنْ (.+?)(?:\s+رَضِيَ|\s+قَالَ|\s+أَنَّهُ|\s+أَنَّ)', arabic_text)
                if m: return m.group(1).strip()
                m2 = _re.match(r'^عن (.+?)(?:\s+رضي|\s+قال|\s+أنه|\s+أن)', arabic_text)
                if m2: return m2.group(1).strip()
                return ""

            # تحويل البيانات إلى الصيغة المستخدمة في المشروع
            data = []
            for h in hadiths_raw:
                hid = h.get("idInBook", h.get("id"))
                arabic_text = h.get("arabic", "")
                
                # استخراج اسم الراوي - في الملف الجديد narrator هو dict
                narrator_raw = h.get("narrator", "")
                if isinstance(narrator_raw, dict):
                    narrator_name = narrator_raw.get("arabic", "")
                else:
                    narrator_name = extract_narrator(arabic_text) or narrator_raw

                # استخراج المصدر - في الملف الجديد source هو dict
                source_raw = h.get("source", {})
                if isinstance(source_raw, dict):
                    source_text = source_raw.get("grade_arabic", "الأربعون النووية")
                else:
                    source_text = source_raw or "الأربعون النووية"

                data.append({
                    "id":              hid,
                    "title":           h.get("arabic_title", f"الحديث {hid}"),
                    "narrator":        narrator_name,
                    "_raw_narrator":   narrator_raw if isinstance(narrator_raw, dict) else {},
                    "narrator_dict":   narrator_raw if isinstance(narrator_raw, dict) else {},
                    "source_dict":     source_raw if isinstance(source_raw, dict) else {},
                    "text":            arabic_text,
                    "source":          source_text,
                    "arabic_hadith_text_plain": h.get("arabic_hadith_text_plain", ""),
                    "vocabulary":      h.get("vocabulary", []),
                    "benefits":        h.get("benefits", []),
                    "topics":          h.get("topics", {}),
                    "hadith_type":     h.get("hadith_type", ""),
                    "related_hadiths": h.get("related_hadiths", []),
                })
            
            logger.info(f"✅ تم تحميل {len(data)} حديث بنجاح من {file_path}")
            return data
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ خطأ في صيغة JSON في السطر {e.lineno}: {e.msg}")
        logger.error(f"الموضع: {e.pos}")
        return []
    except UnicodeDecodeError as e:
        logger.error(f"❌ خطأ في ترميز الملف: {e}")
        logger.error("تأكد أن الملف بصيغة UTF-8")
        return []
    except OSError as e:
        logger.error(f"❌ خطأ في قراءة الملف: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        logger.error(traceback.format_exc())
        return []


HADITHS_DATA: List[Dict] = load_hadiths()
HADITHS_INDEX: Dict[int, Dict] = {h["id"]: h for h in HADITHS_DATA}

# ============================================
# GLOBAL STATE
# ============================================
supabase_service: Optional[SupabaseService] = None
email_service: Optional[EmailService] = None


# ============================================
# LIFESPAN MANAGER  (بديل on_event - FastAPI 0.93+)
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق بدلاً من @app.on_event"""
    global supabase_service, email_service

    # ──── Startup ────
    logger.info("=" * 60)
    logger.info(f"🚀 بدء تشغيل {settings.app_name} v{settings.app_version}")
    logger.info(f"📍 البيئة: {settings.environment}")
    logger.info(f"📖 الأحاديث المحملة: {len(HADITHS_DATA)}")

    # تهيئة Supabase
    if settings.supabase_url and settings.supabase_key:
        try:
            supabase_service = SupabaseService(settings.supabase_url, settings.supabase_key)
            logger.info("🗄️  Supabase: ✅ متصل")
        except Exception as e:
            logger.warning(f"⚠️ فشل تهيئة Supabase (سيتم المتابعة بدونه): {e}")
            supabase_service = None
    else:
        logger.warning("⚠️ بيانات Supabase غير مُعيَّنة - خدمة التعليقات معطّلة")

    # تهيئة خدمة البريد الإلكتروني (Resend)
    if settings.resend_api_key and settings.contact_email_to:
        try:
            email_service = EmailService(
                api_key=settings.resend_api_key,
                from_name=settings.email_from_name
            )
            if email_service.test_connection():
                logger.info("📧 Email Service (Resend): ✅ متصل وجاهز")
            else:
                logger.warning("⚠️ Email Service (Resend): مفتاح API غير صالح")
        except Exception as e:
            logger.warning(f"⚠️ فشل تهيئة خدمة البريد (نموذج التواصل معطّل): {e}")
            email_service = None
    else:
        logger.warning("⚠️ RESEND_API_KEY أو CONTACT_EMAIL_TO غير مُعيَّن - نموذج التواصل معطّل")

    logger.info("🤖 Telegram Bot: @NibrasNawawi_bot")
    logger.info("=" * 60)

    yield  # التطبيق يعمل هنا

    # ──── Shutdown ────
    logger.info("=" * 60)
    logger.info("👋 إيقاف التطبيق بشكل نظيف...")
    logger.info("=" * 60)


# ============================================
# FASTAPI APP INITIALIZATION
# ============================================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API احترافي للأحاديث النبوية الشريفة",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================
# MIDDLEWARE
# ============================================
origins = settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ============================================
# TEMPLATES & STATIC FILES
# ============================================
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.now

app.mount("/static", StaticFiles(directory="static"), name="static")

# إصلاح مسار sw.js ليكون متاحاً من الجذر (مهم لـ PWA)
@app.get("/static/sw.js")
async def get_sw():
    from fastapi.responses import FileResponse
    return FileResponse("static/sw.js")

# Favicon route
@app.get("/favicon.ico")
async def get_favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/favicon.ico")


# ============================================
# HELPER FUNCTIONS
# ============================================
def get_hadith_by_id(hadith_id: int) -> Optional[Dict]:
    return HADITHS_INDEX.get(hadith_id)


def search_hadiths(query: str) -> List[Dict]:
    """البحث الذكي في الأحاديث"""
    query = query.lower().strip()
    if not query:
        return HADITHS_DATA

    results = []
    for hadith in HADITHS_DATA:
        searchable_text = " ".join([
            hadith.get("title", ""),
            hadith.get("text", ""),
            hadith.get("narrator", ""),
            hadith.get("source", ""),
            " ".join(hadith.get("vocabulary", [])),
            " ".join(hadith.get("benefits", [])),
        ]).lower()
        if query in searchable_text:
            results.append(hadith)
    return results


def api_error(status_code: int, message: str, detail: Any = None) -> JSONResponse:
    """استجابة خطأ موحّدة للـ API"""
    body: Dict[str, Any] = {"success": False, "error": message}
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


def api_success(data: Any, message: str = "تمت العملية بنجاح", status_code: int = 200) -> JSONResponse:
    """استجابة نجاح موحّدة للـ API"""
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": data},
    )


# ============================================
# PYDANTIC MODELS  (Pydantic v2 - field_validator بدلاً من validator)
# ============================================
class CommentCreate(BaseModel):
    """نموذج إضافة تعليق"""
    hadith_id: int = Field(..., description="رقم الحديث")
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    comment: str = Field(..., min_length=5, max_length=1000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("الاسم لا يمكن أن يكون فارغاً")
        return v.strip()

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("التعليق لا يمكن أن يكون فارغاً")
        return v.strip()


class HadithResponse(BaseModel):
    """نموذج استجابة الحديث"""
    id: int
    title: str
    text: str
    narrator: str
    source: Optional[str] = None
    vocabulary: List[str] = []
    benefits: List[str] = []

    model_config = {"from_attributes": True}


class ContactForm(BaseModel):
    """نموذج التواصل"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)

    @field_validator("name", "subject", "message")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("الحقل لا يمكن أن يكون فارغاً")
        return stripped


# ============================================
# WEB ROUTES
# ============================================
@app.get("/")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def home(request: Request, q: Optional[str] = None, narrator: Optional[str] = None):
    try:
        hadiths = search_hadiths(q) if q else HADITHS_DATA
        # فلتر الراوي
        if narrator:
            hadiths = [h for h in hadiths if narrator in h.get("narrator", "")]
        # قائمة الرواة مرتبة حسب رقم الحديث (أول ظهور)
        seen = {}
        for h in HADITHS_DATA:
            n = h.get("narrator", "")
            if n and n not in seen:
                seen[n] = h["id"]
        narrators = sorted(seen.keys(), key=lambda x: seen[x])
        return templates.TemplateResponse("index.html", {
            "request": request,
            "hadiths": hadiths,
            "search_query": q or "",
            "total_hadiths": len(HADITHS_DATA),
            "settings": settings,
            "narrators": narrators,
            "active_narrator": narrator or "",
        })
    except Exception as e:
        logger.error(f"❌ خطأ في الصفحة الرئيسية: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="خطأ في تحميل الصفحة")


@app.get("/debug/hadiths")
async def debug_hadiths(request: Request):
    """صفحة تشخيص الأحاديث - للتطوير فقط"""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    
    return JSONResponse({
        "total_hadiths": len(HADITHS_DATA),
        "hadiths_loaded": len(HADITHS_DATA) > 0,
        "first_hadith": HADITHS_DATA[0] if HADITHS_DATA else None,
        "last_hadith": HADITHS_DATA[-1] if HADITHS_DATA else None,
        "current_dir": os.getcwd(),
        "files_in_current_dir": [f for f in os.listdir('.') if f.endswith('.json')],
        "enriched_json_exists": os.path.exists('nawawi40_structured.json'),
        "index_sample": {k: v for k, v in list(HADITHS_INDEX.items())[:3]} if HADITHS_INDEX else {},
    })


@app.get("/hadith/{hadith_id}")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def hadith_detail(request: Request, hadith_id: int):
    try:
        hadith = get_hadith_by_id(hadith_id)
        if not hadith:
            raise HTTPException(status_code=404, detail="الحديث غير موجود")

        current_index = next((i for i, h in enumerate(HADITHS_DATA) if h["id"] == hadith_id), None)
        prev_hadith = HADITHS_DATA[current_index - 1] if current_index and current_index > 0 else None
        next_hadith = (
            HADITHS_DATA[current_index + 1]
            if current_index is not None and current_index < len(HADITHS_DATA) - 1
            else None
        )

        comments = []
        if supabase_service:
            try:
                comments = await supabase_service.get_comments_for_hadith(hadith_id)
                for comment in comments:
                    comment["time_ago"] = supabase_service.format_comment_time(comment["created_at"])
            except Exception as e:
                logger.warning(f"⚠️ خطأ في جلب التعليقات: {e}")

        return templates.TemplateResponse("detail.html", {
            "request": request,
            "hadith": hadith,
            "prev_hadith": prev_hadith,
            "next_hadith": next_hadith,
            "comments": comments,
            "comments_count": len(comments),
            "settings": settings,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطأ في صفحة التفاصيل: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="خطأ في تحميل الحديث")


# ============================================
# API ENDPOINTS
# ============================================
# ⚠️ يجب أن يكون /random قبل /{hadith_id} لتجنب تعارض المسارات
@app.get("/api/hadiths/random", response_model=HadithResponse)
@limiter.limit("100/minute")
async def get_random_hadith_api(request: Request):
    if not HADITHS_DATA:
        raise HTTPException(status_code=404, detail="لا توجد أحاديث متاحة")
    return random.choice(HADITHS_DATA)


@app.get("/api/hadiths", response_model=List[HadithResponse])
@limiter.limit("100/minute")
async def get_all_hadiths(request: Request, skip: int = 0, limit: int = 20):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip يجب أن يكون 0 أو أكبر")
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit يجب أن يكون بين 1 و 100")
    return HADITHS_DATA[skip: skip + limit]


@app.get("/api/hadiths/{hadith_id}", response_model=HadithResponse)
@limiter.limit("100/minute")
async def get_hadith_api(request: Request, hadith_id: int):
    if hadith_id < 1:
        raise HTTPException(status_code=400, detail="رقم الحديث يجب أن يكون موجباً")
    hadith = get_hadith_by_id(hadith_id)
    if not hadith:
        raise HTTPException(status_code=404, detail="الحديث غير موجود")
    return hadith


@app.get("/api/search", response_model=List[HadithResponse])
@limiter.limit("50/minute")
async def search_api(request: Request, q: str, limit: int = 10):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="الرجاء إدخال كلمة للبحث")
    if not 1 <= limit <= 50:
        raise HTTPException(status_code=400, detail="limit يجب أن يكون بين 1 و 50")
    return search_hadiths(q)[:limit]


# ============================================
# COMMENTS API
# ============================================
@app.post("/api/comments", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_comment(request: Request, comment_data: CommentCreate):
    if not supabase_service:
        return api_error(503, "خدمة التعليقات غير متاحة حالياً")

    if not get_hadith_by_id(comment_data.hadith_id):
        return api_error(404, "الحديث المحدد غير موجود")

    try:
        comment = await supabase_service.add_comment(
            hadith_id=comment_data.hadith_id,
            name=comment_data.name,
            email=comment_data.email,
            comment=comment_data.comment,
        )
        return api_success(data=comment, message="تم إضافة التعليق بنجاح", status_code=201)
    except ValueError as e:
        logger.warning(f"⚠️ بيانات غير صحيحة: {e}")
        return api_error(400, str(e))
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة التعليق: {e}\n{traceback.format_exc()}")
        return api_error(500, "خطأ داخلي في إضافة التعليق")


@app.get("/api/comments/{hadith_id}")
@limiter.limit("50/minute")
async def get_comments(request: Request, hadith_id: str):
    # التحقق مما إذا كان hadith_id هو "undefined" أو قيمة غير صالحة
    if str(hadith_id) == "undefined":
         return []
         
    try:
        hid = int(hadith_id)
        if hid < 1:
            return []
    except ValueError:
        return []

    if not supabase_service:
        return []
    try:
        return await supabase_service.get_comments_for_hadith(hid)
    except Exception as e:
        logger.error(f"❌ خطأ في جلب التعليقات: {e}")
        return []

@app.get("/api/general-comments")
@limiter.limit("50/minute")
async def get_general_comments(request: Request):
    if not supabase_service:
        return []
    try:
        return await supabase_service.get_comments_for_hadith(0)
    except Exception as e:
        logger.error(f"❌ خطأ في جلب التعليقات العامة: {e}")
        return []

@app.post("/api/general-comments")
@limiter.limit("10/minute")
async def create_general_comment(request: Request, comment_data: Dict[str, Any]):
    if not supabase_service:
        return api_error(503, "خدمة التعليقات غير متاحة حالياً")
    
    try:
        # استخدام hadith_id = 0 للتعليقات العامة
        comment = await supabase_service.add_comment(
            hadith_id=0,
            name=comment_data.get("name"),
            email=comment_data.get("email"),
            comment=comment_data.get("comment"),
        )
        return api_success(data=comment, message="تم إضافة التعليق بنجاح", status_code=201)
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة التعليق العام: {e}")
        return api_error(500, "خطأ داخلي")


# ============================================
# TELEGRAM WEBHOOK
# ============================================
@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    return {"status": "ok"}


# ============================================
# OTHER PAGES
# ============================================
@app.get("/quiz")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def quiz_list_page(request: Request):
    return templates.TemplateResponse("quiz.html", {"request": request, "settings": settings})


@app.get("/quiz/start")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def quiz_start_page(request: Request, type: str = "first-10"):
    try:
        questions, quiz_title, time_limit = generate_quiz_questions(type)
        return templates.TemplateResponse("quiz_test.html", {
            "request": request,
            "questions": questions,
            "quiz_title": quiz_title,
            "time_limit": time_limit,
            "quiz_type": type,
            "settings": settings,
        })
    except Exception as e:
        logger.error(f"❌ خطأ في صفحة الاختبار: {e}")
        raise HTTPException(status_code=500, detail="خطأ في تحميل الاختبار")


def _get_narrator_field(hadith: Dict, field: str, default="") -> Any:
    """استخراج حقل من بيانات الراوي بأمان"""
    nar = hadith.get("narrator_dict") or hadith.get("_raw_narrator") or {}
    if isinstance(nar, dict):
        return nar.get(field, default)
    return default

def _get_source_books(hadith: Dict) -> list:
    """استخراج قائمة كتب المصادر"""
    src = hadith.get("source_dict") or {}
    return src.get("books_arabic", [])

def _build_options(correct: str, pool: list, count: int = 3) -> list:
    """بناء 4 خيارات: 1 صحيح + 3 خاطئة"""
    wrong_pool = [x for x in pool if x and x != correct]
    wrong_pool = list(dict.fromkeys(wrong_pool))  # إزالة التكرار
    if len(wrong_pool) < count:
        return []
    wrong = random.sample(wrong_pool, count)
    options = wrong + [correct]
    random.shuffle(options)
    return options

def _make_narrator_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """من الراوي؟"""
    correct = _get_narrator_field(hadith, "arabic", "")
    if not correct:
        return None
    pool = [_get_narrator_field(h, "arabic") for h in all_hadiths]
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'من روى الحديث المعروف بـ «{hadith.get("title", "")}»؟',
        "hadith_text": hadith.get("arabic_hadith_text_plain", ""),
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'رواه {correct} رضي الله عنه. {_get_narrator_field(hadith, "bio_arabic", "")}',
    }

def _make_complete_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """أكمل الحديث"""
    text = hadith.get("arabic_hadith_text_plain", "").strip().strip('"').strip('«').strip('»')
    if not text:
        return None
    words = text.split()
    if len(words) < 8:
        return None
    # أخذ النصف الأول وترك النصف الثاني للإكمال
    split = len(words) // 2
    first_half = " ".join(words[:split])
    correct = " ".join(words[split:split+4])  # 4 كلمات
    # خيارات خاطئة من أحاديث أخرى
    pool = []
    for h in all_hadiths:
        t = h.get("arabic_hadith_text_plain", "").strip().strip('"')
        w = t.split()
        if len(w) > split + 4 and h["id"] != hadith["id"]:
            pool.append(" ".join(w[split:split+4]))
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'أكمل الحديث: «{first_half} ...»',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'النص الكامل: «{text}»',
    }

def _make_which_hadith_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """من أي حديث هذا المقطع؟"""
    text = hadith.get("arabic_hadith_text_plain", "").strip().strip('"')
    if not text:
        return None
    words = text.split()
    if len(words) < 5:
        return None
    # أخذ مقطع من المنتصف
    mid = len(words) // 3
    snippet = " ".join(words[mid:mid+6])
    correct = hadith.get("title", "")
    pool = [h.get("title", "") for h in all_hadiths if h["id"] != hadith["id"]]
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'من أي حديث هذا المقطع؟\n«...{snippet}...»',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'هذا مقطع من حديث «{correct}».',
    }

def _make_vocabulary_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """معاني المفردات"""
    vocab = hadith.get("vocabulary", [])
    if not vocab:
        return None
    entry = random.choice(vocab)
    # الشكل: "الكلمة: المعنى"
    if ":" not in entry:
        return None
    parts = entry.split(":", 1)
    word = parts[0].strip()
    correct = parts[1].strip()
    # خيارات من معاني كلمات أخرى
    pool = []
    for h in all_hadiths:
        for v in h.get("vocabulary", []):
            if ":" in v:
                p = v.split(":", 1)
                meaning = p[1].strip()
                if meaning != correct and p[0].strip() != word:
                    pool.append(meaning)
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'ما معنى كلمة «{word}» في قول النبي ﷺ؟',
        "hadith_text": hadith.get("arabic_hadith_text_plain", ""),
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'«{word}»: {correct}',
    }

def _make_benefit_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """فوائد الأحاديث"""
    benefits = hadith.get("benefits", [])
    if not benefits:
        return None
    correct = random.choice(benefits)
    pool = []
    for h in all_hadiths:
        for b in h.get("benefits", []):
            if b != correct:
                pool.append(b)
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'ما إحدى فوائد حديث «{hadith.get("title", "")}»؟',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'من فوائد هذا الحديث: {correct}',
    }

def _make_topic_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """تصنيف الأحاديث"""
    correct = (hadith.get("topics") or {}).get("category_arabic", "")
    if not correct:
        return None
    pool = list(set(
        (h.get("topics") or {}).get("category_arabic", "")
        for h in all_hadiths
        if (h.get("topics") or {}).get("category_arabic") and h["id"] != hadith["id"]
    ))
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'ما التصنيف الرئيسي لحديث «{hadith.get("title", "")}»؟',
        "hadith_text": hadith.get("arabic_hadith_text_plain", ""),
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'حديث «{hadith.get("title", "")}» يندرج تحت تصنيف: {correct}',
    }

def _make_source_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """مصادر الأحاديث"""
    books = _get_source_books(hadith)
    if not books:
        return None
    correct = books[0]
    pool = list(set(
        b for h in all_hadiths
        for b in _get_source_books(h)
        if b != correct
    ))
    options = _build_options(correct, pool)
    if not options:
        return None
    src = hadith.get("source_dict") or {}
    grade = src.get("grade_arabic", "")
    return {
        "question": f'في أي كتاب ورد حديث «{hadith.get("title", "")}»?',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'رواه {correct}. درجته: {grade}',
    }

def _make_narrator_tribe_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """قبائل الرواة"""
    correct = _get_narrator_field(hadith, "tribe_arabic", "")
    narrator = _get_narrator_field(hadith, "arabic", "الراوي")
    if not correct:
        return None
    pool = list(set(
        _get_narrator_field(h, "tribe_arabic")
        for h in all_hadiths
        if _get_narrator_field(h, "tribe_arabic") and _get_narrator_field(h, "tribe_arabic") != correct
    ))
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'من أي قبيلة ينتسب {narrator} راوي حديث «{hadith.get("title", "")}»؟',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'{narrator} ينتسب إلى قبيلة {correct}.',
    }

def _make_narrator_died_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """تاريخ وفاة الراوي"""
    died = _get_narrator_field(hadith, "died_ah", None)
    narrator = _get_narrator_field(hadith, "arabic", "الراوي")
    if died is None:
        return None
    correct = f"{died} هـ"
    pool = list(set(
        f"{_get_narrator_field(h, 'died_ah')} هـ"
        for h in all_hadiths
        if _get_narrator_field(h, 'died_ah') and _get_narrator_field(h, 'died_ah') != died
    ))
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'متى توفي {narrator} راوي حديث «{hadith.get("title", "")}»؟',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'توفي {narrator} سنة {correct}.',
    }

def _make_narrations_count_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """عدد روايات الصحابي"""
    count = _get_narrator_field(hadith, "narrations_count", None)
    narrator = _get_narrator_field(hadith, "arabic", "الراوي")
    if count is None:
        return None
    correct = f"{int(str(count).split()[0].replace(",","")):,} حديث"
    pool = list(set(
        f"{int(str(_get_narrator_field(h, 'narrations_count') or 0).split()[0].replace(",","")):,} حديث"
        for h in all_hadiths
        if _get_narrator_field(h, 'narrations_count') and _get_narrator_field(h, 'narrations_count') != count
    ))
    options = _build_options(correct, pool)
    if not options:
        return None
    return {
        "question": f'كم عدد روايات {narrator} في كتب السنة؟',
        "options": options,
        "correctAnswer": options.index(correct),
        "explanation": f'روى {narrator} ما مجموعه {correct} في كتب السنة النبوية.',
    }

def _make_speed_q(hadith: Dict, all_hadiths: List[Dict]) -> Optional[Dict]:
    """سؤال سريع متنوع للسباق ضد الوقت"""
    makers = [_make_narrator_q, _make_which_hadith_q, _make_source_q, _make_topic_q]
    random.shuffle(makers)
    for maker in makers:
        q = maker(hadith, all_hadiths)
        if q:
            return q
    return None

def generate_quiz_questions(quiz_type: str):
    """توليد أسئلة حقيقية لكل نوع اختبار"""

    # ── تحديد الأحاديث والعنوان والوقت ──
    CONFIG = {
        "narrator":          ("من الراوي؟",                  10, 8,  _make_narrator_q),
        "complete":          ("أكمل الحديث",                 10, 10, _make_complete_q),
        "which-hadith":      ("من أي حديث؟",                 10, 10, _make_which_hadith_q),
        "vocabulary":        ("معاني المفردات",               10, 8,  _make_vocabulary_q),
        "benefit":           ("فوائد الأحاديث",               10, 8,  _make_benefit_q),
        "topic":             ("تصنيف الأحاديث",               10, 8,  _make_topic_q),
        "source":            ("مصادر الأحاديث",               10, 8,  _make_source_q),
        "narrator-tribe":    ("قبائل الرواة",                 10, 8,  _make_narrator_tribe_q),
        "narrator-died":     ("تاريخ وفاة الراوي",            10, 8,  _make_narrator_died_q),
        "narrations-count":  ("عدد الروايات",                 10, 8,  _make_narrations_count_q),
        "speed":             ("السباق ضد الوقت ⚡",           10, 1,  _make_speed_q),
        "random-20":         ("الاختبار الشامل 🎲",           20, 10, None),
        "first-10":          ("اختبار الأحاديث العشرة الأولى", 10, 5, None),
    }

    if quiz_type not in CONFIG:
        quiz_type = "narrator"

    quiz_title, target_count, time_limit, maker = CONFIG[quiz_type]

    # ── اختيار مجموعة الأحاديث ──
    if quiz_type == "first-10":
        pool = HADITHS_DATA[:10]
    elif quiz_type == "random-20":
        pool = random.sample(HADITHS_DATA, min(20, len(HADITHS_DATA)))
    else:
        pool = list(HADITHS_DATA)
        random.shuffle(pool)

    # ── توليد الأسئلة ──
    questions = []

    if quiz_type in ("random-20", "first-10"):
        # مزيج من كل الأنواع
        all_makers = [
            _make_narrator_q, _make_complete_q, _make_which_hadith_q,
            _make_vocabulary_q, _make_benefit_q, _make_topic_q,
            _make_source_q, _make_narrator_tribe_q,
        ]
        for hadith in pool:
            if len(questions) >= target_count:
                break
            mk = random.choice(all_makers)
            q = mk(hadith, HADITHS_DATA)
            if q:
                questions.append(q)
    else:
        for hadith in pool:
            if len(questions) >= target_count:
                break
            q = maker(hadith, HADITHS_DATA)
            if q:
                questions.append(q)

    random.shuffle(questions)
    return questions, quiz_title, time_limit




# ============================================
# صفحة الرواة
# ============================================
@app.get("/narrators")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def narrators_page(request: Request):
    try:
        # جمع الرواة مع بياناتهم الكاملة
        seen = {}
        for h in HADITHS_DATA:
            raw = h.get("_raw_narrator") or {}
            name = h.get("narrator", "")
            if name and name not in seen:
                seen[name] = {
                    "name": name,
                    "hadith_count": 0,
                    "first_hadith_id": h["id"],
                    "info": raw if isinstance(raw, dict) else {}
                }
            if name in seen:
                seen[name]["hadith_count"] += 1

        narrators = sorted(seen.values(), key=lambda x: x["first_hadith_id"])
        return templates.TemplateResponse("narrators.html", {
            "request": request,
            "narrators": narrators,
            "total": len(narrators),
            "settings": settings,
        })
    except Exception as e:
        logger.error(f"❌ خطأ في صفحة الرواة: {e}")
        raise HTTPException(status_code=500, detail="خطأ في تحميل الصفحة")


@app.get("/narrator/{narrator_name}")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def narrator_detail_page(request: Request, narrator_name: str):
    try:
        from urllib.parse import unquote
        narrator_name = unquote(narrator_name)
        hadiths = [h for h in HADITHS_DATA if h.get("narrator", "") == narrator_name]
        if not hadiths:
            raise HTTPException(status_code=404, detail="الراوي غير موجود")

        # استخراج بيانات الراوي الكاملة من أول حديث
        first = hadiths[0]
        narrator_info = first.get("_raw_narrator") or {}

        return templates.TemplateResponse("narrator_detail.html", {
            "request": request,
            "narrator_name": narrator_name,
            "narrator_info": narrator_info if isinstance(narrator_info, dict) else {},
            "hadiths": hadiths,
            "settings": settings,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطأ في صفحة الراوي: {e}")
        raise HTTPException(status_code=500, detail="خطأ في تحميل الصفحة")


# ============================================
# API: مشاركة الحديث كصورة (بيانات JSON)
# ============================================
@app.get("/api/hadith/{hadith_id}/share-data")
async def hadith_share_data(request: Request, hadith_id: int):
    hadith = get_hadith_by_id(hadith_id)
    if not hadith:
        raise HTTPException(status_code=404)
    return {
        "id": hadith["id"],
        "title": hadith.get("title", ""),
        "text": hadith.get("text", ""),
        "narrator": hadith.get("narrator", ""),
        "source": hadith.get("source", ""),
    }

@app.get("/comments")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def all_comments_page(request: Request):
    all_comments = []
    if supabase_service:
        try:
            all_comments = await supabase_service.get_all_comments(limit=100)
            for comment in all_comments:
                comment["time_ago"] = supabase_service.format_comment_time(comment["created_at"])
                hadith_id = comment.get("hadith_id", 0)
                if hadith_id and hadith_id > 0:
                    h = get_hadith_by_id(hadith_id)
                    comment["hadith_title"] = h.get("title", "") if h else ""
                else:
                    comment["hadith_title"] = "تعليق عام"
        except Exception as e:
            logger.warning(f"⚠️ خطأ في جلب التعليقات: {e}")

    return templates.TemplateResponse("all_comments.html", {
        "request": request,
        "comments": all_comments,
        "total_comments": len(all_comments),
        "settings": settings,
    })


@app.get("/api-docs")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def api_documentation(request: Request):
    return templates.TemplateResponse("api_docs.html", {
        "request": request, "settings": settings, "base_url": settings.site_url
    })


@app.get("/profile")
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request, "settings": settings})


@app.get("/contact")
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "settings": settings})


@app.post("/api/contact")
@limiter.limit("5/minute")
async def contact_api(request: Request, form: ContactForm):
    """معالجة نموذج التواصل - إرسال بريد إلكتروني عبر Resend"""
    try:
        logger.info(f"📩 رسالة من {form.name} ({form.email}) - {form.subject}")

        if email_service and settings.contact_email_to:
            success = email_service.send_contact_email(
                to_email=settings.contact_email_to,
                name=form.name,
                email=form.email,
                subject=form.subject,
                message=form.message
            )

            if success:
                return api_success(
                    data=None,
                    message="تم إرسال رسالتك بنجاح! سنتواصل معك قريباً إن شاء الله 🌿"
                )
            else:
                # Resend فشل — أعد خطأ حقيقي ليفتح الـ frontend mailto fallback
                logger.error(f"❌ فشل إرسال بريد Resend لـ: {form.name} ({form.email})")
                return api_error(503, "خدمة البريد غير متاحة حالياً، يرجى المحاولة لاحقاً")
        else:
            # خدمة البريد غير مُهيأة
            logger.warning("⚠️ RESEND_API_KEY أو CONTACT_EMAIL_TO غير مُعيَّن")
            return api_error(503, "خدمة البريد غير مُهيأة")

    except Exception as e:
        logger.error(f"❌ خطأ في معالجة التواصل: {e}")
        return api_error(500, "خطأ داخلي، يرجى المحاولة لاحقاً")


@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request, "settings": settings})


@app.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request, "settings": settings})


@app.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request, "settings": settings})


# ============================================
# SITEMAP & ROBOTS.TXT
# ============================================
@app.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    """Sitemap ديناميكي يتحدث تلقائياً مع كل حديث جديد"""
    from fastapi.responses import Response

    today = datetime.now().strftime("%Y-%m-%d")
    base = settings.site_url.rstrip("/")

    # الصفحات الثابتة مع أولوياتها
    static_pages = [
        (f"{base}/",         "1.0", "daily"),
        (f"{base}/quiz",     "0.9", "weekly"),
        (f"{base}/about",    "0.8", "monthly"),
        (f"{base}/comments", "0.7", "daily"),
        (f"{base}/api-docs", "0.6", "monthly"),
        (f"{base}/contact",  "0.6", "monthly"),
        (f"{base}/privacy",  "0.4", "yearly"),
        (f"{base}/terms",    "0.4", "yearly"),
    ]

    urls_xml = ""
    for loc, priority, freq in static_pages:
        urls_xml += (
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>\n"
        )

    # صفحات الأحاديث الـ 42
    for hadith in HADITHS_DATA:
        hid = hadith["id"]
        priority = "0.95" if hid <= 5 else "0.85" if hid <= 15 else "0.80"
        urls_xml += (
            f"  <url>\n"
            f"    <loc>{base}/hadith/{hid}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>\n"
        )

    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{urls_xml}'
        '</urlset>'
    )

    return Response(content=xml_content, media_type="application/xml")


@app.get("/robots.txt")
async def robots_txt(request: Request):
    """robots.txt — يوجّه محركات البحث ويشير للسيتماب"""
    from fastapi.responses import Response

    base = settings.site_url.rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /hadith/\n"
        "Allow: /quiz\n"
        "Allow: /about\n"
        "Allow: /comments\n"
        "Allow: /api-docs\n"
        "Allow: /contact\n"
        "Allow: /privacy\n"
        "Allow: /terms\n"
        "\n"
        "Disallow: /api/\n"
        "Disallow: /debug/\n"
        "Disallow: /profile\n"
        "\n"
        f"Sitemap: {base}/sitemap.xml\n"
        "Crawl-delay: 10\n"
    )
    return Response(content=content, media_type="text/plain")


# ============================================
# GLOBAL EXCEPTION HANDLERS
# ============================================
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """معالج موحّد لأخطاء HTTP - يفرّق بين API والصفحات"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail},
        )
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request, "settings": settings}, status_code=404)
    return templates.TemplateResponse("500.html", {"request": request, "settings": settings, "error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """معالج الأخطاء غير المتوقعة"""
    logger.error(
        f"❌ خطأ غير متوقع [{request.method} {request.url.path}]: "
        f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    )
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"success": False, "error": "خطأ داخلي في الخادم"})
    return templates.TemplateResponse("500.html", {"request": request, "settings": settings}, status_code=500)


# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
