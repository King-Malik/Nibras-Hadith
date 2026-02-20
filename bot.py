"""
بوت تليجرام 'نبراس' - معلم الأربعين النووية - النسخة الكاملة v3
====================================================================
بوت متخصص في تعليم وشرح الأحاديث النبوية من كتاب الأربعين النووية
باستخدام الذكاء الاصطناعي مع ميزات متقدمة لطلاب العلم.

الميزات (v3 — 10/10):
- 🔍 البحث في الأحاديث (مع أولوية العنوان)
- 🎓 اختبارات تفاعلية (4 أنواع أسئلة)
- 📊 إحصائيات تقدم أسبوعية وإجمالية
- 🔖 المفضلة
- 🔗 الأحاديث المرتبطة (روابط حقيقية من JSON)
- 📝 الملاحظات الشخصية
- 📅 حديث اليوم (مع تذكير ذكي بالمتبقي)
- 🎯 خطة دراسية منظمة
- 💬 شرح مبسط ومقارن (مع ذاكرة سياق محسّنة)
- ⏰ تذكير يومي تلقائي
- 💡 أسئلة ذكية مقترحة
- ☕ نظام الدعم
- 👤 بطاقة الراوي التفاعلية (جديد)
- 🏷️ التصفح بالموضوعات والتصنيفات (جديد)
- 🌍 الترجمة الإنجليزية (جديد)
- 🏅 شارة الحديث القدسي (جديد)
- 🃏 بطاقات الحفظ / Flashcards (جديد)
- 🏆 نظام الشارات والإنجازات (جديد)
- 🔥 السلسلة اليومية / Streak (جديد)
- 🤔 اختبار أعرف/لا أعرف (جديد)
- 📤 مشاركة الحديث بصيغة جاهزة (جديد)
- 🔔 تذكير ذكي بالأحاديث غير المقروءة (جديد)
- 🌙 وضع الليل / تذكير مسائي (جديد)
"""

import os
import logging
import asyncio
import json
import random
import re
from typing import Optional, Dict, List, Any, Tuple
from collections import deque
from pathlib import Path
from datetime import datetime, timedelta
from datetime import time as datetime_time
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# 1. الإعدادات والثوابت
# ═══════════════════════════════════════════════════════════════════

TELEGRAM_TOKEN: Optional[str] = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
DEVELOPER_TELEGRAM_ID: Optional[str] = os.getenv("DEVELOPER_TELEGRAM_ID")
# وضع الصيانة — يُفعَّل بأمر /admin_maintenance
_maintenance_mode: bool = False
_maintenance_message: str = "🔧 البوت في وضع الصيانة حالياً، يرجى المحاولة لاحقاً."

SUPPORT_LINK = "https://ko-fi.com/nibras_hadith"
SUPPORT_REMINDER_INTERVAL = 30

# ── Monetag ──────────────────────────────────────────────────────
MONETAG_ENABLED:  bool = os.getenv("MONETAG_ENABLED", "True").strip().lower() == "true"
MONETAG_DIRECT_LINK: str = os.getenv("MONETAG_DIRECT_LINK", "https://omg10.com/4/10632325")
# عرض إعلان كل N تفاعل (0 = معطّل)
MONETAG_INTERVAL: int  = 8
# تتبع آخر مرة ظهر فيها إعلان لكل مستخدم {user_id: interaction_count_at_last_ad}
_monetag_last_shown: Dict[int, int] = {}

DEFAULT_REMINDER_TIME = "08:00"
DEFAULT_TIMEZONE = "Asia/Riyadh"

MAX_CONVERSATION_HISTORY = 8
REQUEST_TIMEOUT = 30.0

