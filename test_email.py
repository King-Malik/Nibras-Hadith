#!/usr/bin/env python3
"""
اختبار سريع لخدمة البريد الإلكتروني
"""

import sys
import os

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_service import EmailService
from config import settings

def test_email_connection():
    """اختبار الاتصال بخادم SMTP"""
    print("=" * 60)
    print("🧪 اختبار خدمة البريد الإلكتروني")
    print("=" * 60)
    
    # التحقق من الإعدادات
    print("\n📋 التحقق من الإعدادات:")
    print(f"   SMTP Server: {settings.smtp_server}")
    print(f"   SMTP Port: {settings.smtp_port}")
    print(f"   Username: {settings.smtp_username}")
    print(f"   Password: {'*' * len(settings.smtp_password) if settings.smtp_password else 'غير محدد'}")
    print(f"   To Email: {settings.contact_email_to}")
    
    if not settings.smtp_username or not settings.smtp_password:
        print("\n❌ خطأ: لم يتم تعيين SMTP_USERNAME أو SMTP_PASSWORD في ملف .env")
        print("\nتأكد من:")
        print("  1. وجود ملف .env في المجلد الحالي")
        print("  2. SMTP_USERNAME=your-email@gmail.com")
        print("  3. SMTP_PASSWORD=your-app-password (بدون مسافات!)")
        return False
    
    try:
        # إنشاء خدمة البريد
        print("\n🔌 إنشاء خدمة البريد...")
        email_service = EmailService(
            smtp_server=settings.smtp_server,
            smtp_port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_name=settings.email_from_name
        )
        
        # اختبار الاتصال
        print("🔍 اختبار الاتصال بخادم SMTP...")
        if email_service.test_connection():
            print("✅ نجح الاتصال بخادم SMTP!")
            
            # اختبار إرسال رسالة
            print("\n📧 إرسال رسالة تجريبية...")
            success = email_service.send_contact_email(
                to_email=settings.contact_email_to,
                name="مختبر نبراس",
                email="test@nabras.local",
                subject="رسالة اختبار من نظام نبراس",
                message="هذه رسالة تجريبية للتأكد من عمل نظام البريد الإلكتروني بشكل صحيح.\n\nإذا وصلتك هذه الرسالة، فهذا يعني أن النظام يعمل بشكل ممتاز! ✅"
            )
            
            if success:
                print("\n" + "=" * 60)
                print("🎉 نجح الاختبار! تم إرسال الرسالة التجريبية")
                print("=" * 60)
                print(f"\n✅ تحقق من بريدك: {settings.contact_email_to}")
                print("   (قد تحتاج للتحقق من مجلد Spam)")
                return True
            else:
                print("\n❌ فشل إرسال الرسالة")
                return False
        else:
            print("\n❌ فشل الاتصال بخادم SMTP")
            print("\nتحقق من:")
            print("  1. SMTP_PASSWORD بدون مسافات (vodjrlwrpfhctmrj)")
            print("  2. تفعيل التحقق بخطوتين في Gmail")
            print("  3. إنشاء App Password من https://myaccount.google.com/apppasswords")
            return False
            
    except ValueError as e:
        print(f"\n❌ خطأ في الإعدادات: {e}")
        return False
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback
        print("\nتفاصيل الخطأ:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_email_connection()
    sys.exit(0 if success else 1)
