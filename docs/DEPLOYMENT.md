# دليل النشر — نبراس

## النشر على Render (موصى به)

### 1. رفع الكود على GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/your-username/nibras
git push -u origin main
```

### 2. إنشاء Web Service على Render

1. اذهب إلى [render.com](https://render.com) وسجّل الدخول
2. انقر **New → Web Service**
3. اربط مستودع GitHub
4. الإعدادات:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### 3. إضافة المتغيرات البيئية

في Render Dashboard → Environment، أضف:

```
SECRET_KEY          = (مفتاح عشوائي طويل)
SUPABASE_URL        = https://your-project.supabase.co
SUPABASE_KEY        = your-service-role-key
RESEND_API_KEY      = re_your_api_key
CONTACT_EMAIL_TO    = your@email.com
SITE_URL            = https://your-app.onrender.com
ALLOWED_ORIGINS     = https://your-app.onrender.com
```

### 4. النشر

انقر **Deploy** وانتظر اكتمال البناء. السجلات الصحيحة:

```
✅ تم تحميل 42 حديث بنجاح
✅ تم الاتصال بـ Supabase بنجاح
📧 Email Service (Resend): ✅ جاهز للإرسال
Application startup complete.
```

---

## ملاحظات مهمة

### Resend
- مفتاح `RESEND_API_KEY` يجب أن يبدأ بـ `re_`
- أضف `CONTACT_EMAIL_TO` كـ Verified Email في Resend Dashboard
- أو اربط Domain خاص لإرسال لأي بريد

### Supabase
- استخدم `service_role` key وليس `anon` key
- راجع [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) لإنشاء الجداول

### حجم الخطة
- Render Free تكفي للمشروع
- تنام بعد 15 دقيقة خمول (تستيقظ عند أول طلب)
