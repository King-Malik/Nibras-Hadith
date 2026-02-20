"""
إعدادات التطبيق - متوافقة مع pydantic-settings 2.7.1
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "نبراس"
    app_subtitle: str = "الأربعون النووية"
    app_version: str = "1.1.1"
    debug: bool = False
    environment: str = "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    secret_key: str = Field(
        default="change-this-in-production-use-a-long-random-string",
        description="مفتاح سري للأمان - يجب تغييره في الإنتاج",
    )
    allowed_origins: str = "*"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Cache
    cache_enabled: bool = True
    cache_ttl: int = 3600

    # SEO
    site_url: str = "https://nibras-hadith.onrender.com"
    site_description: str = "نبراس - الأربعون النووية - مرجع شامل للأحاديث النبوية الشريفة"
    site_keywords: str = "الأحاديث النبوية, الأربعون النووية, السنة النبوية, الإسلام, نبراس, أحاديث صحيحة, شرح الأربعين النووية, صحيح البخاري, صحيح مسلم, علوم الحديث, تخريج الأحاديث, متون الحديث, تطبيق إسلامي, السيرة النبوية, فقه الحديث"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Telegram Bot (اختياري)
    telegram_bot_token: Optional[str] = None

    # Google AdSense
    adsense_enabled: bool = False
    adsense_client: str = "ca-pub-XXXXXXXXXXXXXXXX"
    adsense_slot_index: str = "1111111111"
    adsense_slot_index_grid: str = "2222222222"
    adsense_slot_detail: str = "3333333333"
    adsense_slot_quiz: str = "4444444444"

    # Email Configuration (Resend)
    resend_api_key: str = Field(
        default="",
        description="مفتاح API الخاص بـ Resend"
    )
    contact_email_to: str = Field(
        default="",
        description="البريد الذي سيتلقى رسائل نموذج التواصل"
    )
    email_from_name: str = Field(
        default="نبراس - الأربعون النووية",
        description="اسم المرسل الذي سيظهر في البريد"
    )

    # pydantic-settings v2: SettingsConfigDict بدلاً من class Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # تجاهل الحقول غير المعرّفة في .env
    )


settings = Settings()
