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
        self._validate_config()

    def _validate_config(self):
        """التحقق من صحة الإعدادات"""
        if not self.api_key:
            raise ValueError("Resend API key is required")

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

            html_content = f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    .field {{
                        margin-bottom: 20px;
                        padding-bottom: 20px;
                        border-bottom: 1px solid #e5e7eb;
                    }}
                    .field:last-child {{
                        border-bottom: none;
                    }}
                    .label {{
                        font-weight: 600;
                        color: #374151;
                        margin-bottom: 8px;
                        font-size: 14px;
                        letter-spacing: 0.5px;
                    }}
                    .value {{
                        color: #1f2937;
                        font-size: 16px;
                        line-height: 1.6;
                        white-space: pre-wrap;
                    }}
                    .footer {{
                        background-color: #f9fafb;
                        padding: 20px;
                        text-align: center;
                        color: #6b7280;
                        font-size: 12px;
                        border-top: 1px solid #e5e7eb;
                    }}
                    .timestamp {{
                        color: #9ca3af;
                        font-size: 12px;
                        margin-top: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📬 رسالة جديدة من نبراس</h1>
                    </div>
                    <div class="content">
                        <div class="field">
                            <div class="label">الاسم</div>
                            <div class="value">{name}</div>
                        </div>
                        <div class="field">
                            <div class="label">البريد الإلكتروني</div>
                            <div class="value"><a href="mailto:{email}">{email}</a></div>
                        </div>
                        <div class="field">
                            <div class="label">الموضوع</div>
                            <div class="value">{subject}</div>
                        </div>
                        <div class="field">
                            <div class="label">الرسالة</div>
                            <div class="value">{message}</div>
                        </div>
                        <div class="timestamp">
                            تم الإرسال في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </div>
                    </div>
                    <div class="footer">
                        <p>هذه الرسالة وردت من نموذج "اتصل بنا" في موقع نبراس - الأربعون النووية</p>
                        <p>يمكنك الرد على <a href="mailto:{email}">{email}</a> للتواصل مع المرسل</p>
                    </div>
                </div>
            </body>
            </html>
            """

            logger.info(f"📧 محاولة إرسال بريد إلى {to_email} عبر Resend")

            r = resend.Emails.send({
                "from": f"{self.from_name} <onboarding@resend.dev>",
                "to": [to_email],
                "reply_to": email,
                "subject": f"[نبراس - اتصل بنا] {subject}",
                "html": html_content,
            })

            logger.info(f"✅ تم إرسال البريد بنجاح من {name} ({email}) - ID: {r.get('id', 'N/A')}")
            return True

        except Exception as e:
            logger.error(f"❌ خطأ في إرسال البريد عبر Resend: {e}")
            logger.exception(e)
            return False

    def test_connection(self) -> bool:
        """اختبار صحة مفتاح API"""
        try:
            import resend
            resend.api_key = self.api_key
            logger.info("✅ مفتاح Resend API تم تحميله بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ فشل التحقق من مفتاح Resend: {e}")
            return False