HADITH_FILE_PATH = Path("nawawi40_structured.json")
USER_DATA_PATH = Path("user_data")
USER_DATA_PATH.mkdir(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 2. التحقق من المتطلبات
# ═══════════════════════════════════════════════════════════════════

def validate_configuration() -> None:
    required = {"TELEGRAM_TOKEN": TELEGRAM_TOKEN, "OPENROUTER_API_KEY": OPENROUTER_API_KEY}
    missing = [k for k, v in required.items() if not v]
    if missing:
        msg = f"❌ متغيرات بيئية مفقودة: {', '.join(missing)}"
        logger.error(msg)
        raise EnvironmentError(f"{msg}\nيرجى إنشاء ملف .env وإضافة المفاتيح المطلوبة.")
    logger.info("✅ تم التحقق من جميع الإعدادات بنجاح")


# ═══════════════════════════════════════════════════════════════════
# 3. قاعدة بيانات الأحاديث (محسّنة بالكامل)
# ═══════════════════════════════════════════════════════════════════

class HadithDatabase:
    """إدارة بيانات الأحاديث — تستخرج كل حقول JSON الثرية"""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.hadiths: List[Dict[str, Any]] = []
        self._index: Dict[int, Dict[str, Any]] = {}
        # فهرس الموضوعات: category_arabic → [hadith_ids]
        self._topics_index: Dict[str, List[int]] = {}
        # فهرس الموضوعات الفردية: topic → [hadith_ids]
        self._topic_tags_index: Dict[str, List[int]] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not self.file_path.exists():
            logger.warning(f"⚠️ ملف الأحاديث غير موجود: {self.file_path}")
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for h in raw.get("hadiths", []):
                hadith = self._normalise(h)
                self.hadiths.append(hadith)
                self._index[hadith["id"]] = hadith
                # بناء فهرس التصنيفات
                cat = hadith.get("category_arabic", "")
                if cat:
                    self._topics_index.setdefault(cat, []).append(hadith["id"])
                # بناء فهرس الموضوعات الفردية
                for tag in hadith.get("topics_arabic", []):
                    self._topic_tags_index.setdefault(tag, []).append(hadith["id"])
            logger.info(f"✅ تم تحميل {len(self.hadiths)} حديث | {len(self._topics_index)} تصنيف")
        except json.JSONDecodeError as exc:
            logger.error(f"❌ خطأ في JSON: {exc}")
        except OSError as exc:
            logger.error(f"❌ خطأ في القراءة: {exc}")

    @staticmethod
    def _normalise(h: Dict[str, Any]) -> Dict[str, Any]:
        """تحويل سجل خام إلى صيغة داخلية موحّدة — يستخرج كل الحقول"""
        hid = h.get("idInBook", h.get("id"))

        # ── الراوي ──
        narrator_raw = h.get("narrator", "")
        if isinstance(narrator_raw, dict):
            narrator_name = narrator_raw.get("arabic", "")
            narrator_full = narrator_raw  # نحتفظ بالكامل
        else:
            narrator_name = str(narrator_raw)
            narrator_full = {}

        # ── المصدر ──
        source_raw = h.get("source", {})
        if isinstance(source_raw, dict):
            source_text  = source_raw.get("grade_arabic", "الأربعون النووية")
            source_books = source_raw.get("books_arabic", [])
            source_grade = source_raw.get("grade_arabic", "")
        else:
            source_text  = str(source_raw) if source_raw else "الأربعون النووية"
            source_books = []
            source_grade = ""

        # ── الموضوعات ──
        topics_raw = h.get("topics", {})
        if isinstance(topics_raw, dict):
            topics_arabic   = topics_raw.get("arabic", [])
            topics_english  = topics_raw.get("english", [])
            category_arabic = topics_raw.get("category_arabic", "")
        else:
            topics_arabic = topics_english = []
            category_arabic = ""

        # ── نوع الحديث ──
        htype_raw = h.get("hadith_type", {})
        if isinstance(htype_raw, dict):
            hadith_type_key    = htype_raw.get("type", "marfu")
            hadith_type_arabic = htype_raw.get("arabic", "حديث مرفوع")
        else:
            hadith_type_key    = "marfu"
            hadith_type_arabic = "حديث مرفوع"

        # ── الترجمة الإنجليزية ──
        english_raw = h.get("english", {})
        if isinstance(english_raw, dict):
            english_narrator = english_raw.get("narrator", "")
            english_text     = english_raw.get("text", "")
        else:
            english_narrator = english_text = ""

        return {
            "id":                   hid,
            "title":                h.get("arabic_title", f"الحديث {hid}"),
            "narrator":             narrator_name,
            "narrator_full":        narrator_full,      # dict كامل للراوي
            "text":                 h.get("arabic", ""),
            "narrator_intro":       h.get("arabic_narrator_intro", ""),
            "hadith_text_only":     h.get("arabic_hadith_text", ""),
            "arabic_plain":         h.get("arabic_plain", ""),
            "source":               source_text,
            "source_books":         source_books,
            "source_grade":         source_grade,
            "vocabulary":           h.get("vocabulary", []),
            "benefits":             h.get("benefits", []),
            "topics_arabic":        topics_arabic,
            "topics_english":       topics_english,
            "category_arabic":      category_arabic,
            "hadith_type":          hadith_type_key,     # "marfu" أو "qudsi"
            "hadith_type_arabic":   hadith_type_arabic,
            "english_narrator":     english_narrator,
            "english_text":         english_text,
            "related_hadiths":      h.get("related_hadiths", []),  # ← روابط حقيقية!
        }

    @staticmethod
    def _extract_narrator(arabic_text: str) -> str:
        patterns = [
            r"^عَنْ (.+?)(?:\s+رَضِيَ|\s+قَالَ|\s+أَنَّهُ|\s+أَنَّ)",
            r"^عن (.+?)(?:\s+رضي|\s+قال|\s+أنه|\s+أن)",
        ]
        for pat in patterns:
            m = re.match(pat, arabic_text)
            if m:
                return m.group(1).strip()
        return ""

    # ── واجهة الاستعلام ─────────────────────────────────────────────

    def get_by_id(self, hadith_id: int) -> Optional[Dict[str, Any]]:
        return self._index.get(hadith_id)

    def get_random(self) -> Optional[Dict[str, Any]]:
        return random.choice(self.hadiths) if self.hadiths else None

    def get_all(self) -> List[Dict[str, Any]]:
        return self.hadiths

    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        بحث ذكي متقدم:
        - يدعم كلمات متعددة (كل الكلمات يجب أن تتواجد)
        - يبحث في جميع الحقول (عنوان، نص، راوي، مفردات، فوائد، مصدر، موضوعات)
        - يرتب النتائج حسب الصلة (تطابق العنوان أولاً، ثم التطابق الكامل، ثم الجزئي)
        """
        kw = keyword.strip().lower()
        if not kw:
            return []

        # دعم البحث بكلمات متعددة
        words = kw.split()

        scored = []
        for hadith in self.hadiths:
            title      = hadith.get("title", "").lower()
            text       = hadith.get("text", "").lower()
            narrator   = hadith.get("narrator", "").lower()
            source     = hadith.get("source", "").lower()
            topics     = " ".join(hadith.get("topics_arabic", [])).lower()
            vocabulary = " ".join(
                v if isinstance(v, str) else v.get("word", "") + " " + v.get("meaning", "")
                for v in hadith.get("vocabulary", [])
            ).lower()
            benefits   = " ".join(
                b if isinstance(b, str) else ""
                for b in hadith.get("benefits", [])
            ).lower()

            full_text = f"{title} {text} {narrator} {source} {topics} {vocabulary} {benefits}"

            # تحقق أن كل كلمات البحث موجودة
            if not all(w in full_text for w in words):
                continue

            # حساب درجة الصلة
            score = 0
            if kw in title:           score += 100   # تطابق كامل في العنوان
            if all(w in title for w in words): score += 50   # كل الكلمات في العنوان
            if kw in text:            score += 30    # تطابق كامل في النص
            if kw in topics:          score += 20    # في الموضوعات
            if kw in narrator:        score += 15    # في الراوي
            if kw in vocabulary:      score += 10    # في المفردات
            if kw in benefits:        score += 10    # في الفوائد
            # مكافأة على قِصَر النص (الحديث أكثر تركيزاً)
            score += max(0, 10 - len(text) // 100)

            scored.append((score, hadith))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in scored[:limit]]

    def get_related(self, hadith_id: int, limit: int = 3) -> List[Dict[str, Any]]:
        """يستخدم الروابط الحقيقية من JSON أولاً، ثم يعود للخوارزمية"""
        current = self.get_by_id(hadith_id)
        if not current:
            return []

        # ── الروابط الحقيقية المحررة يدوياً ──
        real_related = current.get("related_hadiths", [])
        if real_related:
            result = []
            for rid in real_related[:limit]:
                h = self.get_by_id(rid)
                if h:
                    result.append(h)
            if result:
                return result

        # ── احتياطي: مقارنة العناوين ──
        title_words = set(current.get("title", "").split())
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for hadith in self.hadiths:
            if hadith["id"] == hadith_id:
                continue
            common = title_words & set(hadith.get("title", "").split())
            if common:
                scored.append((len(common), hadith))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in scored[:limit]]

    def get_categories(self) -> Dict[str, List[int]]:
        """جلب كل التصنيفات مع قائمة الأحاديث لكل تصنيف"""
        return self._topics_index

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        ids = self._topics_index.get(category, [])
        return [self._index[i] for i in ids if i in self._index]

    def get_qudsi_hadiths(self) -> List[Dict[str, Any]]:
        return [h for h in self.hadiths if h.get("hadith_type") == "qudsi"]

    def __len__(self) -> int:
        return len(self.hadiths)


# ═══════════════════════════════════════════════════════════════════
# 4. إدارة بيانات المستخدم (محسّنة بميزات جديدة)
# ═══════════════════════════════════════════════════════════════════

# ── تعريف الشارات ──
BADGES: Dict[str, Dict[str, Any]] = {
    "seedling":   {"emoji": "🌱", "name": "مبتدئ",          "desc": "قراءة 5 أحاديث",       "check": lambda d: len(d.get("read_hadiths", [])) >= 5},
    "student":    {"emoji": "📚", "name": "طالب علم",        "desc": "قراءة 20 حديثاً",      "check": lambda d: len(d.get("read_hadiths", [])) >= 20},
    "graduate":   {"emoji": "🎓", "name": "الخريج",          "desc": "إتمام الـ 42",         "check": lambda d: len(d.get("read_hadiths", [])) >= 42},
    "champion":   {"emoji": "🏆", "name": "الحافظ",          "desc": "نتيجة 100% في اختبار", "check": lambda d: any(q.get("percentage", 0) == 100 for q in d.get("quiz_scores", []))},
    "starred":    {"emoji": "⭐", "name": "المميز",           "desc": "10 أحاديث في المفضلة", "check": lambda d: len(d.get("favorites", [])) >= 10},
    "writer":     {"emoji": "📝", "name": "الكاتب",           "desc": "10 ملاحظات مكتوبة",   "check": lambda d: len(d.get("notes", {})) >= 10},
    "streak7":    {"emoji": "🔥", "name": "الثابت",           "desc": "7 أيام متواصلة",       "check": lambda d: d.get("streak_count", 0) >= 7},
    "streak30":   {"emoji": "💎", "name": "المداوم",          "desc": "30 يوم متواصلة",       "check": lambda d: d.get("streak_count", 0) >= 30},
    "flashcard":  {"emoji": "🃏", "name": "المتدرب",          "desc": "10 بطاقات حفظ مراجعة", "check": lambda d: d.get("flashcard_count", 0) >= 10},
}

_USER_DEFAULTS: Dict[str, Any] = {
    "read_hadiths":          [],
    "favorites":             [],
    "notes":                 {},
    "quiz_scores":           [],
    "study_plan":            [],
    "last_daily":            None,
    "interaction_count":     0,
    "last_support_reminder": None,
    "reminder_enabled":      False,
    "reminder_time":         DEFAULT_REMINDER_TIME,
    "reminder_time_evening": None,     # ← وضع الليل (جديد)
    "reminder_timezone":     DEFAULT_TIMEZONE,
    "last_reminder_sent":    None,
    "last_reminder_evening": None,     # ← (جديد)
    "streak_count":          0,        # ← السلسلة اليومية (جديد)
    "streak_last_date":      None,     # ← (جديد)
    "streak_best":           0,        # ← أعلى سلسلة (جديد)
    "flashcard_count":       0,        # ← عدد البطاقات التي راجعها (جديد)
    "earned_badges":         [],       # ← الشارات المكتسبة (جديد)
    "weekly_reads":          {},       # ← قراءات أسبوعية {ISO_week: count} (جديد)
    "self_assessment":       {},       # ← أعرف/لا أعرف {hadith_id: bool} (جديد)
}


class UserDataManager:
    """إدارة بيانات المستخدمين مع دعم كامل للميزات الجديدة"""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def _get_path(self, user_id: int) -> Path:
        return self.data_dir / f"user_{user_id}.json"

    def _load(self, user_id: int) -> Dict[str, Any]:
        path = self._get_path(user_id)
        if not path.exists():
            return dict(_USER_DEFAULTS)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, default in _USER_DEFAULTS.items():
                if key not in data:
                    data[key] = default
            return data
        except Exception as exc:
            logger.error(f"خطأ في تحميل بيانات {user_id}: {exc}")
            return dict(_USER_DEFAULTS)

    def _save(self, user_id: int, data: Dict[str, Any]) -> bool:
        try:
            with open(self._get_path(user_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as exc:
            logger.error(f"خطأ في حفظ بيانات {user_id}: {exc}")
            return False

    def _update_field(self, user_id: int, **fields) -> bool:
        data = self._load(user_id)
        data.update(fields)
        return self._save(user_id, data)

    # ── الأحاديث المقروءة ─────────────────────────────────────────

    def mark_as_read(self, user_id: int, hadith_id: int) -> bool:
        data = self._load(user_id)
        if hadith_id not in data["read_hadiths"]:
            data["read_hadiths"].append(hadith_id)
            # تحديث القراءات الأسبوعية
            week_key = datetime.now().strftime("%Y-W%W")
            data["weekly_reads"][week_key] = data["weekly_reads"].get(week_key, 0) + 1
            # تحديث السلسلة اليومية
            self._update_streak_in_data(data)
            return self._save(user_id, data)
        return True

    def _update_streak_in_data(self, data: Dict[str, Any]) -> None:
        """تحديث السلسلة اليومية داخل كائن البيانات مباشرة"""
        today = datetime.now().date().isoformat()
        last  = data.get("streak_last_date")
        if last == today:
            return  # نفس اليوم
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
        if last == yesterday:
            data["streak_count"] = data.get("streak_count", 0) + 1
        else:
            data["streak_count"] = 1  # إعادة بدء السلسلة
        data["streak_last_date"] = today
        if data["streak_count"] > data.get("streak_best", 0):
            data["streak_best"] = data["streak_count"]

    def get_read_hadiths(self, user_id: int) -> List[int]:
        return self._load(user_id).get("read_hadiths", [])

    def get_unread_hadiths(self, user_id: int, total: int) -> List[int]:
        read = set(self.get_read_hadiths(user_id))
        return [i for i in range(1, total + 1) if i not in read]

    # ── المفضلة ───────────────────────────────────────────────────

    def add_favorite(self, user_id: int, hadith_id: int) -> bool:
        data = self._load(user_id)
        if hadith_id not in data["favorites"]:
            data["favorites"].append(hadith_id)
            return self._save(user_id, data)
        return True

    def remove_favorite(self, user_id: int, hadith_id: int) -> bool:
        data = self._load(user_id)
        if hadith_id in data["favorites"]:
            data["favorites"].remove(hadith_id)
            return self._save(user_id, data)
        return True

    def get_favorites(self, user_id: int) -> List[int]:
        return self._load(user_id).get("favorites", [])

    def is_favorite(self, user_id: int, hadith_id: int) -> bool:
        return hadith_id in self.get_favorites(user_id)

    # ── الملاحظات ─────────────────────────────────────────────────

    def add_note(self, user_id: int, hadith_id: int, note: str) -> bool:
        data = self._load(user_id)
        data["notes"][str(hadith_id)] = {
            "text": note,
            "timestamp": datetime.now().isoformat(),
        }
        return self._save(user_id, data)

    def get_note(self, user_id: int, hadith_id: int) -> Optional[str]:
        entry = self._load(user_id).get("notes", {}).get(str(hadith_id))
        return entry.get("text") if entry else None

    def delete_note(self, user_id: int, hadith_id: int) -> bool:
        data = self._load(user_id)
        key = str(hadith_id)
        if key in data.get("notes", {}):
            del data["notes"][key]
            return self._save(user_id, data)
        return True

    # ── الاختبارات ────────────────────────────────────────────────

    def save_quiz_score(self, user_id: int, score: int, total: int) -> bool:
        data = self._load(user_id)
        data["quiz_scores"].append({
            "score":      score,
            "total":      total,
            "percentage": round((score / total) * 100, 2) if total else 0,
            "timestamp":  datetime.now().isoformat(),
        })
        return self._save(user_id, data)

    def get_quiz_history(self, user_id: int) -> List[Dict[str, Any]]:
        return self._load(user_id).get("quiz_scores", [])

    # ── حديث اليوم ────────────────────────────────────────────────

    def get_last_daily(self, user_id: int) -> Optional[str]:
        return self._load(user_id).get("last_daily")

    def update_last_daily(self, user_id: int) -> bool:
        return self._update_field(user_id, last_daily=datetime.now().date().isoformat())

    # ── الخطة الدراسية ────────────────────────────────────────────

    def set_study_plan(self, user_id: int, plan: List[int]) -> bool:
        return self._update_field(user_id, study_plan=plan)

    def get_study_plan(self, user_id: int) -> List[int]:
        return self._load(user_id).get("study_plan", [])

    # ── التفاعلات والدعم ──────────────────────────────────────────

    def increment_interaction(self, user_id: int) -> int:
        data = self._load(user_id)
        data["interaction_count"] = data.get("interaction_count", 0) + 1
        self._save(user_id, data)
        return data["interaction_count"]

    def update_support_reminder(self, user_id: int) -> bool:
        return self._update_field(user_id, last_support_reminder=datetime.now().isoformat())

    def should_show_support_reminder(self, user_id: int) -> bool:
        if SUPPORT_REMINDER_INTERVAL <= 0:
            return False
        count = self._load(user_id).get("interaction_count", 0)
        return count > 0 and count % SUPPORT_REMINDER_INTERVAL == 0

    # ── التذكير اليومي ────────────────────────────────────────────

    def enable_reminder(self, user_id: int, time_str: str, timezone: str = DEFAULT_TIMEZONE) -> bool:
        return self._update_field(user_id, reminder_enabled=True, reminder_time=time_str, reminder_timezone=timezone)

    def enable_evening_reminder(self, user_id: int, time_str: str) -> bool:
        return self._update_field(user_id, reminder_time_evening=time_str)

    def disable_evening_reminder(self, user_id: int) -> bool:
        return self._update_field(user_id, reminder_time_evening=None)

    def disable_reminder(self, user_id: int) -> bool:
        return self._update_field(user_id, reminder_enabled=False)

    def get_reminder_settings(self, user_id: int) -> Dict[str, Any]:
        data = self._load(user_id)
        return {
            "enabled":         data.get("reminder_enabled", False),
            "time":            data.get("reminder_time", DEFAULT_REMINDER_TIME),
            "time_evening":    data.get("reminder_time_evening"),
            "timezone":        data.get("reminder_timezone", DEFAULT_TIMEZONE),
            "last_sent":       data.get("last_reminder_sent"),
            "last_evening":    data.get("last_reminder_evening"),
        }

    def update_last_reminder_sent(self, user_id: int, evening: bool = False) -> bool:
        if evening:
            return self._update_field(user_id, last_reminder_evening=datetime.now().isoformat())
        return self._update_field(user_id, last_reminder_sent=datetime.now().isoformat())

    def get_all_users(self) -> List[Tuple[int, Dict[str, Any]]]:
        """إرجاع كل المستخدمين مع بياناتهم الكاملة"""
        users = []
        for path in self.data_dir.glob("user_*.json"):
            try:
                uid  = int(path.stem.split("_")[1])
                data = self._load(uid)
                users.append((uid, data))
            except Exception as exc:
                logger.error(f"خطأ في قراءة {path}: {exc}")
        return users

    def is_banned(self, user_id: int) -> bool:
        return self._load(user_id).get("banned", False)

    def ban_user(self, user_id: int) -> bool:
        return self._update_field(user_id, banned=True)

    def unban_user(self, user_id: int) -> bool:
        return self._update_field(user_id, banned=False)

    def get_all_users_with_reminders(self) -> List[Tuple[int, Dict[str, Any]]]:
        users: List[Tuple[int, Dict[str, Any]]] = []
        for path in self.data_dir.glob("user_*.json"):
            try:
                uid  = int(path.stem.split("_")[1])
                data = self._load(uid)
                if data.get("reminder_enabled"):
                    users.append((uid, {
                        "time":         data.get("reminder_time", DEFAULT_REMINDER_TIME),
                        "time_evening": data.get("reminder_time_evening"),
                        "timezone":     data.get("reminder_timezone", DEFAULT_TIMEZONE),
                        "last_sent":    data.get("last_reminder_sent"),
                        "last_evening": data.get("last_reminder_evening"),
                    }))
            except Exception as exc:
                logger.error(f"خطأ في قراءة {path}: {exc}")
        return users

    # ── السلسلة اليومية ───────────────────────────────────────────

    def get_streak(self, user_id: int) -> Dict[str, Any]:
        data = self._load(user_id)
        return {
            "count": data.get("streak_count", 0),
            "best":  data.get("streak_best", 0),
            "last":  data.get("streak_last_date"),
        }

    # ── بطاقات الحفظ ─────────────────────────────────────────────

    def increment_flashcard(self, user_id: int) -> int:
        data = self._load(user_id)
        data["flashcard_count"] = data.get("flashcard_count", 0) + 1
        self._save(user_id, data)
        return data["flashcard_count"]

    # ── التقييم الذاتي (أعرف/لا أعرف) ───────────────────────────

    def save_self_assessment(self, user_id: int, hadith_id: int, knows: bool) -> bool:
        data = self._load(user_id)
        data["self_assessment"][str(hadith_id)] = knows
        return self._save(user_id, data)

    def get_needs_review(self, user_id: int) -> List[int]:
        data = self._load(user_id)
        return [int(k) for k, v in data.get("self_assessment", {}).items() if not v]

    # ── الشارات ───────────────────────────────────────────────────

    def check_and_award_badges(self, user_id: int) -> List[str]:
        """يتحقق من الشارات المستحقة ويمنح الجديدة — يُعيد قائمة الجديدة"""
        data      = self._load(user_id)
        earned    = set(data.get("earned_badges", []))
        new_ones  = []
        for badge_id, badge in BADGES.items():
            if badge_id not in earned and badge["check"](data):
                earned.add(badge_id)
                new_ones.append(badge_id)
        if new_ones:
            data["earned_badges"] = list(earned)
            self._save(user_id, data)
        return new_ones

    def get_earned_badges(self, user_id: int) -> List[str]:
        return self._load(user_id).get("earned_badges", [])

    # ── الإحصائيات ────────────────────────────────────────────────

    def get_statistics(self, user_id: int, total_hadiths: int) -> Dict[str, Any]:
        data       = self._load(user_id)
        read_count = len(data.get("read_hadiths", []))
        quiz_scores = data.get("quiz_scores", [])
        avg_score  = (
            sum(q["percentage"] for q in quiz_scores) / len(quiz_scores)
            if quiz_scores else 0
        )
        # إحصائيات هذا الأسبوع
        week_key   = datetime.now().strftime("%Y-W%W")
        week_reads = data.get("weekly_reads", {}).get(week_key, 0)
        # إحصائيات آخر 7 أيام
        last_7_keys = [
            (datetime.now().date() - timedelta(days=i)).strftime("%Y-W%W")
            for i in range(7)
        ]
        week_reads_7 = sum(data.get("weekly_reads", {}).get(k, 0) for k in set(last_7_keys))
        # أفضل نتيجة في الاختبار
        best_quiz = max((q["percentage"] for q in quiz_scores), default=0)
        return {
            "read_hadiths":        read_count,
            "total_hadiths":       total_hadiths,
            "progress_percentage": round((read_count / total_hadiths) * 100, 2) if total_hadiths else 0,
            "favorites":           len(data.get("favorites", [])),
            "notes":               len(data.get("notes", {})),
            "quizzes_taken":       len(quiz_scores),
            "average_quiz_score":  round(avg_score, 2),
            "best_quiz_score":     round(best_quiz, 2),
            "streak":              data.get("streak_count", 0),
            "streak_best":         data.get("streak_best", 0),
            "week_reads":          week_reads_7,
            "earned_badges":       data.get("earned_badges", []),
            "flashcard_count":     data.get("flashcard_count", 0),
            "needs_review":        len([v for v in data.get("self_assessment", {}).values() if not v]),
        }


# ═══════════════════════════════════════════════════════════════════
# 5. أنظمة الحالة
# ═══════════════════════════════════════════════════════════════════

class ConversationMemory:
    """ذاكرة المحادثات — تحتفظ بسياق الحديث الأخير لتحسين AI"""

    def __init__(self, max_history: int = MAX_CONVERSATION_HISTORY) -> None:
        self._sessions: Dict[int, deque] = {}
        self._active_hadith: Dict[int, int] = {}   # user_id → hadith_id المناقَش
        self.max_history = max_history

    def get(self, user_id: int) -> deque:
        if user_id not in self._sessions:
            self._sessions[user_id] = deque(maxlen=self.max_history)
        return self._sessions[user_id]

    def add_message(self, user_id: int, role: str, content: str) -> None:
        self.get(user_id).append({"role": role, "content": content})

    def set_active_hadith(self, user_id: int, hadith_id: int) -> None:
        self._active_hadith[user_id] = hadith_id

    def get_active_hadith(self, user_id: int) -> Optional[int]:
        return self._active_hadith.get(user_id)

    def clear(self, user_id: int) -> None:
        if user_id in self._sessions:
            self._sessions[user_id].clear()
        self._active_hadith.pop(user_id, None)


class FeedbackSystem:
    _waiting: Dict[int, bool] = {}

    @classmethod
    def start(cls, user_id: int) -> None:
        cls._waiting[user_id] = True

    @classmethod
    def stop(cls, user_id: int) -> None:
        cls._waiting.pop(user_id, None)

    @classmethod
    def is_active(cls, user_id: int) -> bool:
        return cls._waiting.get(user_id, False)


class NoteSystem:
    _waiting: Dict[int, int] = {}

    @classmethod
    def start(cls, user_id: int, hadith_id: int) -> None:
        cls._waiting[user_id] = hadith_id

    @classmethod
    def stop(cls, user_id: int) -> None:
        cls._waiting.pop(user_id, None)

    @classmethod
    def is_active(cls, user_id: int) -> bool:
        return user_id in cls._waiting

    @classmethod
    def get_hadith_id(cls, user_id: int) -> Optional[int]:
        return cls._waiting.get(user_id)


class FlashcardSystem:
    """حالة جلسة بطاقات الحفظ"""
    _sessions: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def start(cls, user_id: int, hadith_ids: List[int]) -> None:
        random.shuffle(hadith_ids)
        cls._sessions[user_id] = {
            "queue":   hadith_ids,
            "index":   0,
            "correct": 0,
            "total":   len(hadith_ids),
        }

    @classmethod
    def get_current(cls, user_id: int) -> Optional[int]:
        s = cls._sessions.get(user_id)
        if not s or s["index"] >= len(s["queue"]):
            return None
        return s["queue"][s["index"]]

    @classmethod
    def advance(cls, user_id: int, knew_it: bool) -> bool:
        """يُقدّم للبطاقة التالية — يُعيد True إذا انتهت الجلسة"""
        s = cls._sessions.get(user_id)
        if not s:
            return True
        if knew_it:
            s["correct"] += 1
        s["index"] += 1
        return s["index"] >= len(s["queue"])

    @classmethod
    def get_result(cls, user_id: int) -> Optional[Dict[str, Any]]:
        return cls._sessions.pop(user_id, None)

    @classmethod
    def is_active(cls, user_id: int) -> bool:
        return user_id in cls._sessions

    @classmethod
    def cancel(cls, user_id: int) -> None:
        cls._sessions.pop(user_id, None)


# ═══════════════════════════════════════════════════════════════════
# 6. أنظمة مساعدة
# ═══════════════════════════════════════════════════════════════════

class SupportSystem:
    _MESSAGES = [
        "💝 *هل استفدت من نبراس؟*\n\nدعمك يساعدنا على الاستمرار! ☕\nكوب قهوة صغير = تحفيز كبير 🌟",
        "🌟 *نبراس يسعد بخدمتك!*\n\nإن شاء الله ينفع الله بك ✨\nدعمك يعيننا على التطوير ☕",
        "✨ *جزاك الله خيراً على استخدامك نبراس*\n\nمساهمتك تساعد على تحسين البوت 💪",
        "🎯 *نبراس في خدمتك دائماً*\n\nساعدنا على الاستمرار في العطاء 🌱",
    ]

    @staticmethod
    def get_button() -> InlineKeyboardButton:
        return InlineKeyboardButton("☕ ادعم البوت", url=SUPPORT_LINK)

    @staticmethod
    def get_message() -> str:
        return random.choice(SupportSystem._MESSAGES)

    @staticmethod
    def get_stats_footer() -> str:
        return (
            "\n─────────────────\n"
            "💝 *استمتعت بنبراس؟*\n"
            "ساعدنا على الاستمرار ☕\n"
            f"[ادعم البوت هنا]({SUPPORT_LINK})"
        )


class MonetagSystem:
    """
    نظام إعلانات Monetag (Interstitial/Pop) للبوت
    ─────────────────────────────────────────────────
    آلية العمل:
      - يُرسل رابط Monetag Direct Link كزر للمستخدم
      - عند الضغط يُفتح الإعلان في المتصفح (Interstitial/Pop)

    الأماكن الاستراتيجية:
      1. بعد إتمام الاختبار (نتيجة الاختبار)
      2. بعد إتمام جلسة بطاقات الحفظ
      3. كل MONETAG_INTERVAL تفاعل (شرح AI)
      4. بعد حديث اليوم (مرة واحدة/يوم)

    متغيرات البيئة المطلوبة:
      MONETAG_ENABLED      = True/False
      MONETAG_DIRECT_LINK  = https://omg10.com/4/10632325  (الرابط المباشر)
    """

    @staticmethod
    def _get_ad_url() -> str:
        """إرجاع الرابط المباشر للإعلان"""
        return os.getenv("MONETAG_DIRECT_LINK", MONETAG_DIRECT_LINK).strip()

    @classmethod
    async def send_ad(
        cls,
        bot,
        chat_id: int,
        context_label: str = "",
    ) -> bool:
        """
        إرسال إعلان Monetag — يُعيد True إذا نجح الإرسال
        context_label: نص تشجيعي يظهر فوق الإعلان
        """
        if not MONETAG_ENABLED:
            return False

        ad_url = cls._get_ad_url()
        if not ad_url:
            logger.warning("Monetag: MONETAG_DIRECT_LINK غير مضبوط، تم تخطي الإعلان.")
            return False

        try:
            header = "📢 *إعلان*"
            if context_label:
                header = f"{context_label}\n\n📢 *إعلان*"

            message_text = (
                f"{header}\n\n"
                "🌐 اضغط على الزر أدناه لدعم البوت ومشاهدة الإعلان:"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 عرض الإعلان", url=ad_url)]
            ])

            await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

            logger.info(f"📢 Monetag ad sent → {chat_id} [{context_label}]")
            return True

        except Exception as exc:
            logger.debug(f"Monetag send error: {exc}")
            return False

    @classmethod
    def should_show_interval_ad(cls, user_id: int, current_interactions: int) -> bool:
        """هل حان وقت إعلان التفاعل الدوري؟"""
        if MONETAG_INTERVAL <= 0:
            return False
        last = _monetag_last_shown.get(user_id, 0)
        if current_interactions - last >= MONETAG_INTERVAL:
            _monetag_last_shown[user_id] = current_interactions
            return True
        return False


class ReminderSystem:
    @staticmethod
    def parse_time(time_str: str) -> Optional[datetime_time]:
        try:
            h, m = map(int, time_str.split(":"))
            if 0 <= h < 24 and 0 <= m < 60:
                return datetime_time(hour=h, minute=m)
        except (ValueError, AttributeError):
            pass
        return None

    @staticmethod
    def should_send(last_sent: Optional[str], timezone_str: str) -> bool:
        if not last_sent:
            return True
        try:
            tz   = ZoneInfo(timezone_str)
            last = datetime.fromisoformat(last_sent)
            # ✅ إصلاح: تأكد أن last يحمل timezone قبل المقارنة
            if last.tzinfo is None:
                last = last.replace(tzinfo=tz)
            return last.astimezone(tz).date() < datetime.now(tz).date()
        except Exception:
            return True

    @staticmethod
    def build_message(hadith: Dict[str, Any], unread_count: int = 0) -> str:
        streak_line = ""
        base = (
            "⏰ *تذكيرك اليومي من نبراس*\n\n"
            f"📖 *الحديث رقم {hadith['id']}: {MessageFormatter.esc(hadith['title'])}*\n\n"
            f"«{MessageFormatter.esc(hadith['text'][:300])}»\n\n"
            f"📚 *الراوي:* {MessageFormatter.esc(hadith['narrator'])}\n"
        )
        if unread_count > 0:
            base += f"📚 *تبقى لك:* {unread_count} حديثاً لإتمام الأربعين!\n"
        base += "\n💡 استخدم /reminder لإدارة التذكير اليومي"
        return base

    @staticmethod
    def build_evening_message(hadith: Dict[str, Any]) -> str:
        return (
            "🌙 *حديث المساء من نبراس*\n\n"
            f"📖 *{MessageFormatter.esc(hadith['title'])}*\n\n"
            f"«{MessageFormatter.esc(hadith['text'][:300])}»\n\n"
            "💭 تأمل في هذا الحديث قبل نومك 🌟"
        )


class SmartQuestionSystem:
    _KEYWORD_QUESTIONS: Dict[str, str] = {
        "نية":   "ما أهمية النية في الأعمال؟",
        "إيمان": "كيف نقوي الإيمان من خلال هذا الحديث؟",
        "صلاة":  "ما الأحكام المستفادة عن الصلاة؟",
        "صوم":   "ما فضل الصيام في هذا الحديث؟",
        "زكاة":  "ما شروط الزكاة المذكورة؟",
        "حج":    "ما أركان الحج الواردة؟",
        "تقوى":  "كيف نحقق التقوى عملياً؟",
        "صدق":   "ما ثمرات الصدق؟",
        "حلال":  "كيف نميز بين الحلال والحرام؟",
        "حرام":  "لماذا حُرم ما ذُكر في الحديث؟",
        "رحمة":  "كيف نجسّد الرحمة في حياتنا؟",
        "ظلم":   "ما عقوبة الظلم المستفادة؟",
    }

    @classmethod
    def generate(cls, hadith: Dict[str, Any]) -> List[str]:
        questions = [
            f"ما المعنى الإجمالي للحديث رقم {hadith['id']}؟",
            f"ما الفوائد العملية من حديث {hadith['title']}؟",
            f"كيف أطبق حديث '{hadith['title']}' في حياتي اليومية؟",
        ]
        if hadith.get("id", 0) > 1:
            questions.append(f"ما العلاقة بين الحديث {hadith['id']} والأحاديث الأخرى؟")
        text = hadith.get("text", "").lower()
        for kw, q in cls._KEYWORD_QUESTIONS.items():
            if kw in text:
                questions.append(q)
        # أسئلة من الموضوعات
        for topic in hadith.get("topics_arabic", [])[:2]:
            questions.append(f"كيف يتعلق موضوع '{topic}' بحياتنا اليومية؟")
        return random.sample(questions, min(5, len(questions)))

    @classmethod
    def format_message(cls, hadith: Dict[str, Any], count: int = 3) -> str:
        questions = cls.generate(hadith)[:count]
        if not questions:
            return ""
        lines = ["\n\n💡 *أسئلة مقترحة — اضغط للنسخ ثم أرسلها:*\n"]
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. `{q}`\n")
        return "".join(lines).rstrip()


# ═══════════════════════════════════════════════════════════════════
# 7. تنسيق الرسائل (محسّن بالكامل)
# ═══════════════════════════════════════════════════════════════════

class MessageFormatter:
    _SUGGESTION_RE = re.compile(r"##(.*?)##", re.DOTALL)

    @staticmethod
    def esc(text: str) -> str:
        """Escape رموز Markdown الخطرة في النصوص الديناميكية"""
        for ch in ('_', '*', '[', ']', '`'):
            text = text.replace(ch, '\\' + ch)
        return text

    @classmethod
    def format_response(cls, text: str) -> str:
        match = cls._SUGGESTION_RE.search(text)
        clean = cls._SUGGESTION_RE.sub("", text).strip()
        if not match:
            return clean
        suggestion = match.group(1).strip()
        if len(suggestion) < 5 or suggestion == "السؤال":
            return clean
        return (
            clean
            + "\n\n💡 *سؤال مقترح:*\n"
            "_(انقر للنسخ)_\n"
            f"`{suggestion}`"
        )

    @staticmethod
    def build_hadith_display(
        hadith: Dict[str, Any],
        include_actions: bool = False,
        is_favorite: bool = False,
        has_note: bool = False,
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """بناء عرض الحديث — يستخدم الفصل بين مقدمة الراوي ونص الحديث"""
        hid = hadith["id"]

        # ── شارة الحديث القدسي ──
        type_badge = ""
        if hadith.get("hadith_type") == "qudsi":
            type_badge = " ✨ *قدسي*"

        lines = [
            f"📖 *الحديث رقم {hid}: {MessageFormatter.esc(hadith['title'])}*{type_badge}",
            "ــــــــــــــــــــــــــــــــــــــــ",
            "",
        ]

        # ── إضافة شرح الحديث القدسي ──
        if hadith.get("hadith_type") == "qudsi":
            lines.append("💎 هذا حديث قدسي — كلام الله تعالى برواية النبي ﷺ\n")

        # ── فصل مقدمة الراوي عن نص الحديث ──
        intro = hadith.get("narrator_intro", "").strip()
        body  = hadith.get("hadith_text_only", "").strip()

        if intro and body:
            lines.append(f"🗣️ {MessageFormatter.esc(intro)}")
            lines.append("")
            lines.append("📜 *قال رسول الله ﷺ:*")
            lines.append(f"«{MessageFormatter.esc(body)}»")
        else:
            lines.append(f"👤 *عن {MessageFormatter.esc(hadith['narrator'])} قال:*")
            lines.append(f"«{MessageFormatter.esc(hadith['text'])}»")

        lines.append("")
        lines.append(f"📚 *المصدر:* {MessageFormatter.esc(hadith['source'])}")

        if hadith.get("vocabulary"):
            lines.append("")
            lines.append("🔍 *معاني المفردات:*")
            lines.extend(f"• {MessageFormatter.esc(str(v))}" for v in hadith["vocabulary"])

        if hadith.get("benefits"):
            lines.append("")
            lines.append("✨ *من فوائد الحديث:*")
            lines.extend(f"• {MessageFormatter.esc(str(b))}" for b in hadith["benefits"])

        # ── الموضوعات ──
        if hadith.get("topics_arabic"):
            topics_str = " · ".join(MessageFormatter.esc(str(t)) for t in hadith["topics_arabic"][:5])
            lines.append(f"\n🏷️ *المواضيع:* {topics_str}")

        text = "\n".join(lines)
        keyboard = None

        if include_actions:
            fav_label  = f"{'⭐' if is_favorite else '☆'} مفضلة"
            note_label = f"📝 {'تعديل' if has_note else 'إضافة'} ملاحظة"
            buttons = [
                [
                    InlineKeyboardButton(fav_label,  callback_data=f"fav_{hid}"),
                    InlineKeyboardButton(note_label, callback_data=f"note_{hid}"),
                ],
                [
                    InlineKeyboardButton("👤 بطاقة الراوي",  callback_data=f"narrator_{hid}"),
                    InlineKeyboardButton("🔗 أحاديث مرتبطة", callback_data=f"related_{hid}"),
                ],
                [
                    InlineKeyboardButton("💬 شرح مبسط",      callback_data=f"simple_{hid}"),
                    InlineKeyboardButton("📖 شروحات متعددة", callback_data=f"compare_{hid}"),
                ],
                [
                    InlineKeyboardButton("🌍 الترجمة",        callback_data=f"english_{hid}"),
                    InlineKeyboardButton("📤 مشاركة",         callback_data=f"share_{hid}"),
                ],
                [
                    InlineKeyboardButton("🃏 بطاقة حفظ",      callback_data=f"flashcard_{hid}"),
                    InlineKeyboardButton("🤔 أعرف؟",           callback_data=f"selftest_{hid}"),
                ],
                [
                    InlineKeyboardButton("💬 تواصل معنا",     callback_data="feedback_start"),
                ],
            ]
            keyboard = InlineKeyboardMarkup(buttons)

        return text, keyboard

    @staticmethod
    def build_narrator_card(narrator: Dict[str, Any]) -> str:
        """بناء بطاقة الراوي التفاعلية"""
        name    = narrator.get("arabic", "")
        kunya   = narrator.get("kunya_arabic", "")
        title   = narrator.get("title_arabic", "")
        tribe   = narrator.get("tribe_arabic", "")
        died_ah = narrator.get("died_ah")
        died_ce = narrator.get("died_ce")
        count   = narrator.get("narrations_count")
        bio     = narrator.get("bio_arabic", "")
        paradise = narrator.get("is_ten_promised_paradise", False)
        companion = narrator.get("is_companion", True)

        lines = [f"👤 *{name}*"]
        if kunya:
            lines.append(f"🏷️ *الكنية:* {kunya}")
        if title:
            lines.append(f"🌟 *اللقب:* {title}")
        if tribe:
            lines.append(f"🏺 *القبيلة:* {tribe}")
        lines.append("")

        death_parts = []
        if died_ah:
            death_parts.append(f"{died_ah} هـ")
        if died_ce:
            death_parts.append(f"{died_ce} م")
        if death_parts:
            lines.append(f"📅 *الوفاة:* {' / '.join(death_parts)}")

        if count:
            lines.append(f"📜 *عدد مروياته:* {count:,} حديث")

        badges_parts = []
        if companion:
            badges_parts.append("صحابي جليل ✓")
        if paradise:
            badges_parts.append("⭐ من العشرة المبشرين بالجنة")
        if badges_parts:
            lines.append(f"🏅 {' | '.join(badges_parts)}")

        if bio:
            lines.append(f"\n{MessageFormatter.esc(bio)}")

        return "\n".join(lines)

    @staticmethod
    def build_english_display(hadith: Dict[str, Any]) -> str:
        """بناء العرض الإنجليزي للحديث"""
        lines = [
            f"🌍 *English — Hadith #{hadith['id']}*",
            f"*{MessageFormatter.esc(hadith['title'])}*",
            "────────────────────────────",
            "",
        ]
        if hadith.get("english_narrator"):
            lines.append(f"🗣️ {MessageFormatter.esc(hadith['english_narrator'])}")
            lines.append("")
        if hadith.get("english_text"):
            lines.append(f"📜 The Prophet ﷺ said:")
            lines.append(f"«{MessageFormatter.esc(hadith['english_text'])}»")
        lines.append(f"\n📚 *Source:* {hadith.get('source', '')}")
        return "\n".join(lines)

    @staticmethod
    def build_share_text(hadith: Dict[str, Any]) -> str:
        """بناء نص الحديث الجاهز للمشاركة — بدون Markdown لتجنب أخطاء التنسيق"""
        body = hadith.get("hadith_text_only") or hadith.get("text", "")
        narrator = hadith.get("narrator", "")
        # إذا كان narrator dict، خذ النص العربي
        if isinstance(narrator, dict):
            narrator = narrator.get("arabic", str(narrator))
        source = hadith.get("source", "")
        lines = [
            f"📖 الحديث رقم {hadith['id']} من الأربعين النووية",
            f"{hadith['title']}",
            "",
            "قال رسول الله ﷺ:",
            f"«{body}»",
            "",
            f"📚 عن: {narrator}",
            f"المصدر: {source}",
            "",
            "📲 عبر @NibrasNawawi_bot",
        ]
        return "\n".join(lines)

    @staticmethod
    def build_hadith_list(hadiths: List[Dict[str, Any]]) -> str:
        lines = ["📚 *فهرس الأربعين النووية:*", ""]
        for h in hadiths:
            badge = " ✨" if h.get("hadith_type") == "qudsi" else ""
            lines.append(f"الحديث {h['id']}: {h['title']}{badge}")
        return "\n".join(lines)

    @staticmethod
    def build_search_results(results: List[Dict[str, Any]], keyword: str) -> str:
        if not results:
            suggestions = [
                "• تأكد من الإملاء الصحيح",
                "• جرب كلمة أقصر أو مرادفاً",
                "• مثال: النية، الصلاة، الإيمان",
            ]
            return (
                f"🔍 لم أجد نتائج للبحث عن: *{MessageFormatter.esc(keyword)}*\n\n"
                "💡 *اقتراحات:*\n" + "\n".join(suggestions)
            )

        # معاينة النص مع تمييز الكلمة
        def preview(hadith: Dict[str, Any], kw: str) -> str:
            text = hadith.get("text", "")
            kw_l = kw.lower()
            idx  = text.lower().find(kw_l)
            if idx == -1:
                # ابحث في العنوان
                return ""
            start = max(0, idx - 30)
            end   = min(len(text), idx + len(kw) + 50)
            snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
            return f"\n   _{MessageFormatter.esc(snippet)}_"

        total = len(results)
        lines = [
            f"🔍 *نتائج: «{MessageFormatter.esc(keyword)}»*",
            f"📊 {total} نتيجة مرتبة حسب الصلة:",
            "ــــــــــــــــ",
        ]

        for h in results[:15]:  # عرض أول 15 نتيجة
            badge   = " ✨" if h.get("hadith_type") == "qudsi" else ""
            topics  = h.get("topics_arabic", [])
            tag     = f" • _{MessageFormatter.esc(topics[0])}_" if topics else ""
            snip    = preview(h, keyword)
            lines.append(
                f"\n*{h['id']}.* {MessageFormatter.esc(h['title'])}{badge}{tag}{snip}"
            )

        if total > 15:
            lines.append(f"\n_... و {total - 15} نتيجة أخرى، خصّص بحثك أكثر_")

        lines.append("\n💡 أرسل رقم الحديث لعرضه كاملاً")
        return "\n".join(lines)

    @staticmethod
    def build_statistics(stats: Dict[str, Any]) -> str:
        progress = stats["progress_percentage"]
        filled   = int(progress / 10)
        bar      = "▰" * filled + "▱" * (10 - filled)

        # شريط السلسلة
        streak       = stats.get("streak", 0)
        streak_best  = stats.get("streak_best", 0)
        streak_fire  = "🔥" * min(streak, 5)

        # الشارات
        earned = stats.get("earned_badges", [])
        badges_str = " ".join(BADGES[b]["emoji"] for b in earned if b in BADGES) if earned else "لا توجد بعد"

        # أسبوع
        week_reads = stats.get("week_reads", 0)

        lines = [
            "📊 *إحصائياتك في نبراس*",
            "ــــــــــــــــــــــــــــــــــ",
            "",
            "*🗓️ هذا الأسبوع:*",
            f"• 📖 قرأت {week_reads} حديثاً",
            f"• 🔥 السلسلة: {streak} يوم متواصل {streak_fire}",
            f"• 🏆 أعلى سلسلة: {streak_best} يوم",
            "",
            "*📈 الإجمالي:*",
            f"• 📖 الأحاديث المقروءة: {stats['read_hadiths']}/{stats['total_hadiths']}",
            f"• 📊 نسبة الإنجاز: {progress}%",
            f"• ⭐ المفضلة: {stats['favorites']} حديث",
            f"• 📝 الملاحظات: {stats['notes']}",
            "",
            f"*🎓 الاختبارات:*",
            f"• عدد الاختبارات: {stats['quizzes_taken']}",
            f"• متوسط النتائج: {stats['average_quiz_score']}%",
            f"• أفضل نتيجة: {stats['best_quiz_score']}%",
            "",
            f"*🃏 بطاقات الحفظ:* {stats.get('flashcard_count', 0)} مراجعة",
            f"*📋 تحتاج مراجعة:* {stats.get('needs_review', 0)} حديث",
            "",
            f"التقدم: {bar} {progress}%",
            "",
            f"🏅 *شاراتك:* {badges_str}",
        ]
        return "\n".join(lines)

    @staticmethod
    def build_categories_menu(categories: Dict[str, List[int]]) -> Tuple[str, InlineKeyboardMarkup]:
        """بناء قائمة التصنيفات التفاعلية"""
        text = "🏷️ *تصفح الأحاديث بالموضوع*\n\nاختر تصنيفاً:"
        buttons = []
        for cat, ids in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            label = f"{cat} ({len(ids)})"
            cb    = f"cat_{cat[:28]}"  # 28 حرف × 2 bytes + 4 = 60 bytes < 64
            buttons.append([InlineKeyboardButton(label, callback_data=cb)])
        buttons.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="start")])
        return text, InlineKeyboardMarkup(buttons)

    @staticmethod
    def build_flashcard(hadith: Dict[str, Any], show_answer: bool = False) -> Tuple[str, InlineKeyboardMarkup]:
        """بناء بطاقة حفظ تفاعلية"""
        hid  = hadith["id"]
        body = hadith.get("hadith_text_only") or hadith.get("text", "")

        if not show_answer:
            text = (
                f"🃏 *بطاقة حفظ — الحديث {hid}*\n"
                f"*{MessageFormatter.esc(hadith['title'])}*\n\n"
                "━━━━━━━━━━━━━━━━━\n\n"
                f"«{MessageFormatter.esc(body[:200])}»\n\n"
                "━━━━━━━━━━━━━━━━━\n\n"
                "_هل تعرف راوي هذا الحديث ومصدره؟_"
            )
            buttons = [
                [
                    InlineKeyboardButton("🔍 اكشف الراوي",  callback_data=f"fc_reveal_{hid}"),
                ],
                [
                    InlineKeyboardButton("✅ حفظته!",        callback_data=f"fc_know_{hid}"),
                    InlineKeyboardButton("❓ لا أتذكره",     callback_data=f"fc_dontknow_{hid}"),
                ],
                [InlineKeyboardButton("⏭️ تخطى",            callback_data=f"fc_skip_{hid}")],
                [InlineKeyboardButton("🚪 إنهاء الجلسة",   callback_data="fc_end")],
            ]
        else:
            text = (
                f"🃏 *الحديث {hid}: {MessageFormatter.esc(hadith['title'])}*\n\n"
                f"📜 «{MessageFormatter.esc(body[:200])}»\n\n"
                f"👤 *الراوي:* {MessageFormatter.esc(hadith['narrator'])}\n"
                f"📚 *المصدر:* {MessageFormatter.esc(hadith['source'])}\n\n"
                "_هل حفظته؟_"
            )
            buttons = [
                [
                    InlineKeyboardButton("✅ نعم، حفظته!",   callback_data=f"fc_know_{hid}"),
                    InlineKeyboardButton("❓ لا بعد",         callback_data=f"fc_dontknow_{hid}"),
                ],
                [InlineKeyboardButton("🚪 إنهاء الجلسة",   callback_data="fc_end")],
            ]
        return text, InlineKeyboardMarkup(buttons)


# ═══════════════════════════════════════════════════════════════════
# 8. نظام الاختبارات
# ═══════════════════════════════════════════════════════════════════

class QuizSystem:
    active_quizzes: Dict[int, Dict[str, Any]] = {}
    _TYPE_EMOJI = {"narrator": "👤", "title": "📖", "completion": "✍️", "source": "📚"}

    @classmethod
    def generate_quiz(cls, hadith_db: HadithDatabase, question_count: int = 5) -> List[Dict[str, Any]]:
        all_hadiths   = hadith_db.get_all()
        question_count = min(question_count, len(all_hadiths))
        selected      = random.sample(all_hadiths, question_count)
        questions: List[Dict[str, Any]] = []
        types = ["narrator", "title", "completion", "source"]
        for hadith in selected:
            q_type   = random.choice(types)
            question = cls._make_question(q_type, hadith, all_hadiths)
            if not cls._is_valid(question):
                question = cls._make_narrator_q(hadith, all_hadiths)
            if cls._is_valid(question):
                questions.append(question)
        return questions

    @classmethod
    def _make_question(cls, q_type: str, hadith: Dict[str, Any], all_hadiths: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if q_type == "narrator":
            return cls._make_narrator_q(hadith, all_hadiths)
        elif q_type == "title":
            return cls._make_title_q(hadith, all_hadiths)
        elif q_type == "completion":
            return cls._make_completion_q(hadith, all_hadiths)
        else:
            return cls._make_source_q(hadith, all_hadiths)

    @staticmethod
    def _build_options(correct: str, pool: List[str], count: int = 3) -> List[str]:
        others = [x for x in set(pool) if x != correct]
        random.shuffle(others)
        opts = [correct] + others[:count]
        random.shuffle(opts)
        return opts

    @classmethod
    def _make_narrator_q(cls, h: Dict[str, Any], all_h: List[Dict[str, Any]]) -> Dict[str, Any]:
        correct = h["narrator"]
        pool = [x["narrator"] for x in all_h] + [
            "أبو هريرة", "عمر بن الخطاب", "عائشة",
            "أنس بن مالك", "ابن عباس", "أبو سعيد الخدري",
        ]
        return {"hadith_id": h["id"], "question": f"من راوي الحديث: *{MessageFormatter.esc(h['title'])}*؟",
                "options": cls._build_options(correct, pool), "correct_answer": correct, "type": "narrator"}

    @classmethod
    def _make_title_q(cls, h: Dict[str, Any], all_h: List[Dict[str, Any]]) -> Dict[str, Any]:
        correct = h["title"]
        pool    = [x["title"] for x in all_h]
        preview = h["text"][:80] + ("..." if len(h["text"]) > 80 else "")
        return {"hadith_id": h["id"], "question": f"ما عنوان الحديث الذي يبدأ بـ:\n«{MessageFormatter.esc(preview)}»",
                "options": cls._build_options(correct, pool), "correct_answer": correct, "type": "title"}

    @classmethod
    def _make_completion_q(cls, h: Dict[str, Any], all_h: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        words = h["text"].split()
        if len(words) < 15:
            return None
        cut        = random.randint(len(words) // 3, len(words) // 2)
        first_part = " ".join(words[:cut])
        correct    = " ".join(words[cut:cut + 5])
        pool: List[str] = []
        for other in all_h:
            if other["id"] == h["id"]:
                continue
            ow = other["text"].split()
            if len(ow) < 5:
                continue
            si    = random.randint(0, len(ow) - 5)
            chunk = " ".join(ow[si:si + 5])
            if chunk != correct:
                pool.append(chunk)
            if len(pool) >= 10:
                break
        pool.extend(["والله أعلم بذلك", "وهو على كل شيء قدير", "إن الله غفور رحيم"])
        return {"hadith_id": h["id"], "question": f"أكمل الحديث:\n«{MessageFormatter.esc(first_part)}... »",
                "options": cls._build_options(correct, pool), "correct_answer": correct, "type": "completion"}

    @classmethod
    def _make_source_q(cls, h: Dict[str, Any], all_h: List[Dict[str, Any]]) -> Dict[str, Any]:
        correct = h["source"]
        pool = [x["source"] for x in all_h] + [
            "صحيح البخاري", "صحيح مسلم", "سنن أبي داود",
            "سنن الترمذي", "سنن النسائي", "سنن ابن ماجه",
        ]
        return {"hadith_id": h["id"], "question": f"ما مصدر الحديث: *{MessageFormatter.esc(h['title'])}*؟",
                "options": cls._build_options(correct, pool), "correct_answer": correct, "type": "source"}

    @staticmethod
    def _is_valid(q: Optional[Dict[str, Any]]) -> bool:
        if not q:
            return False
        if not all(f in q for f in ("question", "options", "correct_answer", "type")):
            return False
        if len(q["options"]) < 2:
            return False
        if q["correct_answer"] not in q["options"]:
            return False
        return True

    @classmethod
    def start(cls, user_id: int, questions: List[Dict[str, Any]]) -> None:
        cls.active_quizzes[user_id] = {"questions": questions, "current_index": 0, "score": 0, "answers": []}

    @classmethod
    def get_current_question(cls, user_id: int) -> Optional[Dict[str, Any]]:
        quiz = cls.active_quizzes.get(user_id)
        if not quiz:
            return None
        idx = quiz["current_index"]
        return quiz["questions"][idx] if idx < len(quiz["questions"]) else None

    @classmethod
    def submit_answer(cls, user_id: int, answer: str) -> Tuple[bool, Optional[str]]:
        quiz = cls.active_quizzes.get(user_id)
        if not quiz:
            return False, None
        question   = quiz["questions"][quiz["current_index"]]
        is_correct = answer == question.get("correct_answer")
        if is_correct:
            quiz["score"] += 1
        quiz["answers"].append({
            "question_id":    quiz["current_index"],
            "user_answer":    answer,
            "correct_answer": question.get("correct_answer"),
            "is_correct":     is_correct,
        })
        quiz["current_index"] += 1
        return is_correct, question.get("correct_answer")

    @classmethod
    def get_result(cls, user_id: int) -> Optional[Dict[str, Any]]:
        quiz = cls.active_quizzes.pop(user_id, None)
        if not quiz:
            return None
        total = len(quiz["questions"])
        score = quiz["score"]
        return {"score": score, "total": total, "percentage": round((score / total) * 100, 2) if total else 0, "answers": quiz["answers"]}

    @classmethod
    def is_active(cls, user_id: int) -> bool:
        return user_id in cls.active_quizzes

    @classmethod
    def cancel(cls, user_id: int) -> None:
        cls.active_quizzes.pop(user_id, None)

    @staticmethod
    def build_result_text(result: Dict[str, Any]) -> str:
        pct = result["percentage"]
        if pct >= 90:
            grade, emoji = "ممتاز! 🏆", "🌟"
        elif pct >= 70:
            grade, emoji = "جيد جداً! 👏", "✨"
        elif pct >= 50:
            grade, emoji = "جيد! 👍", "💪"
        else:
            grade, emoji = "يحتاج تحسين 📚", "💡"
        return (
            f"{emoji} *نتيجة الاختبار*\n"
            "ــــــــــــــــــــــ\n\n"
            f"✅ الصحيح: {result['score']}/{result['total']}\n"
            f"📊 النسبة: {pct}%\n"
            f"🎯 التقييم: {grade}\n\n"
            "💪 استمر في التعلم!"
        )


# ═══════════════════════════════════════════════════════════════════
# 9. الذكاء الاصطناعي (محسّن بسياق الحديث)
# ═══════════════════════════════════════════════════════════════════

class NibrasAI:
    OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
    GOOGLE_URL       = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    _PROMPTS = {
        "normal": (
            "أنت 'نبراس'، مساعد ذكي متخصص حصرياً في شرح وتفسير 'الأربعين النووية'.\n"
            "تتميز بالدقة العلمية، الوضوح، الوقار، والتركيز على التطبيق العملي.\n\n"
            "⚠️ في نهاية كل رد اقترح سؤالاً واحداً ذكياً بين ## ##\n"
            "مثال: ##ما العلاقة بين هذا الحديث والحديث السابع؟##"
        ),
        "simple": (
            "أنت معلم صبور يشرح للأطفال والمبتدئين.\n"
            "اشرح بلغة بسيطة مع أمثلة من الحياة اليومية وجمل قصيرة.\n"
            "في النهاية اقترح سؤالاً مناسباً بين ## ##"
        ),
        "compare": (
            "أنت عالم يقدم شروحاً مقارنة للأحاديث:\n"
            "1. الفهم اللغوي  2. الشرح الفقهي  3. الجوانب الأخلاقية  4. التطبيق المعاصر\n"
            "في النهاية اقترح سؤالاً عميقاً بين ## ##"
        ),
    }

    def __init__(self, openrouter_key: str, google_key: Optional[str], memory: ConversationMemory) -> None:
        self.openrouter_key = openrouter_key
        self.google_key     = google_key
        self.memory         = memory

    async def generate_response(
        self,
        user_id: int,
        user_message: str,
        additional_context: str = "",
        mode: str = "normal",
        active_hadith: Optional[Dict[str, Any]] = None,
    ) -> str:
        messages = self._build_messages(user_id, user_message, additional_context, mode, active_hadith)

        if self.google_key:
            try:
                text = await self._call_google(messages)
                self._store(user_id, user_message, text)
                return text
            except Exception as exc:
                logger.warning(f"⚠️ فشل Google AI: {exc}")

        try:
            text = await self._call_openrouter(messages)
            self._store(user_id, user_message, text)
            return text
        except Exception as exc:
            logger.error(f"❌ فشلت جميع المحاولات: {exc}")
            return self._fallback()

    def _store(self, user_id: int, user_msg: str, ai_msg: str) -> None:
        self.memory.add_message(user_id, "user",      user_msg)
        self.memory.add_message(user_id, "assistant", ai_msg)

    def _build_messages(self, user_id: int, msg: str, context: str, mode: str, active_hadith: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
        prompt = self._PROMPTS.get(mode, self._PROMPTS["normal"])
        if context:
            prompt += f"\n\n{context}"
        # ← تحسين السياق: أخبر AI بالحديث المناقَش
        if active_hadith:
            prompt += (
                f"\n\n📌 الحديث المناقَش حالياً:\n"
                f"الرقم: {active_hadith['id']} — {active_hadith['title']}\n"
                f"الراوي: {active_hadith['narrator']}\n"
                f"النص: {active_hadith['text'][:400]}"
            )
        messages = [{"role": "system", "content": prompt}]
        messages.extend(self.memory.get(user_id))
        messages.append({"role": "user", "content": msg})
        return messages

    async def _call_google(self, messages: List[Dict[str, str]]) -> str:
        prompt = "\n\n".join(f"{m['role']}: {m['content']}" for m in messages)
        url    = f"{self.GOOGLE_URL}?key={self.google_key}"
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openrouter(self, messages: List[Dict[str, str]]) -> str:
        headers = {"Authorization": f"Bearer {self.openrouter_key}", "Content-Type": "application/json"}
        payload = {"model": self.OPENROUTER_MODEL, "messages": messages}
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(self.OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _fallback() -> str:
        return (
            "😔 أعتذر، واجهت صعوبة في معالجة طلبك حالياً.\n\n"
            "💡 *يمكنك:*\n"
            "• المحاولة مرة أخرى بعد دقائق\n"
            "• استخدام `/list` لتصفح الأحاديث\n"
            "• إرسال رقم الحديث مباشرة\n\n"
            "_سنعمل على حل المشكلة قريباً_ 🔧"
        )


# ═══════════════════════════════════════════════════════════════════
# 10. معالجات البوت (الكاملة)
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# نظام المشرف
# ═══════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    """تحقق أن المستخدم هو المشرف"""
    dev_id = os.getenv("DEVELOPER_TELEGRAM_ID", "")
    return dev_id and str(user_id) == str(dev_id)


def admin_only(func):
    """Decorator يمنع غير المشرف من تنفيذ الأمر"""
    import functools
    @functools.wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ هذا الأمر للمشرف فقط.")
            return
        return await func(self, update, context)
    return wrapper

class BotHandlers:
    """معالجات أوامر ورسائل البوت — النسخة الكاملة v3"""

    _WELCOME_TEXT = (
        "🌟 *مرحباً بك في نبراس*\n"
        "_معلّمك الذكي للأربعين النووية_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*📚 ما الذي يمكنني فعله؟*\n\n"
        "🔍 البحث والاستكشاف بالموضوعات\n"
        "💬 شرح وتفسير بالذكاء الاصطناعي\n"
        "🎓 اختبارات تفاعلية متعددة الأنواع\n"
        "🃏 بطاقات الحفظ التفاعلية\n"
        "👤 بطاقة الراوي التفصيلية\n"
        "🌍 الترجمة الإنجليزية\n"
        "🏆 نظام الشارات والإنجازات\n"
        "🔥 السلسلة اليومية والإحصائيات\n"
        "⭐ مفضلة وملاحظات شخصية\n"
        "🎯 خطة دراسية منظمة\n"
        "⏰ تذكير يومي ومسائي\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*🚀 ابدأ الآن:*\n"
        "• اضغط أي زر أدناه\n"
        "• أو أرسل رقم الحديث (1-42)\n"
        "• أو اطرح أي سؤال نصي!"
    )

    _HELP_TEXT = (
        "📖 *دليل استخدام نبراس v3*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*📚 الأحاديث:*\n"
        "/list — فهرس الأربعين حديثاً\n"
        "/random — حديث عشوائي\n"
        "/daily — حديث اليوم\n"
        "/topics — تصفح بالموضوعات\n"
        "/search كلمة — بحث في الأحاديث\n"
        "أو أرسل رقماً من 1 إلى 42 مباشرة\n\n"
        "*🎓 التعلم:*\n"
        "/quiz — اختبار تفاعلي\n"
        "/flashcard — بطاقات الحفظ\n"
        "/selftest — أعرف / لا أعرف\n"
        "/plan — خطة دراسية منظمة\n\n"
        "*📊 المتابعة:*\n"
        "/stats — إحصائياتي وشاراتي\n"
        "/badges — شاراتي والإنجازات\n"
        "/favorites — أحاديثي المفضلة\n"
        "/review — الأحاديث التي تحتاج مراجعة\n\n"
        "*⏰ التذكير:*\n"
        "/reminder — إعدادات التذكير\n"
        "/reminder on 08:00 — تفعيل صباحي\n"
        "/reminder evening 22:00 — تفعيل مسائي\n"
        "/reminder off — تعطيل\n\n"
        "*💬 أخرى:*\n"
        "/feedback — تواصل مع المطور\n"
        "/cancel — إلغاء العملية الحالية\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "*💡 نصيحة:* اطرح أي سؤال نصي\n"
        "وسأجيبك بالذكاء الاصطناعي! 🤖"
    )

    def __init__(
        self,
        hadith_db:     HadithDatabase,
        user_data_mgr: UserDataManager,
        ai_engine:     NibrasAI,
        formatter:     MessageFormatter,
    ) -> None:
        self.db        = hadith_db
        self.user_data = user_data_mgr
        self.ai        = ai_engine
        self.fmt       = formatter

    # ════════════════════════════════════════════════════════════════
    # دوال مساعدة خاصة
    # ════════════════════════════════════════════════════════════════

    def _main_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📚 الفهرس",          callback_data="list"),
                InlineKeyboardButton("🌀 عشوائي",          callback_data="random"),
            ],
            [
                InlineKeyboardButton("📅 حديث اليوم",      callback_data="daily"),
                InlineKeyboardButton("🏷️ حسب الموضوع",    callback_data="topics"),
            ],
            [
                InlineKeyboardButton("🎓 اختبار",          callback_data="quiz"),
                InlineKeyboardButton("🃏 بطاقات الحفظ",    callback_data="flashcard_start"),
            ],
            [
                InlineKeyboardButton("🤔 أعرف/لا أعرف",   callback_data="selftest_start"),
                InlineKeyboardButton("🎯 خطة دراسية",      callback_data="plan"),
            ],
            [
                InlineKeyboardButton("📊 إحصائياتي",       callback_data="stats"),
                InlineKeyboardButton("🏅 شاراتي",          callback_data="badges"),
            ],
            [
                InlineKeyboardButton("⭐ المفضلة",         callback_data="favorites"),
                InlineKeyboardButton("⏰ التذكير",         callback_data="reminder_menu"),
            ],
            [
                InlineKeyboardButton("💬 تواصل معنا",      callback_data="feedback_start"),
                SupportSystem.get_button(),
            ],
            [InlineKeyboardButton("❓ المساعدة الكاملة",   callback_data="help")],
        ])

    def _plan_choice_keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 7 أيام (6 أحاديث/يوم)",  callback_data="plan_7")],
            [InlineKeyboardButton("📅 14 يوم (3 أحاديث/يوم)", callback_data="plan_14")],
            [InlineKeyboardButton("📅 21 يوم (2 حديث/يوم)",   callback_data="plan_21")],
            [InlineKeyboardButton("📅 42 يوم (حديث/يوم)",     callback_data="plan_42")],
            [InlineKeyboardButton("🏠 الرئيسية",               callback_data="start")],
        ])

    async def _display_hadith(self, user_id: int, hadith: Dict[str, Any], status_message, prefix: str = "") -> None:
        """عرض حديث كامل مع تسجيله مقروءاً + التحقق من الشارات الجديدة"""
        self.user_data.mark_as_read(user_id, hadith["id"])
        self.ai.memory.set_active_hadith(user_id, hadith["id"])

        is_fav  = self.user_data.is_favorite(user_id, hadith["id"])
        has_note = self.user_data.get_note(user_id, hadith["id"]) is not None

        body, keyboard = self.fmt.build_hadith_display(
            hadith, include_actions=True, is_favorite=is_fav, has_note=has_note
        )
        questions_text = SmartQuestionSystem.format_message(hadith)
        final = (prefix + body + questions_text).strip()

        if len(final) > 4096:
            final = final[:4093] + "..."

        await status_message.edit_text(final, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

        # التحقق من الشارات الجديدة وإخبار المستخدم
        new_badges = self.user_data.check_and_award_badges(user_id)
        if new_badges:
            badges_text = "\n".join(
                f"{BADGES[b]['emoji']} *{BADGES[b]['name']}* — {BADGES[b]['desc']}"
                for b in new_badges if b in BADGES
            )
            await status_message.reply_text(
                f"🎉 *مبروك! حصلت على شارة جديدة!*\n\n{badges_text}",
                parse_mode=ParseMode.MARKDOWN,
            )

    async def _send_support_if_due(self, chat_id: int, bot) -> None:
        if self.user_data.should_show_support_reminder(chat_id):
            self.user_data.update_support_reminder(chat_id)
            await bot.send_message(
                chat_id=chat_id,
                text=SupportSystem.get_message(),
                reply_markup=InlineKeyboardMarkup([[SupportSystem.get_button()]]),
                parse_mode=ParseMode.MARKDOWN,
            )

    async def _handle_hadith_by_number(self, update: Update, number: str, user_id: int) -> None:
        hadith_id = int(number)
        hadith    = self.db.get_by_id(hadith_id)
        if not hadith:
            await update.message.reply_text(
                f"❌ لم أجد الحديث رقم {hadith_id}.\nالأحاديث المتوفرة: 1-{len(self.db)}"
            )
            return
        status = await update.message.reply_text("🔎 جاري البحث...")
        await self._display_hadith(user_id, hadith, status)

    async def _handle_general_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        text_input = update.message.text or ""
        if not text_input.strip():
            await update.message.reply_text("❌ لم أستطع فهم رسالتك.")
            return
        status = await update.message.reply_text("🔎 جاري التفكير...")
        # إرسال سياق الحديث المناقَش إلى AI
        active_hid    = self.ai.memory.get_active_hadith(user_id)
        active_hadith = self.db.get_by_id(active_hid) if active_hid else None
        ai_response   = await self.ai.generate_response(user_id, text_input, active_hadith=active_hadith)
        formatted     = self.fmt.format_response(ai_response)
        if len(formatted) > 4096:
            await status.edit_text(formatted[:4093] + "...", parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text(formatted[4093:], parse_mode=ParseMode.MARKDOWN)
        else:
            await status.edit_text(formatted, parse_mode=ParseMode.MARKDOWN)
        self.user_data.increment_interaction(user_id)
        await self._send_support_if_due(user_id, context.bot)

        # 📢 إعلان Monetag الدوري كل MONETAG_INTERVAL تفاعل
        interaction_count = self.user_data._load(user_id).get("interaction_count", 0)
        if MonetagSystem.should_show_interval_ad(user_id, interaction_count):
            await asyncio.sleep(2)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=user_id,
                context_label="💡 *هل تعلم؟*",
            )

    def _build_plan_text(self, user_id: int, plan: List[int]) -> str:
        read      = set(self.user_data.get_read_hadiths(user_id))
        completed = sum(1 for h in plan if h in read)
        remaining = len(plan) - completed
        pct       = round((completed / len(plan)) * 100, 1) if plan else 0
        text = (
            "🎯 *خطتك الدراسية*\n"
            "ــــــــــــــــــ\n\n"
            f"📊 التقدم: {completed}/{len(plan)} أحاديث\n"
            f"📈 النسبة: {pct}%\n"
            f"📚 المتبقي: {remaining} حديث\n\n"
        )
        if remaining > 0:
            nexts = [h for h in plan if h not in read][:3]
            text += "*📖 الأحاديث التالية:*\n"
            for hid in nexts:
                h = self.db.get_by_id(hid)
                if h:
                    text += f"• الحديث {hid}: {h['title']}\n"
        else:
            text += "🎉 *مبروك! أكملت خطتك الدراسية!*"
        return text

    # ════════════════════════════════════════════════════════════════
    # الأوامر الرئيسية
    # ════════════════════════════════════════════════════════════════

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await context.bot.set_my_commands([
                BotCommand("start",     "🏠 الرئيسية"),
                BotCommand("list",      "📚 فهرس الأحاديث"),
                BotCommand("random",    "🌀 حديث عشوائي"),
                BotCommand("daily",     "📅 حديث اليوم"),
                BotCommand("topics",    "🏷️ تصفح بالموضوعات"),
                BotCommand("search",    "🔍 بحث في الأحاديث"),
                BotCommand("quiz",      "🎓 اختبر نفسك"),
                BotCommand("flashcard", "🃏 بطاقات الحفظ"),
                BotCommand("selftest",  "🤔 أعرف/لا أعرف"),
                BotCommand("plan",      "🎯 خطة دراسية"),
                BotCommand("stats",     "📊 إحصائياتي"),
                BotCommand("badges",    "🏅 شاراتي"),
                BotCommand("favorites", "⭐ المفضلة"),
                BotCommand("review",    "📋 تحتاج مراجعة"),
                BotCommand("reminder",  "⏰ التذكير اليومي"),
                BotCommand("feedback",  "💬 تواصل معنا"),
                BotCommand("cancel",    "🚫 إلغاء"),
                BotCommand("help",      "❓ المساعدة"),
            ])
            await update.message.reply_text(
                self._WELCOME_TEXT,
                reply_markup=self._main_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
            # 🔔 إشعار المشرف عند مستخدم جديد
            user_id = update.effective_user.id
            interaction_count = self.user_data._load(user_id).get("interaction_count", 0)
            if interaction_count == 0 and DEVELOPER_TELEGRAM_ID:
                try:
                    user     = update.effective_user
                    all_users = self.user_data.get_all_users()
                    safe_name = MessageFormatter.esc(user.first_name or "مجهول")
                    uname     = f" (@{user.username})" if user.username else ""
                    await context.bot.send_message(
                        chat_id=int(DEVELOPER_TELEGRAM_ID),
                        text=(
                            "🆕 *مستخدم جديد انضم!*\n"
                            f"👤 الاسم: {safe_name}{uname}\n"
                            f"🆔 المعرف: `{user_id}`\n"
                            f"👥 إجمالي المستخدمين الآن: *{len(all_users)}*"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass

            # 📢 إعلان Monetag عند /start للمستخدمين القدامى فقط
            if interaction_count > 0:
                await asyncio.sleep(2)
                await MonetagSystem.send_ad(
                    context.bot,
                    chat_id=user_id,
                    context_label="🏠 *أهلاً بعودتك!*",
                )
        except Exception as exc:
            logger.error(f"خطأ في start: {exc}")
            await update.message.reply_text("حدث خطأ. يرجى المحاولة مرة أخرى.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 الرئيسية",       callback_data="start"),
             InlineKeyboardButton("⏰ التذكير",         callback_data="reminder_menu")],
            [SupportSystem.get_button()],
        ])
        await update.message.reply_text(self._HELP_TEXT, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if context.args:
                await self._handle_hadith_by_number(update, context.args[0], update.effective_user.id)
                return
            if not self.db:
                await update.message.reply_text("❌ قاعدة الأحاديث غير متوفرة.")
                return
            await update.message.reply_text(
                self.fmt.build_hadith_list(self.db.get_all()),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as exc:
            logger.error(f"خطأ في list: {exc}")
            await update.message.reply_text("حدث خطأ في عرض الفهرس.")

    async def random_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            hadith = self.db.get_random()
            if not hadith:
                await update.message.reply_text("❌ لا توجد أحاديث متوفرة.")
                return
            status  = await update.message.reply_text("🌀 جاري اختيار حديث...")
            user_id = update.effective_user.id
            await self._display_hadith(user_id, hadith, status)
            self.user_data.increment_interaction(user_id)
            await self._send_support_if_due(user_id, context.bot)
            # 📢 إعلان Monetag بعد الحديث العشوائي
            await asyncio.sleep(1)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=user_id,
                context_label="🌀 *استمتع بالحديث!*",
            )
        except Exception as exc:
            logger.error(f"خطأ في random: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            if not context.args:
                await update.message.reply_text(
                    "🔍 *البحث في الأحاديث*\n"
                    "ــــــــــــــــ\n\n"
                    "📝 *الاستخدام:*\n"
                    "`/search [كلمة أو أكثر]`\n\n"
                    "💡 *أمثلة:*\n"
                    "`/search النية`\n"
                    "`/search الإيمان والأعمال`\n"
                    "`/search طهور الصلاة`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            keyword = " ".join(context.args)

            # رسالة انتظار
            status = await update.message.reply_text("🔍 جاري البحث...")

            results = self.db.search(keyword)
            text    = self.fmt.build_search_results(results, keyword)

            # أزرار للنتائج الأولى (أسرع وصول)
            if results:
                buttons = []
                for h in results[:5]:
                    buttons.append([InlineKeyboardButton(
                        f"📖 {h['id']}. {h['title'][:35]}{'...' if len(h['title']) > 35 else ''}",
                        callback_data=f"hadith_{h['id']}"
                    )])
                keyboard = InlineKeyboardMarkup(buttons)
                await status.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
            else:
                await status.edit_text(text, parse_mode=ParseMode.MARKDOWN)

            # 📢 إعلان Monetag بعد نتائج البحث
            await asyncio.sleep(1)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=user_id,
                context_label="🔍 *وجدت ما تبحث عنه!*",
            )
        except Exception as exc:
            logger.error(f"خطأ في search: {exc}")
            await update.message.reply_text("حدث خطأ في البحث.")

    async def topics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """[جديد] تصفح الأحاديث حسب الموضوع"""
        try:
            if context.args:
                # عرض تصنيف محدد
                category = " ".join(context.args)
                hadiths  = self.db.get_by_category(category)
                if not hadiths:
                    await update.message.reply_text(f"❌ لم أجد أحاديث في تصنيف: {category}")
                    return
                lines = [f"🏷️ *{category}*\n"]
                for h in hadiths:
                    badge = " ✨" if h.get("hadith_type") == "qudsi" else ""
                    lines.append(f"• الحديث {h['id']}: {h['title']}{badge}")
                lines.append("\n💡 أرسل رقم الحديث لعرضه")
                await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
            else:
                cats     = self.db.get_categories()
                text, kb = self.fmt.build_categories_menu(cats)
                await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        except Exception as exc:
            logger.error(f"خطأ في topics: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            stats   = self.user_data.get_statistics(user_id, len(self.db))
            text    = self.fmt.build_statistics(stats) + SupportSystem.get_stats_footer()
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏅 شاراتي",    callback_data="badges"),
                 InlineKeyboardButton("🏠 الرئيسية", callback_data="start")],
                [SupportSystem.get_button()],
            ])
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            # 📢 إعلان Monetag بعد عرض الإحصائيات
            await asyncio.sleep(1)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=user_id,
                context_label="📊 *رائع! استمر في تقدمك*",
            )
        except Exception as exc:
            logger.error(f"خطأ في stats: {exc}")
            await update.message.reply_text("حدث خطأ في عرض الإحصائيات.")

    async def badges_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """[جديد] عرض الشارات والإنجازات"""
        try:
            user_id = update.effective_user.id
            earned  = set(self.user_data.get_earned_badges(user_id))
            stats   = self.user_data.get_statistics(user_id, len(self.db))

            lines = ["🏅 *شاراتك وإنجازاتك*\n", "ــــــــــــــــــ\n"]
            for badge_id, badge in BADGES.items():
                if badge_id in earned:
                    lines.append(f"✅ {badge['emoji']} *{badge['name']}* — {badge['desc']}")
                else:
                    lines.append(f"🔒 ░ *{badge['name']}* — {badge['desc']}")

            lines.append(f"\n📊 *مكتسب:* {len(earned)}/{len(BADGES)} شارة")
            lines.append(f"🔥 *السلسلة الحالية:* {stats['streak']} يوم")

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats"),
                 InlineKeyboardButton("🏠 الرئيسية",  callback_data="start")],
            ])
            await update.message.reply_text("\n".join(lines), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            # 📢 إعلان Monetag بعد عرض الشارات
            await asyncio.sleep(1)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=user_id,
                context_label="🏅 *أحسنت! إليك شيء قد يهمك*",
            )
        except Exception as exc:
            logger.error(f"خطأ في badges: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def favorites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id   = update.effective_user.id
            favorites = self.user_data.get_favorites(user_id)
            if not favorites:
                await update.message.reply_text(
                    "⭐ *المفضلة فارغة*\n\n"
                    "لم تقم بإضافة أي حديث للمفضلة بعد.\n"
                    "عند عرض أي حديث، اضغط ☆ لإضافته.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            lines = ["⭐ *أحاديثك المفضلة:*\n"]
            for hid in favorites:
                h = self.db.get_by_id(hid)
                if h:
                    lines.append(f"• الحديث {hid}: {h['title']}")
            lines.append("\n💡 أرسل رقم الحديث لعرضه")
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
            # 📢 إعلان Monetag بعد عرض المفضلة
            await asyncio.sleep(1)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=update.effective_user.id,
                context_label="⭐ *أحاديثك المفضلة!*",
            )
        except Exception as exc:
            logger.error(f"خطأ في favorites: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def review_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """[جديد] عرض الأحاديث التي تحتاج مراجعة"""
        try:
            user_id   = update.effective_user.id
            needs_rev = self.user_data.get_needs_review(user_id)
            if not needs_rev:
                await update.message.reply_text(
                    "📋 *لا توجد أحاديث تحتاج مراجعة*\n\n"
                    "استخدم /selftest لتقييم معرفتك بالأحاديث.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            lines = [f"📋 *أحاديث تحتاج مراجعة ({len(needs_rev)}):*\n"]
            for hid in needs_rev:
                h = self.db.get_by_id(hid)
                if h:
                    lines.append(f"• الحديث {hid}: {h['title']}")
            lines.append("\n💡 أرسل رقم الحديث لعرضه ومراجعته")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🃏 ابدأ مراجعة بطاقات", callback_data="flashcard_review")],
                [InlineKeyboardButton("🏠 الرئيسية",             callback_data="start")],
            ])
            await update.message.reply_text("\n".join(lines), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        except Exception as exc:
            logger.error(f"خطأ في review: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            today   = datetime.now().date().isoformat()
            if self.user_data.get_last_daily(user_id) == today:
                await update.message.reply_text(
                    "📅 لقد حصلت على حديث اليوم بالفعل!\nعد غداً للحصول على حديث جديد. 🌟"
                )
                return
            unread    = self.user_data.get_unread_hadiths(user_id, len(self.db))
            hadith_id = random.choice(unread) if unread else random.randint(1, len(self.db))
            hadith    = self.db.get_by_id(hadith_id)
            if hadith:
                status = await update.message.reply_text("📅 حديث اليوم...")
                self.user_data.update_last_daily(user_id)
                remaining = len(unread) - 1 if unread else 0
                prefix    = f"📅 *حديث اليوم*\n📚 تبقى لك {remaining} حديثاً للإتمام!\n\n"
                await self._display_hadith(user_id, hadith, status, prefix=prefix)
                self.user_data.increment_interaction(user_id)
                await self._send_support_if_due(user_id, context.bot)
        except Exception as exc:
            logger.error(f"خطأ في daily: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            if QuizSystem.is_active(user_id):
                await update.message.reply_text(
                    "⚠️ لديك اختبار نشط!\nأكمله أو استخدم /cancel_quiz لإلغائه."
                )
                return
            questions = QuizSystem.generate_quiz(self.db, question_count=5)
            if not questions:
                await update.message.reply_text("❌ تعذّر توليد الاختبار، حاول مرة أخرى.")
                return
            QuizSystem.start(user_id, questions)
            await self._show_quiz_question(update.message, user_id)
        except Exception as exc:
            logger.error(f"خطأ في quiz: {exc}")
            await update.message.reply_text("حدث خطأ في بدء الاختبار.")

    async def cancel_quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        if not QuizSystem.is_active(user_id):
            await update.message.reply_text("❌ ليس لديك اختبار نشط.")
            return
        QuizSystem.cancel(user_id)
        await update.message.reply_text(
            "✅ تم إلغاء الاختبار.\n\nيمكنك بدء اختبار جديد باستخدام `/quiz`",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def flashcard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """[جديد] بدء جلسة بطاقات الحفظ"""
        try:
            user_id = update.effective_user.id
            if FlashcardSystem.is_active(user_id):
                await update.message.reply_text("⚠️ لديك جلسة بطاقات نشطة.")
                return
            all_ids = [h["id"] for h in self.db.get_all()]
            FlashcardSystem.start(user_id, all_ids)
            await self._show_flashcard(update.message, user_id)
        except Exception as exc:
            logger.error(f"خطأ في flashcard: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def selftest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """[جديد] اختبار أعرف/لا أعرف"""
        try:
            user_id   = update.effective_user.id
            all_ids   = [h["id"] for h in self.db.get_all()]
            random.shuffle(all_ids)
            hadith_id = all_ids[0]
            hadith    = self.db.get_by_id(hadith_id)
            if not hadith:
                await update.message.reply_text("❌ لا توجد أحاديث.")
                return
            await self._show_selftest(update.message, hadith)
        except Exception as exc:
            logger.error(f"خطأ في selftest: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def plan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id  = update.effective_user.id
            cur_plan = self.user_data.get_study_plan(user_id)
            if not cur_plan:
                await update.message.reply_text(
                    "🎯 *إنشاء خطة دراسية*\n\nاختر المدة المناسبة:",
                    reply_markup=self._plan_choice_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await update.message.reply_text(
                    self._build_plan_text(user_id, cur_plan),
                    parse_mode=ParseMode.MARKDOWN,
                )
        except Exception as exc:
            logger.error(f"خطأ في plan: {exc}")
            await update.message.reply_text("حدث خطأ.")

    async def note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "📝 *كيفية إضافة ملاحظة:*\n"
                "استخدم: `/note [رقم_الحديث] [ملاحظتك]`\n\n"
                "*مثال:*\n`/note 1 حديث مهم جداً عن النية`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        try:
            hadith_id = int(context.args[0])
            note_text = " ".join(context.args[1:])
            user_id   = update.effective_user.id
            if self.user_data.add_note(user_id, hadith_id, note_text):
                await update.message.reply_text(f"✅ تمت إضافة ملاحظتك على الحديث رقم {hadith_id}")
            else:
                await update.message.reply_text("❌ حدث خطأ في حفظ الملاحظة")
        except ValueError:
            await update.message.reply_text("❌ رقم الحديث غير صحيح")

    async def feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        FeedbackSystem.start(user_id)
        await update.message.reply_text(
            "💬 *تواصل معنا*\n\nنسعد بسماع رأيك! 🌟\n\n"
            "• 🐛 تقرير عن مشكلة\n"
            "• 💡 اقتراح ميزة\n"
            "• 📝 ملاحظة أو رأي\n\n"
            "*📨 أرسل رسالتك الآن*\nأو `/cancel` للإلغاء",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def reminder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id  = update.effective_user.id
        settings = self.user_data.get_reminder_settings(user_id)

        if not context.args:
            status   = "🟢 مفعّل" if settings["enabled"] else "🔴 معطّل"
            evening  = settings.get("time_evening") or "غير مفعّل"
            text = (
                "⏰ *إعدادات التذكير اليومي*\n\n"
                f"*الحالة:* {status}\n"
                f"*التذكير الصباحي:* {settings['time']}\n"
                f"*التذكير المسائي:* {evening}\n"
                f"*المنطقة الزمنية:* {settings['timezone']}\n\n"
                "*📝 الاستخدام:*\n"
                "`/reminder on 08:00` — تفعيل صباحي\n"
                "`/reminder evening 22:00` — تفعيل مسائي\n"
                "`/reminder evening off` — إلغاء المسائي\n"
                "`/reminder set 20:00` — تغيير الوقت\n"
                "`/reminder off` — تعطيل الكل"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 تفعيل",  callback_data="reminder_on"),
                 InlineKeyboardButton("🔴 تعطيل", callback_data="reminder_off")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="start")],
            ])
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            return

        cmd = context.args[0].lower()
        if cmd == "on":
            time_str = context.args[1] if len(context.args) > 1 else DEFAULT_REMINDER_TIME
            if not ReminderSystem.parse_time(time_str):
                await update.message.reply_text("❌ صيغة الوقت غير صحيحة! استخدم: `HH:MM`", parse_mode=ParseMode.MARKDOWN)
                return
            self.user_data.enable_reminder(user_id, time_str)
            await update.message.reply_text(
                f"✅ *تم تفعيل التذكير الصباحي!*\n\n⏰ الساعة {time_str} يومياً",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif cmd == "evening":
            if len(context.args) < 2:
                await update.message.reply_text("⚠️ حدّد الوقت! مثال: `/reminder evening 22:00`", parse_mode=ParseMode.MARKDOWN)
                return
            if context.args[1].lower() == "off":
                self.user_data.disable_evening_reminder(user_id)
                await update.message.reply_text("🔴 *تم إلغاء التذكير المسائي*", parse_mode=ParseMode.MARKDOWN)
            else:
                time_str = context.args[1]
                if not ReminderSystem.parse_time(time_str):
                    await update.message.reply_text("❌ صيغة الوقت غير صحيحة!", parse_mode=ParseMode.MARKDOWN)
                    return
                self.user_data.enable_evening_reminder(user_id, time_str)
                await update.message.reply_text(
                    f"✅ *تم تفعيل التذكير المسائي!*\n\n🌙 الساعة {time_str} يومياً",
                    parse_mode=ParseMode.MARKDOWN,
                )
        elif cmd == "off":
            self.user_data.disable_reminder(user_id)
            await update.message.reply_text(
                "🔴 *تم تعطيل التذكير اليومي*\n\nيمكنك تفعيله مجدداً بـ `/reminder on`",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif cmd == "set":
            if len(context.args) < 2 or not ReminderSystem.parse_time(context.args[1]):
                await update.message.reply_text("⚠️ مثال: `/reminder set 09:00`", parse_mode=ParseMode.MARKDOWN)
                return
            self.user_data.enable_reminder(user_id, context.args[1])
            await update.message.reply_text(f"✅ *تم تحديث وقت التذكير إلى:* {context.args[1]}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ أمر غير معروف! استخدم `/reminder` للمساعدة", parse_mode=ParseMode.MARKDOWN)


    # ════════════════════════════════════════════════════════════════
    # أوامر المشرف — مخفية عن المستخدمين العاديين
    # ════════════════════════════════════════════════════════════════

    @admin_only
    async def admin_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (
            "🔐 *أوامر المشرف — نبراس*\n"
            "ــــــــــــــــــ\n\n"
            "📊 `/admin_stats` — إحصائيات البوت\n"
            "🏆 `/admin_top` — أنشط 10 مستخدمين\n"
            "😴 `/admin_inactive` — غير نشطين ≥7 أيام\n\n"
            "📢 `/admin_broadcast [رسالة]` — رسالة جماعية\n"
            "📣 `/admin_announce [رسالة]` — إعلان مميز\n\n"
            "🚫 `/admin_ban [id]` — حظر مستخدم\n"
            "✅ `/admin_unban [id]` — رفع الحظر\n"
            "🔍 `/admin_user [id]` — بيانات مستخدم\n"
            "📋 `/admin_export` — تصدير CSV\n\n"
            "🔧 `/admin_maintenance on/off` — وضع الصيانة\n"
            "❓ `/admin_help` — هذه القائمة\n"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        users = self.user_data.get_all_users()
        total = len(users)
        if total == 0:
            await update.message.reply_text("📊 لا يوجد مستخدمون بعد.")
            return

        active_today = active_week = banned_count = 0
        total_reads  = total_inter = reminder_on  = completed_40 = 0
        from datetime import timezone as dt_tz
        now = datetime.now(dt_tz.utc)

        for uid, data in users:
            reads = len(data.get("read_hadiths", []))
            total_reads += reads
            total_inter += data.get("interaction_count", 0)
            if data.get("banned"):           banned_count += 1
            if data.get("reminder_enabled"): reminder_on  += 1
            if reads >= 42:                  completed_40 += 1
            last = data.get("streak_last_date")
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=dt_tz.utc)
                    diff = (now.date() - last_dt.date()).days
                    if diff == 0: active_today += 1
                    if diff <= 7: active_week  += 1
                except Exception:
                    pass

        avg = round(total_reads / total, 1) if total else 0
        text = (
            "📊 *إحصائيات البوت — لوحة المشرف*\n"
            "ـــــــــــــــــــــــــ\n\n"
            f"👥 إجمالي المستخدمين: *{total}*\n"
            f"🟢 نشطون اليوم: *{active_today}*\n"
            f"📅 نشطون هذا الأسبوع: *{active_week}*\n"
            f"⛔ محظورون: *{banned_count}*\n\n"
            f"📖 إجمالي القراءات: *{total_reads}*\n"
            f"💬 إجمالي التفاعلات: *{total_inter}*\n"
            f"🎓 أتمّوا الأربعين: *{completed_40}*\n"
            f"⏰ مفعّلو التذكير: *{reminder_on}*\n\n"
            f"📈 معدل القراءة/مستخدم: *{avg}*\n"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    @admin_only
    async def admin_broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text(
                "📢 *الرسالة الجماعية*\n\n"
                "الاستخدام:\n`/admin_broadcast رسالتك هنا`\n\n"
                "⚠️ ستُرسل لجميع المستخدمين.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        message_text = " ".join(context.args)
        users  = self.user_data.get_all_users()
        total  = len(users)
        status = await update.message.reply_text(f"📤 جاري الإرسال لـ {total} مستخدم...")

        sent = failed = blocked = 0
        for uid, data in users:
            if data.get("banned"):
                continue
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=(
                        "📢 *رسالة من فريق نبراس*\n"
                        "ـــــ\n\n"
                        f"{MessageFormatter.esc(message_text)}"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                err = str(e).lower()
                if "blocked" in err or "forbidden" in err:
                    blocked += 1
                else:
                    failed += 1

        await status.edit_text(
            f"✅ *اكتمل الإرسال*\n\n"
            f"📨 أُرسلت: {sent}\n"
            f"🚫 حجبوا البوت: {blocked}\n"
            f"❌ فشل: {failed}\n"
            f"📊 الإجمالي: {total}",
            parse_mode=ParseMode.MARKDOWN,
        )

    @admin_only
    async def admin_ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "🚫 *حظر مستخدم*\n\nالاستخدام:\n`/admin_ban 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        uid = int(context.args[0])
        if is_admin(uid):
            await update.message.reply_text("⛔ لا يمكن حظر المشرف.")
            return
        self.user_data.ban_user(uid)
        await update.message.reply_text(
            f"✅ تم حظر المستخدم `{uid}` بنجاح.",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            await context.bot.send_message(chat_id=uid, text="⛔ تم حظرك من استخدام هذا البوت.")
        except Exception:
            pass

    @admin_only
    async def admin_unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "✅ *رفع الحظر*\n\nالاستخدام:\n`/admin_unban 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        uid = int(context.args[0])
        self.user_data.unban_user(uid)
        await update.message.reply_text(
            f"✅ تم رفع الحظر عن المستخدم `{uid}`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            await context.bot.send_message(
                chat_id=uid,
                text="✅ تم رفع الحظر عنك، يمكنك استخدام البوت مجدداً.",
            )
        except Exception:
            pass

    @admin_only
    async def admin_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "🔍 *بيانات مستخدم*\n\nالاستخدام:\n`/admin_user 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        uid    = int(context.args[0])
        data   = self.user_data._load(uid)
        reads  = len(data.get("read_hadiths", []))
        inter  = data.get("interaction_count", 0)
        streak = data.get("streak_count", 0)
        badges = data.get("badges", [])
        banned = data.get("banned", False)
        rem    = data.get("reminder_enabled", False)
        tz     = data.get("reminder_timezone", "—")
        badges_str = " ".join(BADGES[b]["emoji"] for b in badges if b in BADGES) or "لا توجد"
        text = (
            f"🔍 *بيانات المستخدم* `{uid}`\n"
            "ــــــــ\n\n"
            f"📖 أحاديث مقروءة: {reads}/42\n"
            f"💬 تفاعلات: {inter}\n"
            f"🔥 السلسلة: {streak} يوم\n"
            f"🏅 شارات: {badges_str}\n"
            f"⏰ تذكير: {'✅' if rem else '❌'} ({tz})\n"
            f"⛔ محظور: {'نعم' if banned else 'لا'}\n"
        )
        label = "✅ رفع الحظر" if banned else "🚫 حظر"
        cb    = f"admin_unban_{uid}" if banned else f"admin_ban_{uid}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=cb)]])
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    @admin_only
    async def admin_export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        import csv, io
        users = self.user_data.get_all_users()
        if not users:
            await update.message.reply_text("📋 لا يوجد بيانات للتصدير.")
            return
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "read_hadiths", "interaction_count",
                         "streak_count", "badges", "reminder_enabled", "banned"])
        for uid, data in users:
            writer.writerow([
                uid,
                len(data.get("read_hadiths", [])),
                data.get("interaction_count", 0),
                data.get("streak_count", 0),
                len(data.get("badges", [])),
                data.get("reminder_enabled", False),
                data.get("banned", False),
            ])
        output.seek(0)
        csv_bytes = output.getvalue().encode("utf-8-sig")
        await update.message.reply_document(
            document=csv_bytes,
            filename="nibras_users.csv",
            caption=f"📋 *بيانات {len(users)} مستخدم*",
            parse_mode=ParseMode.MARKDOWN,
        )


    @admin_only
    async def admin_top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """📈 /admin_top — أكثر 10 مستخدمين نشاطاً"""
        users = self.user_data.get_all_users()
        if not users:
            await update.message.reply_text("لا يوجد مستخدمون بعد.")
            return
        # ترتيب حسب القراءات ثم التفاعلات
        ranked = sorted(
            users,
            key=lambda x: (
                len(x[1].get("read_hadiths", [])),
                x[1].get("interaction_count", 0)
            ),
            reverse=True
        )[:10]

        lines = ["🏆 *أكثر 10 مستخدمين نشاطاً*\n" "ـــــــــــــــ\n"]
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        for i, (uid, data) in enumerate(ranked):
            reads  = len(data.get("read_hadiths", []))
            inter  = data.get("interaction_count", 0)
            streak = data.get("streak_count", 0)
            lines.append(
                f"{medals[i]} `{uid}`\n"
                f"   📖 {reads}/42 قراءة  •  💬 {inter} تفاعل  •  🔥 {streak}د"
            )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    @admin_only
    async def admin_inactive_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """😴 /admin_inactive — مستخدمون غير نشطين منذ أسبوع"""
        from datetime import timezone as dt_tz
        now   = datetime.now(dt_tz.utc)
        users = self.user_data.get_all_users()
        inactive = []
        for uid, data in users:
            if data.get("banned"):
                continue
            last = data.get("streak_last_date")
            if not last:
                # لم يتفاعل أبداً بعد التسجيل
                inactive.append((uid, data, 999))
                continue
            try:
                last_dt = datetime.fromisoformat(last)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=dt_tz.utc)
                days = (now.date() - last_dt.date()).days
                if days >= 7:
                    inactive.append((uid, data, days))
            except Exception:
                pass

        inactive.sort(key=lambda x: x[2], reverse=True)
        total = len(inactive)

        if total == 0:
            await update.message.reply_text("✅ لا يوجد مستخدمون غير نشطين منذ أسبوع!")
            return

        lines = [
            f"😴 *المستخدمون غير النشطين (≥7 أيام)*\n"
            f"العدد: {total} مستخدم\nـــــــ\n"
        ]
        for uid, data, days in inactive[:15]:
            reads = len(data.get("read_hadiths", []))
            day_str = "لم يتفاعل أبداً" if days == 999 else f"منذ {days} يوم"
            lines.append(f"• `{uid}` — {day_str} — {reads}/42 قراءة")

        if total > 15:
            lines.append(f"\n_...و {total-15} آخرون_")

        lines.append(
            f"\n💡 يمكنك استخدام `/admin_broadcast` لإرسال رسالة تشجيعية لهم."
        )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    @admin_only
    async def admin_announce_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """📣 /admin_announce [رسالة] — إعلان مميز بتنسيق خاص"""
        if not context.args:
            await update.message.reply_text(
                "📣 *الإعلان المميز*\n\n"
                "الاستخدام:\n`/admin_announce نص الإعلان`\n\n"
                "يُرسل بتنسيق مميز يختلف عن broadcast العادي.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        msg_text = " ".join(context.args)
        users    = self.user_data.get_all_users()
        total    = len(users)
        status   = await update.message.reply_text(f"📣 جاري إرسال الإعلان لـ {total} مستخدم...")

        announce_text = (
            "╔══════════════════╗\n"
            "║  📣 *إعلان نبراس*  ║\n"
            "╚══════════════════╝\n\n"
            f"{MessageFormatter.esc(msg_text)}\n\n"
            "─────────────────\n"
            "🌿 _فريق نبراس — الأربعون النووية_"
        )

        sent = failed = blocked = 0
        for uid, data in users:
            if data.get("banned"):
                continue
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=announce_text,
                    parse_mode=ParseMode.MARKDOWN,
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                err = str(e).lower()
                if "blocked" in err or "forbidden" in err:
                    blocked += 1
                else:
                    failed += 1

        await status.edit_text(
            f"✅ *اكتمل الإعلان*\n\n"
            f"📨 أُرسل لـ: {sent}\n"
            f"🚫 حجبوا البوت: {blocked}\n"
            f"❌ فشل: {failed}",
            parse_mode=ParseMode.MARKDOWN,
        )

    @admin_only
    async def admin_maintenance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """🔧 /admin_maintenance [on/off] [رسالة] — تفعيل/إيقاف وضع الصيانة"""
        global _maintenance_mode, _maintenance_message

        if not context.args:
            status_text = "مفعّل ✅" if _maintenance_mode else "معطّل ❌"
            await update.message.reply_text(
                f"🔧 *وضع الصيانة الحالي:* {status_text}\n\n"
                "الاستخدام:\n"
                "`/admin_maintenance on` — تفعيل\n"
                "`/admin_maintenance off` — إيقاف\n"
                "`/admin_maintenance on جاري التحديث...` — مع رسالة مخصصة",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        action = context.args[0].lower()
        custom_msg = " ".join(context.args[1:]) if len(context.args) > 1 else ""

        if action == "on":
            _maintenance_mode = True
            if custom_msg:
                _maintenance_message = f"🔧 {custom_msg}"
            else:
                _maintenance_message = "🔧 البوت في وضع الصيانة حالياً، يرجى المحاولة لاحقاً."
            await update.message.reply_text(
                f"🔧 *وضع الصيانة مفعَّل*\n\n"
                f"📝 الرسالة: _{MessageFormatter.esc(_maintenance_message)}_\n\n"
                "المستخدمون سيحصلون على هذه الرسالة حتى تُوقف الصيانة.",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif action == "off":
            _maintenance_mode = False
            await update.message.reply_text("✅ *وضع الصيانة أُوقف* — البوت يعمل بشكل طبيعي الآن.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ استخدم `on` أو `off`.", parse_mode=ParseMode.MARKDOWN)


    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        if QuizSystem.is_active(user_id):
            QuizSystem.cancel(user_id)
            await update.message.reply_text("✅ تم إلغاء الاختبار.")
            return
        if FlashcardSystem.is_active(user_id):
            FlashcardSystem.cancel(user_id)
            await update.message.reply_text("✅ تم إلغاء جلسة البطاقات.")
            return
        if FeedbackSystem.is_active(user_id):
            FeedbackSystem.stop(user_id)
            await update.message.reply_text("✅ تم إلغاء إرسال الملاحظة.")
            return
        if NoteSystem.is_active(user_id):
            NoteSystem.stop(user_id)
            await update.message.reply_text("✅ تم إلغاء إضافة الملاحظة.")
            return
        await update.message.reply_text("لا توجد عملية نشطة للإلغاء.")

    # ════════════════════════════════════════════════════════════════
    # معالج الرسائل
    # ════════════════════════════════════════════════════════════════

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            msg     = update.message
            user_id = update.effective_user.id

            # رد المشرف على مستخدم من feedback
            if is_admin(user_id) and context.user_data.get("reply_to_user"):
                target_uid = context.user_data.pop("reply_to_user")
                reply_text = msg.text.strip()
                try:
                    await context.bot.send_message(
                        chat_id=target_uid,
                        text=(
                            "📩 *رد من فريق نبراس*\n"
                            "ـــــ\n\n"
                            f"{MessageFormatter.esc(reply_text)}"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    await msg.reply_text(f"✅ تم إرسال ردك للمستخدم `{target_uid}`.", parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    await msg.reply_text(f"❌ فشل الإرسال: {e}")
                return

            # فحص وضع الصيانة
            global _maintenance_mode, _maintenance_message
            if _maintenance_mode and not is_admin(user_id):
                await msg.reply_text(_maintenance_message)
                return

            # فحص الحظر
            if self.user_data.is_banned(user_id):
                await msg.reply_text("⛔ تم حظرك من استخدام هذا البوت.")
                return

            if msg.voice:
                await msg.reply_text("❌ لا أقبل الرسائل الصوتية.\nيمكنك إرسال رقم الحديث أو سؤال نصي.")
                return
            if msg.photo or msg.document or msg.video or msg.sticker:
                await msg.reply_text("❌ أنا متخصص في الرسائل النصية فقط.")
                return
            if not msg.text:
                return

            text = msg.text.strip()

            if FeedbackSystem.is_active(user_id):
                await self._handle_feedback_message(update, context)
                return
            if NoteSystem.is_active(user_id):
                await self._handle_note_input(update, user_id)
                return
            if QuizSystem.is_active(user_id):
                await msg.reply_text(
                    "🎓 يرجى الإجابة باستخدام الأزرار.\nلإلغاء: `/cancel_quiz`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            if text.isdigit():
                await self._handle_hadith_by_number(update, text, user_id)
                return

            await self._handle_general_query(update, context, user_id)

        except Exception as exc:
            logger.error(f"خطأ في message_handler: {exc}", exc_info=True)
            await update.message.reply_text("حدث خطأ في معالجة رسالتك.")

    # ════════════════════════════════════════════════════════════════
    # معالج الأزرار
    # ════════════════════════════════════════════════════════════════

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query   = update.callback_query
        await query.answer()
        data    = query.data
        user_id = update.effective_user.id

        try:
            # ── الحديث ──────────────────────────────────────────────
            if data.startswith("fav_"):
                await self._cb_favorite(query, user_id, int(data.split("_")[1]))

            elif data.startswith("note_"):
                await self._cb_note(query, user_id, int(data.split("_")[1]))

            elif data.startswith("admin_reply_"):
                # رد المشرف مباشرة على مستخدم من feedback
                if is_admin(user_id):
                    target_uid = int(data.split("_")[2])
                    context.user_data["reply_to_user"] = target_uid
                    await query.message.reply_text(
                        f"↩️ *اكتب ردك على المستخدم* `{target_uid}`:\n"
                        "_أرسل رسالتك الآن وستصل إليه مباشرة._\n"
                        "لإلغاء: /cancel",
                        parse_mode=ParseMode.MARKDOWN,
                    )

            elif data.startswith("admin_ban_"):
                uid = int(data.split("_")[2])
                if is_admin(user_id):
                    self.user_data.ban_user(uid)
                    await query.answer(f"✅ تم حظر {uid}", show_alert=True)
                    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ رفع الحظر", callback_data=f"admin_unban_{uid}")
                    ]]))

            elif data.startswith("admin_unban_"):
                uid = int(data.split("_")[2])
                if is_admin(user_id):
                    self.user_data.unban_user(uid)
                    await query.answer(f"✅ رُفع الحظر عن {uid}", show_alert=True)
                    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🚫 حظر", callback_data=f"admin_ban_{uid}")
                    ]]))

            elif data.startswith("hadith_"):
                # فتح حديث مباشرة من نتائج البحث
                hid    = int(data.split("_")[1])
                hadith = self.db.get_by_id(hid)
                if hadith:
                    await self._display_hadith(user_id, hadith, query.message)
                else:
                    await query.answer("❌ الحديث غير موجود", show_alert=True)

            elif data.startswith("related_"):
                await self._cb_related(query, user_id, int(data.split("_")[1]))

            elif data.startswith("simple_"):
                await self._cb_simple(query, user_id, int(data.split("_")[1]))

            elif data.startswith("compare_"):
                await self._cb_compare(query, user_id, int(data.split("_")[1]))

            elif data.startswith("narrator_"):
                await self._cb_narrator(query, int(data.split("_")[1]))

            elif data.startswith("english_"):
                await self._cb_english(query, int(data.split("_")[1]))

            elif data.startswith("share_"):
                await self._cb_share(query, int(data.split("_")[1]))

            # ── اختبار ───────────────────────────────────────────────
            elif data.startswith("quiz_answer_"):
                await self._cb_quiz_answer(query, user_id, int(data.split("_")[2]))

            # ── بطاقات الحفظ ─────────────────────────────────────────
            elif data == "flashcard_start":
                all_ids = [h["id"] for h in self.db.get_all()]
                FlashcardSystem.start(user_id, all_ids)
                await query.message.edit_text("🃏 جلسة بطاقات الحفظ بدأت...")
                await self._show_flashcard(query.message, user_id)

            elif data == "flashcard_review":
                review_ids = self.user_data.get_needs_review(user_id)
                if not review_ids:
                    await query.answer("📋 لا توجد أحاديث للمراجعة!", show_alert=True)
                    return
                FlashcardSystem.start(user_id, review_ids)
                await query.message.edit_text("🃏 جلسة مراجعة بدأت...")
                await self._show_flashcard(query.message, user_id)

            elif data.startswith("fc_reveal_"):
                hid    = int(data.split("_")[2])
                hadith = self.db.get_by_id(hid)
                if hadith:
                    text, kb = self.fmt.build_flashcard(hadith, show_answer=True)
                    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

            elif data.startswith("fc_know_"):
                hid = int(data.split("_")[2])
                self.user_data.save_self_assessment(user_id, hid, True)
                self.user_data.increment_flashcard(user_id)
                done = FlashcardSystem.advance(user_id, knew_it=True)
                if done:
                    await self._finish_flashcard(query.message, user_id)
                else:
                    await self._show_flashcard(query.message, user_id)

            elif data.startswith("fc_dontknow_"):
                hid = int(data.split("_")[2])
                self.user_data.save_self_assessment(user_id, hid, False)
                self.user_data.increment_flashcard(user_id)
                done = FlashcardSystem.advance(user_id, knew_it=False)
                if done:
                    await self._finish_flashcard(query.message, user_id)
                else:
                    await self._show_flashcard(query.message, user_id)

            elif data.startswith("fc_skip_"):
                done = FlashcardSystem.advance(user_id, knew_it=False)
                if done:
                    await self._finish_flashcard(query.message, user_id)
                else:
                    await self._show_flashcard(query.message, user_id)

            elif data == "fc_end":
                await self._finish_flashcard(query.message, user_id)

            # ── اختبار أعرف/لا أعرف ──────────────────────────────────
            elif data == "selftest_start":
                all_ids = [h["id"] for h in self.db.get_all()]
                random.shuffle(all_ids)
                hadith = self.db.get_by_id(all_ids[0])
                if hadith:
                    await query.message.edit_text("🤔 جلسة التقييم الذاتي...")
                    await self._show_selftest(query.message, hadith)

            # selftest_{hid} — زر "🤔 أعرف؟" من داخل صفحة الحديث
            elif data.startswith("selftest_") and data.count("_") == 1:
                hid    = int(data.split("_")[1])
                hadith = self.db.get_by_id(hid)
                if hadith:
                    await self._show_selftest(query.message, hadith)

            # selftest_know_{hid} — ضغط "✅ أعرفه"
            elif data.startswith("selftest_know_"):
                hid  = int(data.split("_")[2])
                self.user_data.save_self_assessment(user_id, hid, True)
                await query.answer("✅ سجّلت أنك تعرفه!")
                all_ids = [h["id"] for h in self.db.get_all()]
                random.shuffle(all_ids)
                next_hadith = self.db.get_by_id(all_ids[0])
                if next_hadith:
                    await self._show_selftest(query.message, next_hadith)

            # selftest_dontknow_{hid} — ضغط "❓ لا أتذكره"
            elif data.startswith("selftest_dontknow_"):
                hid  = int(data.split("_")[2])
                self.user_data.save_self_assessment(user_id, hid, False)
                await query.answer("📋 سجّلت للمراجعة لاحقاً")
                all_ids = [h["id"] for h in self.db.get_all()]
                random.shuffle(all_ids)
                next_hadith = self.db.get_by_id(all_ids[0])
                if next_hadith:
                    await self._show_selftest(query.message, next_hadith)

            elif data.startswith("st_explain_"):
                hid    = int(data.split("_")[2])
                hadith = self.db.get_by_id(hid)
                if hadith:
                    status   = await query.message.reply_text("💬 جاري تحضير الشرح...")
                    prompt   = f"اشرح الحديث التالي بطريقة بسيطة:\n\n{hadith['text']}"
                    response = await self.ai.generate_response(user_id, prompt, mode="simple", active_hadith=hadith)
                    kb = InlineKeyboardMarkup([[SupportSystem.get_button()]])
                    await status.edit_text(
                        f"💬 *شرح — الحديث {hid}*\n\n{self.fmt.format_response(response)}",
                        reply_markup=kb,
                        parse_mode=ParseMode.MARKDOWN,
                    )

            # view_{hid} — زر "📖 عرض كامل" من التقييم الذاتي
            elif data.startswith("view_"):
                hid    = int(data.split("_")[1])
                hadith = self.db.get_by_id(hid)
                if not hadith:
                    await query.answer("❌ الحديث غير موجود", show_alert=True)
                    return
                status = await query.message.reply_text("🔎 جاري العرض...")
                await self._display_hadith(user_id, hadith, status)

            # flashcard_{hid} — زر "🃏 بطاقة حفظ" من داخل صفحة الحديث
            elif data.startswith("flashcard_"):
                try:
                    hid = int(data.split("_")[1])
                    FlashcardSystem.start(user_id, [hid])
                    await self._show_flashcard(query.message, user_id)
                except (ValueError, IndexError):
                    await query.answer("❌ حدث خطأ", show_alert=True)

            # ── الخطة الدراسية ────────────────────────────────────────
            elif data.startswith("plan_"):
                await self._cb_plan(query, user_id, data)

            # ── التواصل ───────────────────────────────────────────────
            elif data == "feedback_start":
                FeedbackSystem.start(user_id)
                await query.message.reply_text(
                    "💬 *تواصل معنا*\n\nأرسل رسالتك الآن أو `/cancel` للإلغاء.",
                    parse_mode=ParseMode.MARKDOWN,
                )

            # ── التذكير ───────────────────────────────────────────────
            elif data == "reminder_menu":
                await self._cb_reminder_menu(query, user_id)

            elif data == "reminder_on":
                self.user_data.enable_reminder(user_id, DEFAULT_REMINDER_TIME)
                await query.message.edit_text(
                    f"✅ *تم تفعيل التذكير!*\n\n⏰ الوقت: {DEFAULT_REMINDER_TIME}\n\n"
                    "لتغيير الوقت: `/reminder set HH:MM`",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ إعدادات",    callback_data="reminder_menu")],
                        [InlineKeyboardButton("🏠 الرئيسية",  callback_data="start")],
                    ]),
                    parse_mode=ParseMode.MARKDOWN,
                )

            elif data == "reminder_off":
                self.user_data.disable_reminder(user_id)
                await query.message.edit_text(
                    "🔴 *تم تعطيل التذكير اليومي*",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🟢 تفعيل مجدداً", callback_data="reminder_on")],
                        [InlineKeyboardButton("🏠 الرئيسية",     callback_data="start")],
                    ]),
                    parse_mode=ParseMode.MARKDOWN,
                )

            # ── القوائم العامة ────────────────────────────────────────
            elif data == "start":
                await query.message.edit_text(
                    self._WELCOME_TEXT, reply_markup=self._main_keyboard(), parse_mode=ParseMode.MARKDOWN
                )

            elif data == "help":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 الرئيسية",  callback_data="start"),
                     InlineKeyboardButton("⏰ التذكير",   callback_data="reminder_menu")],
                    [SupportSystem.get_button()],
                ])
                await query.message.edit_text(self._HELP_TEXT, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

            elif data == "list":
                hadiths  = self.db.get_all()
                text     = self.fmt.build_hadith_list(hadiths)
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="start")]])
                if len(text) <= 4096:
                    await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
                else:
                    await query.message.edit_text("📚 *الفهرس:*\n_(يُرسل في أجزاء)_", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
                    for i in range(0, len(text), 4000):
                        await query.message.reply_text(text[i:i+4000], parse_mode=ParseMode.MARKDOWN)

            elif data == "random":
                hadith = self.db.get_random()
                if not hadith:
                    await query.answer("❌ لا توجد أحاديث", show_alert=True)
                    return
                await query.message.edit_text("🌀 جاري اختيار حديث...")
                await self._display_hadith(user_id, hadith, query.message)
                self.user_data.increment_interaction(user_id)
                await self._send_support_if_due(user_id, context.bot)

            elif data == "daily":
                await self._cb_daily(query, user_id, context)

            elif data == "quiz":
                await self._cb_quiz_start(query, user_id)

            elif data == "topics":
                cats     = self.db.get_categories()
                text, kb = self.fmt.build_categories_menu(cats)
                await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

            elif data.startswith("cat_"):
                category = data[4:]  # إزالة "cat_"
                await self._cb_category(query, category)

            elif data == "stats":
                stats = self.user_data.get_statistics(user_id, len(self.db))
                text  = self.fmt.build_statistics(stats) + SupportSystem.get_stats_footer()
                await query.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏅 شاراتي",    callback_data="badges"),
                         InlineKeyboardButton("🏠 الرئيسية",  callback_data="start")],
                        [SupportSystem.get_button()],
                    ]),
                    parse_mode=ParseMode.MARKDOWN,
                )

            elif data == "badges":
                earned = set(self.user_data.get_earned_badges(user_id))
                stats  = self.user_data.get_statistics(user_id, len(self.db))
                lines  = ["🏅 *شاراتك وإنجازاتك*\n", "ــــــــــــ\n"]
                for bid, badge in BADGES.items():
                    icon = "✅" if bid in earned else "🔒"
                    lines.append(f"{icon} {badge['emoji']} *{badge['name']}* — {badge['desc']}")
                lines.append(f"\n📊 {len(earned)}/{len(BADGES)} شارة | 🔥 {stats['streak']} يوم")
                await query.message.edit_text(
                    "\n".join(lines),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
                         InlineKeyboardButton("🏠 الرئيسية",  callback_data="start")],
                    ]),
                    parse_mode=ParseMode.MARKDOWN,
                )

            elif data == "favorites":
                await self._cb_favorites(query, user_id)

            elif data == "plan":
                await self._cb_plan_menu(query, user_id)

        except Exception as exc:
            logger.error(f"خطأ في button_handler [{data}]: {exc}", exc_info=True)
            try:
                await query.message.reply_text("حدث خطأ. يرجى المحاولة مرة أخرى.")
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    # معالجات الأزرار التفصيلية (private)
    # ════════════════════════════════════════════════════════════════

    async def _cb_favorite(self, query, user_id: int, hadith_id: int) -> None:
        if self.user_data.is_favorite(user_id, hadith_id):
            self.user_data.remove_favorite(user_id, hadith_id)
            await query.answer("☆ تمت الإزالة من المفضلة")
        else:
            self.user_data.add_favorite(user_id, hadith_id)
            await query.answer("⭐ تمت الإضافة للمفضلة")
        is_fav  = self.user_data.is_favorite(user_id, hadith_id)
        has_note = self.user_data.get_note(user_id, hadith_id) is not None
        _, new_kb = self.fmt.build_hadith_display(
            self.db.get_by_id(hadith_id), include_actions=True, is_favorite=is_fav, has_note=has_note
        )
        try:
            await query.message.edit_reply_markup(reply_markup=new_kb)
        except Exception:
            pass
        # تحقق من شارات جديدة
        new_badges = self.user_data.check_and_award_badges(user_id)
        if new_badges:
            for b in new_badges:
                if b in BADGES:
                    await query.message.reply_text(
                        f"🎉 *شارة جديدة!*\n{BADGES[b]['emoji']} *{BADGES[b]['name']}*",
                        parse_mode=ParseMode.MARKDOWN,
                    )

    async def _cb_note(self, query, user_id: int, hadith_id: int) -> None:
        current_note = self.user_data.get_note(user_id, hadith_id)
        NoteSystem.start(user_id, hadith_id)
        if current_note:
            text = (
                f"📝 *ملاحظتك الحالية على الحديث {hadith_id}:*\n\n"
                f"{MessageFormatter.esc(current_note)}\n\n"
                "✏️ *أرسل النص الجديد لتحديثها*\nأو `/cancel` للإلغاء"
            )
        else:
            text = (
                f"📝 *إضافة ملاحظة على الحديث {hadith_id}*\n\n"
                "✏️ *أرسل ملاحظتك الآن*\nأو `/cancel` للإلغاء"
            )
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def _handle_note_input(self, update: Update, user_id: int) -> None:
        hadith_id = NoteSystem.get_hadith_id(user_id)
        NoteSystem.stop(user_id)
        note_text = update.message.text.strip()
        if not note_text:
            await update.message.reply_text("❌ الملاحظة فارغة.")
            return
        if self.user_data.add_note(user_id, hadith_id, note_text):
            await update.message.reply_text(
                f"✅ *تم حفظ ملاحظتك على الحديث {hadith_id}!*\n\n{MessageFormatter.esc(note_text)}",
                parse_mode=ParseMode.MARKDOWN,
            )
            # 📢 إعلان Monetag بعد حفظ الملاحظة
            await asyncio.sleep(1)
            await MonetagSystem.send_ad(
                update.get_bot(),
                chat_id=user_id,
                context_label="📝 *تم حفظ ملاحظتك!*",
            )
            # تحقق من شارة الكاتب
            new_badges = self.user_data.check_and_award_badges(user_id)
            if new_badges and "writer" in new_badges:
                await update.message.reply_text(
                    f"🎉 *شارة جديدة!*\n📝 *الكاتب* — كتبت 10 ملاحظات!",
                    parse_mode=ParseMode.MARKDOWN,
                )
        else:
            await update.message.reply_text("❌ حدث خطأ في حفظ الملاحظة.")

    async def _cb_related(self, query, user_id: int, hadith_id: int) -> None:
        related = self.db.get_related(hadith_id, limit=4)
        if not related:
            await query.message.reply_text("لم أجد أحاديث مرتبطة.")
            return
        lines = ["🔗 *الأحاديث المرتبطة:*\n"]
        lines.extend(f"• الحديث {h['id']}: {h['title']}" for h in related)
        lines.append("\n💡 أرسل رقم الحديث لعرضه")
        keyboard = InlineKeyboardMarkup([[SupportSystem.get_button()]])
        await query.message.reply_text("\n".join(lines), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    async def _cb_narrator(self, query, hadith_id: int) -> None:
        """عرض بطاقة الراوي"""
        hadith = self.db.get_by_id(hadith_id)
        if not hadith:
            await query.answer("❌ الحديث غير موجود")
            return
        narrator_full = hadith.get("narrator_full", {})
        keyboard = InlineKeyboardMarkup([[SupportSystem.get_button()]])
        if not narrator_full:
            await query.message.reply_text(
                f"👤 *الراوي:* {MessageFormatter.esc(hadith['narrator'])}",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        card = self.fmt.build_narrator_card(narrator_full)
        await query.message.reply_text(card, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    async def _cb_english(self, query, hadith_id: int) -> None:
        """عرض الترجمة الإنجليزية"""
        hadith = self.db.get_by_id(hadith_id)
        if not hadith:
            await query.answer("❌ الحديث غير موجود")
            return
        if not hadith.get("english_text"):
            await query.answer("⚠️ الترجمة غير متوفرة لهذا الحديث", show_alert=True)
            return
        text = self.fmt.build_english_display(hadith)
        keyboard = InlineKeyboardMarkup([[SupportSystem.get_button()]])
        await query.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    async def _cb_share(self, query, hadith_id: int) -> None:
        """مشاركة الحديث بصيغة جاهزة"""
        hadith = self.db.get_by_id(hadith_id)
        if not hadith:
            await query.answer("❌ الحديث غير موجود")
            return
        text = self.fmt.build_share_text(hadith)
        keyboard = InlineKeyboardMarkup([[SupportSystem.get_button()]])
        await query.message.reply_text(text, reply_markup=keyboard)

    async def _cb_simple(self, query, user_id: int, hadith_id: int) -> None:
        hadith = self.db.get_by_id(hadith_id)
        if not hadith:
            return
        status   = await query.message.reply_text("💬 جاري تحضير الشرح المبسط...")
        prompt   = f"اشرح الحديث التالي بطريقة بسيطة للأطفال والمبتدئين:\n\n{hadith['text']}"
        response = await self.ai.generate_response(user_id, prompt, mode="simple", active_hadith=hadith)
        keyboard = InlineKeyboardMarkup([[SupportSystem.get_button()]])
        await status.edit_text(
            f"💬 *شرح مبسط — الحديث {hadith_id}*\n\n{self.fmt.format_response(response)}",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _cb_compare(self, query, user_id: int, hadith_id: int) -> None:
        hadith = self.db.get_by_id(hadith_id)
        if not hadith:
            await query.answer("❌ الحديث غير موجود")
            return
        try:
            status   = await query.message.reply_text("📖 جاري تحضير الشروحات...")
            prompt   = f"قدم شرحاً مقارناً متعمقاً للحديث التالي:\n\n{hadith['text']}"
            response = await self.ai.generate_response(user_id, prompt, mode="compare", active_hadith=hadith)
            formatted = self.fmt.format_response(response)
            full      = f"📖 *شرح متعمق — الحديث {hadith_id}*\n\n{formatted}"
            keyboard  = InlineKeyboardMarkup([[SupportSystem.get_button()]])
            if len(full) > 4096:
                await status.edit_text(full[:4093] + "...", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
                await query.message.reply_text("..." + full[4093:], parse_mode=ParseMode.MARKDOWN)
            else:
                await status.edit_text(full, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        except Exception as exc:
            logger.error(f"خطأ في _cb_compare: {exc}")
            await query.answer("❌ حدث خطأ")

    async def _cb_category(self, query, category: str) -> None:
        """[جديد] عرض أحاديث التصنيف"""
        # ننظر عبر كل التصنيفات بما يبدأ بالنص المقصوص
        cats = self.db.get_categories()
        # جرّب المطابقة التامة أولاً
        hadiths = self.db.get_by_category(category)
        if not hadiths:
            # إذا قُصّ المفتاح، ابحث بالبادئة
            for cat_name, ids in cats.items():
                if cat_name.startswith(category):
                    hadiths = [self.db.get_by_id(i) for i in ids]
                    hadiths = [h for h in hadiths if h]
                    category = cat_name
                    break
        if not hadiths:
            await query.answer("❌ لم أجد أحاديث في هذا التصنيف", show_alert=True)
            return
        lines = [f"🏷️ *{category}*\n"]
        for h in hadiths:
            badge = " ✨" if h.get("hadith_type") == "qudsi" else ""
            lines.append(f"• الحديث {h['id']}: {h['title']}{badge}")
        lines.append("\n💡 أرسل رقم الحديث لعرضه")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ التصنيفات",  callback_data="topics"),
             InlineKeyboardButton("🏠 الرئيسية",   callback_data="start")],
            [SupportSystem.get_button()],
        ])
        await query.message.edit_text("\n".join(lines), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── الاختبار ──────────────────────────────────────────────────

    async def _show_quiz_question(self, message, user_id: int) -> None:
        question = QuizSystem.get_current_question(user_id)
        if not question:
            await self._finish_quiz(message, user_id, is_callback=False)
            return
        quiz    = QuizSystem.active_quizzes[user_id]
        current = quiz["current_index"] + 1
        total   = len(quiz["questions"])
        emoji   = QuizSystem._TYPE_EMOJI.get(question["type"], "❓")
        text    = f"{emoji} *سؤال {current} من {total}*\n\n{question['question']}"
        buttons = []
        for i, opt in enumerate(question["options"]):
            label = opt if len(opt) <= 60 else opt[:57] + "..."
            buttons.append([InlineKeyboardButton(label, callback_data=f"quiz_answer_{i}")])
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)

    async def _finish_quiz(self, message, user_id: int, is_callback: bool) -> None:
        result = QuizSystem.get_result(user_id)
        if not result:
            return
        self.user_data.save_quiz_score(user_id, result["score"], result["total"])
        text = QuizSystem.build_result_text(result)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎓 اختبار جديد", callback_data="quiz"),
             InlineKeyboardButton("📊 إحصائياتي",  callback_data="stats")],
            [SupportSystem.get_button()],
            [InlineKeyboardButton("🏠 الرئيسية",   callback_data="start")],
        ])
        await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        # تحقق من شارة الحافظ
        new_badges = self.user_data.check_and_award_badges(user_id)
        if new_badges and "champion" in new_badges:
            await message.reply_text(
                "🎉 *شارة جديدة!*\n🏆 *الحافظ* — نتيجة 100% في اختبار!",
                parse_mode=ParseMode.MARKDOWN,
            )

        # 📢 إعلان Monetag بعد الاختبار
        await asyncio.sleep(1)
        await MonetagSystem.send_ad(
            message.get_bot() if hasattr(message, "get_bot") else message._bot,
            chat_id=user_id,
            context_label="✅ *أحسنت! إليك شيء قد يهمك*",
        )

    async def _cb_quiz_answer(self, query, user_id: int, option_index: int) -> None:
        try:
            question = QuizSystem.get_current_question(user_id)
            if not question:
                await query.answer("انتهى الاختبار")
                return
            if option_index < 0 or option_index >= len(question["options"]):
                await query.answer("❌ خيار غير صحيح")
                return
            selected_answer         = question["options"][option_index]
            is_correct, correct_ans = QuizSystem.submit_answer(user_id, selected_answer)
            await query.answer("✅ صحيح!" if is_correct else "❌ خطأ")
            if is_correct:
                await query.message.reply_text("✅ إجابة صحيحة! ممتاز!")
            else:
                await query.message.reply_text(
                    f"❌ إجابة خاطئة.\n\n*الإجابة الصحيحة:*\n{correct_ans}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            await asyncio.sleep(0.5)
            if QuizSystem.get_current_question(user_id):
                await self._show_quiz_question(query.message, user_id)
            else:
                await self._finish_quiz(query.message, user_id, is_callback=True)
        except Exception as exc:
            logger.error(f"خطأ في _cb_quiz_answer: {exc}", exc_info=True)
            await query.answer("❌ حدث خطأ")

    async def _cb_quiz_start(self, query, user_id: int) -> None:
        if QuizSystem.is_active(user_id):
            await query.answer("⚠️ لديك اختبار نشط!", show_alert=True)
            return
        questions = QuizSystem.generate_quiz(self.db, question_count=5)
        if not questions:
            await query.answer("❌ تعذّر إنشاء الاختبار", show_alert=True)
            return
        QuizSystem.start(user_id, questions)
        await query.message.edit_text("🎓 جاري تحضير الاختبار...")
        await self._show_quiz_question(query.message, user_id)

    # ── بطاقات الحفظ ─────────────────────────────────────────────

    async def _show_flashcard(self, message, user_id: int) -> None:
        hid = FlashcardSystem.get_current(user_id)
        if hid is None:
            await self._finish_flashcard(message, user_id)
            return
        hadith = self.db.get_by_id(hid)
        if not hadith:
            FlashcardSystem.advance(user_id, False)
            await self._show_flashcard(message, user_id)
            return
        session = FlashcardSystem._sessions.get(user_id, {})
        idx   = session.get("index", 0)
        total = session.get("total", 1)
        text, kb = self.fmt.build_flashcard(hadith)
        header   = f"🃏 *البطاقة {idx + 1} من {total}*\n\n"
        try:
            await message.edit_text(header + text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply_text(header + text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    async def _finish_flashcard(self, message, user_id: int) -> None:
        session = FlashcardSystem.get_result(user_id)
        if not session:
            await message.reply_text("✅ انتهت جلسة البطاقات!")
            return
        correct = session.get("correct", 0)
        total   = session.get("total", 0)
        pct     = round((correct / total) * 100) if total else 0
        text = (
            f"🃏 *انتهت جلسة البطاقات!*\n\n"
            f"✅ حفظت: {correct}/{total}\n"
            f"📊 النسبة: {pct}%\n\n"
        )
        if pct >= 80:
            text += "🌟 ممتاز! استمر في المذاكرة!"
        else:
            text += "💪 راجع الأحاديث التي لم تتذكرها!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 أحاديث المراجعة", callback_data="flashcard_review")],
            [SupportSystem.get_button()],
            [InlineKeyboardButton("🏠 الرئيسية",         callback_data="start")],
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        # تحقق من شارات
        self.user_data.check_and_award_badges(user_id)

        # 📢 إعلان Monetag بعد جلسة البطاقات
        await asyncio.sleep(1)
        try:
            bot = message.get_bot() if hasattr(message, "get_bot") else message._bot
            await MonetagSystem.send_ad(
                bot,
                chat_id=user_id,
                context_label="📚 *جلسة رائعة! إليك شيء قد يهمك*",
            )
        except Exception:
            pass

    # ── اختبار أعرف/لا أعرف ─────────────────────────────────────

    async def _show_selftest(self, message, hadith: Dict[str, Any]) -> None:
        hid  = hadith["id"]
        body = hadith.get("hadith_text_only") or hadith.get("text", "")
        text = (
            f"🤔 *هل تعرف هذا الحديث؟*\n\n"
            f"📖 *{MessageFormatter.esc(hadith['title'])}*\n\n"
            f"«{MessageFormatter.esc(body[:250])}»\n\n"
            "─────────────────────"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ أعرفه",           callback_data=f"selftest_know_{hid}"),
                InlineKeyboardButton("❓ لا أتذكره",       callback_data=f"selftest_dontknow_{hid}"),
            ],
            [
                InlineKeyboardButton("💬 اشرحه لي",       callback_data=f"st_explain_{hid}"),
                InlineKeyboardButton("📖 عرض كامل",        callback_data=f"view_{hid}"),
            ],
            [SupportSystem.get_button()],
            [InlineKeyboardButton("🚪 إنهاء",              callback_data="start")],
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── الخطة الدراسية ────────────────────────────────────────────

    async def _cb_plan(self, query, user_id: int, data: str) -> None:
        if data == "plan_reset":
            self.user_data.set_study_plan(user_id, [])
            await query.message.edit_text(
                "🔄 *إنشاء خطة جديدة*\n\nاختر المدة:",
                reply_markup=self._plan_choice_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        days    = int(data.split("_")[1])
        all_ids = list(range(1, len(self.db) + 1))
        random.shuffle(all_ids)
        self.user_data.set_study_plan(user_id, all_ids)
        rate    = round(len(all_ids) / days, 1)
        await query.message.edit_text(
            f"🎯 *تم إنشاء خطتك الدراسية!*\n\n"
            f"📅 المدة: {days} يوم\n"
            f"📚 المعدل: ~{rate} حديث/يوم\n"
            f"📖 عدد الأحاديث: {len(all_ids)}\n\n"
            "💡 ابدأ بقراءة الأحاديث وسيتتبع البوت تقدمك تلقائياً!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 عرض تقدمي", callback_data="plan")],
                [InlineKeyboardButton("🏠 الرئيسية",  callback_data="start")],
            ]),
            parse_mode=ParseMode.MARKDOWN,
        )

    async def _cb_plan_menu(self, query, user_id: int) -> None:
        cur_plan = self.user_data.get_study_plan(user_id)
        try:
            if not cur_plan:
                await query.message.edit_text(
                    "🎯 *إنشاء خطة دراسية*\n\nاختر المدة:",
                    reply_markup=self._plan_choice_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                text     = self._build_plan_text(user_id, cur_plan)
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 خطة جديدة", callback_data="plan_reset")],
                    [InlineKeyboardButton("🏠 الرئيسية",  callback_data="start")],
                ])
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        except Exception as exc:
            logger.error(f"خطأ في _cb_plan_menu: {exc}")
            await query.answer("❌ حدث خطأ", show_alert=True)

    # ── التذكير ───────────────────────────────────────────────────

    async def _cb_reminder_menu(self, query, user_id: int) -> None:
        settings = self.user_data.get_reminder_settings(user_id)
        status   = "🟢 مفعّل" if settings["enabled"] else "🔴 معطّل"
        evening  = settings.get("time_evening") or "غير مفعّل"
        text = (
            "⏰ *إعدادات التذكير اليومي*\n\n"
            f"*الحالة:* {status}\n"
            f"*الصباحي:* {settings['time']}\n"
            f"*المسائي:* {evening}\n\n"
            "استخدم `/reminder` للتحكم الكامل"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 تفعيل",   callback_data="reminder_on"),
             InlineKeyboardButton("🔴 تعطيل",  callback_data="reminder_off")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="start")],
        ])
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── حديث اليوم ────────────────────────────────────────────────

    async def _cb_daily(self, query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        today = datetime.now().date().isoformat()
        if self.user_data.get_last_daily(user_id) == today:
            await query.answer("📅 لقد حصلت على حديث اليوم بالفعل!", show_alert=True)
            return
        unread    = self.user_data.get_unread_hadiths(user_id, len(self.db))
        hadith_id = random.choice(unread) if unread else random.randint(1, len(self.db))
        hadith    = self.db.get_by_id(hadith_id)
        if hadith:
            await query.message.edit_text("📅 حديث اليوم...")
            self.user_data.update_last_daily(user_id)
            remaining = len(unread) - 1 if unread else 0
            prefix    = f"📅 *حديث اليوم*\n📚 تبقى {remaining} حديثاً للإتمام!\n\n"
            await self._display_hadith(user_id, hadith, query.message, prefix=prefix)
            self.user_data.increment_interaction(user_id)
            await self._send_support_if_due(user_id, context.bot)

            # 📢 إعلان Monetag بعد حديث اليوم — مرة واحدة يومياً فقط
            await asyncio.sleep(2)
            await MonetagSystem.send_ad(
                context.bot,
                chat_id=user_id,
                context_label="🌟 *جزاك الله خيراً على قراءتك اليومية*",
            )

    # ── المفضلة ───────────────────────────────────────────────────

    async def _cb_favorites(self, query, user_id: int) -> None:
        favorites = self.user_data.get_favorites(user_id)
        if not favorites:
            text = (
                "⭐ *المفضلة فارغة*\n\n"
                "لم تقم بإضافة أي حديث للمفضلة بعد.\n"
                "عند عرض أي حديث، اضغط ☆ لإضافته."
            )
        else:
            lines = ["⭐ *أحاديثك المفضلة:*\n"]
            for hid in favorites:
                h = self.db.get_by_id(hid)
                if h:
                    lines.append(f"• الحديث {hid}: {h['title']}")
            lines.append("\n💡 أرسل رقم الحديث لعرضه")
            text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="start")]])
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # ── التواصل مع المطور ─────────────────────────────────────────

    async def _handle_feedback_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user    = update.effective_user
        user_id = user.id
        FeedbackSystem.stop(user_id)
        msg_text = update.message.text
        safe_name = MessageFormatter.esc(user.first_name or "")
        safe_msg  = MessageFormatter.esc(msg_text or "")
        dev_msg  = (
            "📨 *رسالة جديدة من مستخدم نبراس*\n\n"
            f"👤 *المستخدم:* {safe_name}"
        )
        if user.username:
            dev_msg += f" (@{user.username})"
        dev_msg += f"\n🆔 *المعرف:* `{user_id}`\n\n💬 *الرسالة:*\n{safe_msg}"
        try:
            if DEVELOPER_TELEGRAM_ID:
                # زر رد مباشر على المستخدم
                reply_keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        f"↩️ رد على {user.first_name or user_id}",
                        callback_data=f"admin_reply_{user_id}"
                    )
                ]])
                await context.bot.send_message(
                    chat_id=int(DEVELOPER_TELEGRAM_ID),
                    text=dev_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_keyboard,
                )
                await update.message.reply_text(
                    "✅ *تم إرسال رسالتك بنجاح!*\n\nشكراً لك! 🙏",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await update.message.reply_text("⚠️ نظام التواصل غير مفعّل حالياً.")
        except Exception as exc:
            logger.error(f"خطأ في إرسال الملاحظة: {exc}")
            await update.message.reply_text("❌ حدث خطأ في إرسال رسالتك.")


# ═══════════════════════════════════════════════════════════════════
# 11. التطبيق الرئيسي
# ═══════════════════════════════════════════════════════════════════

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import telegram.error as tg_err

    # ✅ تعامل خاص مع خطأ تعارض النسخ — لا يُرسل رسالة للمستخدم
    if isinstance(context.error, tg_err.Conflict):
        logger.critical(
            "⚠️ تعارض: نسختان من البوت تعملان في نفس الوقت! "
            "أوقف إحداهما على Render فوراً."
        )
        return

    # ✅ تجاهل أخطاء المستخدمين الذين حجبوا البوت
    if isinstance(context.error, tg_err.Forbidden):
        logger.warning(f"المستخدم حجب البوت: {context.error}")
        return

    # ✅ تجاهل أخطاء انتهاء الجلسة الشبكية بهدوء
    if isinstance(context.error, tg_err.NetworkError):
        logger.warning(f"خطأ شبكي مؤقت: {context.error}")
        return

    logger.error(f"خطأ غير معالَج: {context.error}", exc_info=context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 عذراً، حدث خطأ غير متوقع.\nيرجى المحاولة مرة أخرى."
            )
    except Exception as exc:
        logger.error(f"خطأ في معالج الأخطاء: {exc}")


async def reminder_loop(bot, user_data_mgr, hadith_db) -> None:
    """حلقة التذكير اليومي — تعمل في خلفية asyncio كل 60 ثانية بدون job_queue"""
    logger.info("⏰ حلقة التذكير بدأت")
    while True:
        try:
            await asyncio.sleep(60)
            users = user_data_mgr.get_all_users_with_reminders()
            # ✅ إصلاح: استخدام UTC timezone-aware بدل naive datetime
            from datetime import timezone as dt_timezone
            now = datetime.now(dt_timezone.utc)
            for user_id, settings in users:
                tz_str = settings.get("timezone", DEFAULT_TIMEZONE)
                try:
                    tz     = ZoneInfo(tz_str)
                    now_tz = now.astimezone(tz)
                    cur_min = now_tz.hour * 60 + now_tz.minute

                    # ── التذكير الصباحي ──
                    time_str = settings.get("time", DEFAULT_REMINDER_TIME)
                    rem_time = ReminderSystem.parse_time(time_str)
                    if rem_time:
                        rem_min = rem_time.hour * 60 + rem_time.minute
                        # ✅ إصلاح: توسيع النافذة من 2 إلى 3 دقائق لتفادي التفويت
                        if abs(cur_min - rem_min) < 3 and ReminderSystem.should_send(settings.get("last_sent"), tz_str):
                            unread    = user_data_mgr.get_unread_hadiths(user_id, len(hadith_db))
                            hadith_id = random.choice(unread) if unread else random.randint(1, len(hadith_db))
                            hadith    = hadith_db.get_by_id(hadith_id)
                            if hadith:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text=ReminderSystem.build_message(hadith, len(unread)),
                                    parse_mode=ParseMode.MARKDOWN,
                                )
                                user_data_mgr.update_last_reminder_sent(user_id, evening=False)
                                logger.info(f"📨 تذكير صباحي → {user_id}")

                    # ── التذكير المسائي ──
                    evening_str = settings.get("time_evening")
                    if evening_str:
                        ev_time = ReminderSystem.parse_time(evening_str)
                        if ev_time:
                            ev_min = ev_time.hour * 60 + ev_time.minute
                            # ✅ إصلاح: توسيع النافذة من 2 إلى 3 دقائق
                            if abs(cur_min - ev_min) < 3 and ReminderSystem.should_send(settings.get("last_evening"), tz_str):
                                hadith = hadith_db.get_random()
                                if hadith:
                                    await bot.send_message(
                                        chat_id=user_id,
                                        text=ReminderSystem.build_evening_message(hadith),
                                        parse_mode=ParseMode.MARKDOWN,
                                    )
                                    user_data_mgr.update_last_reminder_sent(user_id, evening=True)
                                    logger.info(f"🌙 تذكير مسائي → {user_id}")
                except Exception as exc:
                    logger.error(f"خطأ تذكير {user_id}: {exc}")
        except asyncio.CancelledError:
            logger.info("⏰ حلقة التذكير أُوقفت")
            break
        except Exception as exc:
            logger.error(f"خطأ في حلقة التذكير: {exc}")


async def _run_bot() -> None:
    """تشغيل البوت مع حلقة التذكير في asyncio"""
    validate_configuration()

    logger.info("🔧 جاري تهيئة المكونات...")
    hadith_db     = HadithDatabase(HADITH_FILE_PATH)
    user_data_mgr = UserDataManager(USER_DATA_PATH)
    memory        = ConversationMemory()
    formatter     = MessageFormatter()
    ai_engine     = NibrasAI(OPENROUTER_API_KEY, GOOGLE_API_KEY, memory)
    handlers      = BotHandlers(hadith_db, user_data_mgr, ai_engine, formatter)

    logger.info("🤖 جاري بناء البوت...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ── تسجيل الأوامر ──
    for cmd, fn in [
        ("start",       handlers.start_command),
        ("help",        handlers.help_command),
        ("list",        handlers.list_command),
        ("random",      handlers.random_command),
        ("search",      handlers.search_command),
        ("topics",      handlers.topics_command),
        ("stats",       handlers.stats_command),
        ("badges",      handlers.badges_command),
        ("favorites",   handlers.favorites_command),
        ("review",      handlers.review_command),
        ("daily",       handlers.daily_command),
        ("quiz",        handlers.quiz_command),
        ("cancel_quiz", handlers.cancel_quiz_command),
        ("flashcard",   handlers.flashcard_command),
        ("selftest",    handlers.selftest_command),
        ("plan",        handlers.plan_command),
        ("note",        handlers.note_command),
        ("feedback",    handlers.feedback_command),
        ("reminder",    handlers.reminder_command),
        ("cancel",      handlers.cancel_command),
        # ── أوامر المشرف (مخفية) ──
        ("admin_help",      handlers.admin_help_command),
        ("admin_stats",     handlers.admin_stats_command),
        ("admin_broadcast", handlers.admin_broadcast_command),
        ("admin_ban",       handlers.admin_ban_command),
        ("admin_unban",     handlers.admin_unban_command),
        ("admin_export",    handlers.admin_export_command),
        ("admin_user",      handlers.admin_user_command),
        ("admin_top",        handlers.admin_top_command),
        ("admin_inactive",   handlers.admin_inactive_command),
        ("admin_announce",   handlers.admin_announce_command),
        ("admin_maintenance",handlers.admin_maintenance_command),
    ]:
        app.add_handler(CommandHandler(cmd, fn))

    app.add_handler(CallbackQueryHandler(handlers.button_handler))
    app.add_handler(MessageHandler(filters.ALL, handlers.message_handler))
    app.add_error_handler(error_handler)

    print("\n" + "=" * 65)
    print("🌟 بوت نبراس v3 — معلم الأربعين النووية")
    print("=" * 65)
    print(f"✅ يعمل بنجاح! | 📚 الأحاديث: {len(hadith_db)}")
    print(f"🏷️ التصنيفات: {len(hadith_db.get_categories())}")
    print("🆕 الميزات: بطاقة الراوي | الترجمة | البطاقات | الشارات | الموضوعات")
    print("⏸️  اضغط Ctrl+C للإيقاف")
    print("=" * 65 + "\n")
    logger.info(f"🚀 نبراس v3 يعمل | {len(hadith_db)} حديث")

    # ── تشغيل حلقة التذكير و البوت معاً ──
    async with app:
        await app.start()
        await app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # ✅ تجاهل الرسائل المرسلة أثناء توقف البوت
        )

        # شغّل حلقة التذكير في الخلفية
        reminder_task = asyncio.create_task(
            reminder_loop(app.bot, user_data_mgr, hadith_db)
        )
        try:
            # انتظر حتى يتوقف البوت (Ctrl+C)
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                pass
            await app.updater.stop()
            await app.stop()


def main() -> None:
    try:
        asyncio.run(_run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت")
    except Exception as exc:
        logger.error(f"❌ خطأ حرج: {exc}", exc_info=True)
        raise


if __name__ == "__main__":
    main()