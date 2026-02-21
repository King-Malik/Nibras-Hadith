"""
خدمة إرسال البريد الإلكتروني
دعم Resend لإرسال رسائل نموذج التواصل
"""

import logging
from datetime import datetime

logger = logging.getLogger("hadith_app.email")


class EmailService:
    """خدمة إرسال البريد الإلكتروني عبر Resend"""

    def __init__(self, api_key: str, from_name: str = "نبراس"):
        self.api_key = api_key
        self.from_name = from_name
        # عنوان المرسل: onboarding@resend.dev يعمل مع أي بريد مستلم في test mode
        # لكن في الإنتاج مع domain مُتحقق منه، استخدم: noreply@your-domain.com
        # حالياً: resend يسمح بالإرسال إلى أي بريد باستخدام onboarding@resend.dev
        # طالما أن المفتاح صالح وتم إضافة البريد المستلم في Resend dashboard
        self.from_address = f"{from_name} <onboarding@resend.dev>"
        self._validate_config()

    def _validate_config(self):
        """التحقق من صحة الإعدادات"""
        if not self.api_key:
            raise ValueError("Resend API key is required")
        if not self.api_key.startswith("re_"):
            logger.warning("⚠️ مفتاح Resend API لا يبدأ بـ 're_' - قد يكون غير صالح")

    def send_contact_email(
        self,
        to_email: str,
        name: str,
        email: str,
        subject: str,
        message: str
    ) -> bool:
        """
        إرسال رسالة من نموذج التواصل

        Args:
            to_email: البريد المستلم (إدارة الموقع)
            name: اسم المرسل
            email: بريد المرسل
            subject: موضوع الرسالة
            message: محتوى الرسالة

        Returns:
            bool: True إذا نجح الإرسال، False إذا فشل
        """
        try:
            import resend
            resend.api_key = self.api_key

            # تنظيف المدخلات لمنع XSS في HTML
            safe_name    = name.replace("<", "&lt;").replace(">", "&gt;")
            safe_email   = email.replace("<", "&lt;").replace(">", "&gt;")
            safe_subject = subject.replace("<", "&lt;").replace(">", "&gt;")
            safe_message = message.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

            html_content = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f0fdf4;
                        padding: 24px 16px;
                        direction: rtl;
                    }}
                    .container {{
                        max-width: 580px;
                        margin: 0 auto;
                        background: #ffffff;
                        border-radius: 12px;
                        box-shadow: 0 4px 24px rgba(16,185,129,0.12);
                        overflow: hidden;
                        border: 1px solid #d1fae5;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        color: white;
                        padding: 28px 32px;
                        text-align: center;
                    }}
                    .header-logo {{
                        font-size: 28px;
                        margin-bottom: 8px;
                    }}
                    .header h1 {{
                        font-size: 20px;
                        font-weight: 700;
                        margin: 0;
                    }}
                    .header p {{
                        font-size: 13px;
                        opacity: 0.85;
                        margin-top: 4px;
                    }}
                    .content {{
                        padding: 28px 32px;
                    }}
                    .field {{
                        background: #f9fafb;
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        padding: 14px 16px;
                        margin-bottom: 12px;
                    }}
                    .label {{
                        font-size: 11px;
                        font-weight: 700;
                        color: #6b7280;
                        text-transform: uppercase;
                        letter-spacing: 0.05em;
                        margin-bottom: 5px;
                    }}
                    .value {{
                        color: #111827;
                        font-size: 15px;
                        line-height: 1.6;
                    }}
                    .value a {{
                        color: #10b981;
                        text-decoration: none;
                    }}
                    .message-field .value {{
                        white-space: pre-wrap;
                        background: white;
                        border-radius: 6px;
                        padding: 10px;
                        border: 1px solid #e5e7eb;
                        font-size: 14px;
                        line-height: 1.8;
                    }}
                    .reply-btn {{
                        display: block;
                        background: #10b981;
                        color: white;
                        text-decoration: none;
                        text-align: center;
                        padding: 14px 24px;
                        border-radius: 8px;
                        font-size: 15px;
                        font-weight: 700;
                        margin: 20px 0 4px;
                    }}
                    .footer {{
                        background: #f9fafb;
                        border-top: 1px solid #e5e7eb;
                        padding: 16px 32px;
                        text-align: center;
                        color: #9ca3af;
                        font-size: 12px;
                        line-height: 1.6;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="header-logo">📬</div>
                        <h1>رسالة جديدة من نبراس</h1>
                        <p>{datetime.now().strftime('%Y-%m-%d %H:%M')} UTC</p>
                    </div>
                    <div class="content">
                        <div class="field">
                            <div class="label">المرسل</div>
                            <div class="value">{safe_name}</div>
                        </div>
                        <div class="field">
                            <div class="label">البريد الإلكتروني</div>
                            <div class="value"><a href="mailto:{safe_email}">{safe_email}</a></div>
                        </div>
                        <div class="field">
                            <div class="label">الموضوع</div>
                            <div class="value">{safe_subject}</div>
                        </div>
                        <div class="field message-field">
                            <div class="label">الرسالة</div>
                            <div class="value">{safe_message}</div>
                        </div>
                        <a href="mailto:{safe_email}?subject=رد: {safe_subject}" class="reply-btn">
                            ← الرد على الرسالة
                        </a>
                    </div>
                    <div class="footer">
                        وردت هذه الرسالة عبر نموذج "اتصل بنا" في موقع نبراس - الأربعون النووية<br>
                        <a href="https://nibras-hadith.onrender.com" style="color:#10b981;">nibras-hadith.onrender.com</a>
                    </div>
                </div>
            </body>
            </html>
            """

            logger.info(f"📧 إرسال بريد إلى {to_email} من {name} ({email})")

            r = resend.Emails.send({
                "from": self.from_address,
                "to": [to_email],
                "reply_to": email,
                "subject": f"[نبراس] {subject} - من {name}",
                "html": html_content,
            })

            email_id = r.get("id", "N/A") if isinstance(r, dict) else getattr(r, "id", "N/A")
            logger.info(f"✅ بريد مُرسل بنجاح - ID: {email_id}")
            return True

        except ImportError:
            logger.error("❌ مكتبة resend غير مثبتة. شغّل: pip install resend")
            return False
        except Exception as e:
            logger.error(f"❌ خطأ Resend: {type(e).__name__}: {e}")
            return False

    def test_connection(self) -> bool:
        """
        اختبار صحة مفتاح API عبر Resend
        ملاحظة: لا نرسل بريداً فعلياً - فقط نتحقق من تهيئة المكتبة
        """
        try:
            import resend
            resend.api_key = self.api_key
            # التحقق الأساسي: هل المفتاح يبدأ بـ re_؟
            if not self.api_key.startswith("re_"):
                logger.error("❌ مفتاح Resend غير صالح (يجب أن يبدأ بـ re_)")
                return False
            logger.info(f"✅ مفتاح Resend محمّل: {self.api_key[:8]}...")
            return True
        except ImportError:
            logger.error("❌ مكتبة resend غير مثبتة - pip install resend")
            return False
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار Resend: {e}")
            return False
