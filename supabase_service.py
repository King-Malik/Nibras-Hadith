"""
خدمة Supabase للتعامل مع التعليقات
متوافقة مع supabase-py 2.x
"""

import logging
import traceback
from typing import List, Dict, Optional
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger("hadith_app.supabase")


class SupabaseService:
    """خدمة التعامل مع قاعدة بيانات Supabase - متوافقة مع supabase==2.27.3"""

    def __init__(self, supabase_url: str, supabase_key: str):
        """تهيئة اتصال Supabase"""
        if not supabase_url or not supabase_key:
            raise ValueError("❌ يجب تعيين SUPABASE_URL و SUPABASE_KEY في ملف .env")

        try:
            # supabase-py v2: create_client لا يزال يعمل بنفس الطريقة
            self.supabase: Client = create_client(supabase_url, supabase_key)
            logger.info(f"✅ تم الاتصال بـ Supabase بنجاح")
            logger.info(f"📍 URL: {supabase_url}")
            self._test_connection()
        except Exception as e:
            logger.error(f"❌ خطأ في الاتصال بـ Supabase: {e}")
            raise

    def _test_connection(self) -> None:
        """اختبار الاتصال بقاعدة البيانات"""
        try:
            response = (
                self.supabase
                .table("comments")
                .select("id", count="exact")
                .limit(1)
                .execute()
            )
            # supabase-py v2: count متاح في response.count
            count = getattr(response, "count", 0) or 0
            logger.info(f"✅ الاتصال ناجح - عدد التعليقات: {count}")
        except Exception as e:
            # التحذير فقط - لا نوقف التطبيق
            logger.warning(f"⚠️ لم يتم التحقق من الاتصال (الجدول ربما غير موجود بعد): {e}")

    async def add_comment(
        self,
        hadith_id: int,
        name: str,
        email: str,
        comment: str,
    ) -> Dict:
        """إضافة تعليق جديد"""
        logger.info(f"🔵 إضافة تعليق للحديث #{hadith_id} من: {name}")

        # التحقق الإضافي (بعد Pydantic)
        if not name or len(name.strip()) < 2:
            raise ValueError("الاسم يجب أن يكون حرفين على الأقل")
        if not email or "@" not in email:
            raise ValueError("البريد الإلكتروني غير صحيح")
        if not comment or len(comment.strip()) < 5:
            raise ValueError("التعليق يجب أن يكون 5 أحرف على الأقل")

        data = {
            "hadith_id": hadith_id,
            "name": name.strip(),
            "email": email.strip().lower(),
            "comment": comment.strip(),
            "is_approved": True,
            "is_deleted": False,
        }

        try:
            response = self.supabase.table("comments").insert(data).execute()

            # supabase-py v2: البيانات في response.data
            if response.data and len(response.data) > 0:
                result = response.data[0]
                logger.info(f"✅ تم إضافة التعليق بنجاح - ID: {result.get('id')}")
                return result
            else:
                raise RuntimeError("فشل في إضافة التعليق - استجابة فارغة من Supabase")

        except ValueError:
            raise  # إعادة رفع أخطاء التحقق
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة التعليق: {e}\n{traceback.format_exc()}")
            raise RuntimeError(f"خطأ في قاعدة البيانات: {e}") from e

    async def get_comments_for_hadith(
        self,
        hadith_id: int,
        limit: int = 50,
    ) -> List[Dict]:
        """جلب التعليقات الخاصة بحديث معين"""
        logger.debug(f"🔵 جلب التعليقات للحديث #{hadith_id}")

        try:
            response = (
                self.supabase
                .table("comments")
                .select("*")
                .eq("hadith_id", hadith_id)
                .eq("is_approved", True)
                .eq("is_deleted", False)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            comments = response.data or []
            logger.debug(f"✅ تم جلب {len(comments)} تعليق للحديث #{hadith_id}")
            return comments

        except Exception as e:
            logger.error(f"❌ خطأ في جلب تعليقات الحديث #{hadith_id}: {e}")
            traceback.print_exc()
            return []

    async def get_all_comments(self, limit: int = 100) -> List[Dict]:
        """جلب جميع التعليقات المعتمدة"""
        try:
            response = (
                self.supabase
                .table("comments")
                .select("*")
                .eq("is_approved", True)
                .eq("is_deleted", False)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            comments = response.data or []
            logger.info(f"✅ تم جلب {len(comments)} تعليق")
            return comments

        except Exception as e:
            logger.error(f"❌ خطأ في جلب جميع التعليقات: {e}")
            return []

    def format_comment_time(self, created_at: str) -> str:
        """تنسيق وقت التعليق بالعربية"""
        try:
            # التعامل مع صيغ التاريخ المختلفة
            dt_str = created_at.replace("Z", "+00:00")
            comment_time = datetime.fromisoformat(dt_str)

            # ضمان أن كلا التوقيتين aware
            now = datetime.now(timezone.utc)
            if comment_time.tzinfo is None:
                comment_time = comment_time.replace(tzinfo=timezone.utc)

            diff = now - comment_time
            total_seconds = int(diff.total_seconds())

            if total_seconds < 0:
                return "للتو"
            if total_seconds < 60:
                return "منذ لحظات"
            if total_seconds < 3600:
                minutes = total_seconds // 60
                return f"منذ {minutes} دقيقة" if minutes == 1 else f"منذ {minutes} دقائق"
            if total_seconds < 86400:
                hours = total_seconds // 3600
                return f"منذ {hours} ساعة" if hours == 1 else f"منذ {hours} ساعات"
            if diff.days < 30:
                days = diff.days
                return f"منذ {days} يوم" if days == 1 else f"منذ {days} أيام"
            if diff.days < 365:
                months = diff.days // 30
                return f"منذ {months} شهر" if months == 1 else f"منذ {months} أشهر"

            years = diff.days // 365
            return f"منذ {years} سنة" if years == 1 else f"منذ {years} سنوات"

        except Exception as e:
            logger.warning(f"⚠️ خطأ في تنسيق الوقت ({created_at}): {e}")
            return "منذ فترة"
