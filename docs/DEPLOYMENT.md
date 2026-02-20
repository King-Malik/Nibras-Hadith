# 🚀 دليل نشر نبراس v1.1.1

دليل شامل لنشر المشروع على منصات مختلفة.

---

## 📋 جدول المحتويات

1. [قبل البدء](#قبل-البدء)
2. [النشر على Render](#1-النشر-على-render-موصى-به)
3. [النشر على Railway](#2-النشر-على-railway)
4. [النشر على Heroku](#3-النشر-على-heroku)
5. [النشر على VPS](#4-النشر-على-vps)
6. [المتغيرات البيئية](#المتغيرات-البيئية-المطلوبة)
7. [ما بعد النشر](#ما-بعد-النشر)

---

## قبل البدء

### ✅ التأكد من الإعدادات

تأكد من تحديث ملف `.env` بمعلوماتك:

```env
# معلومات التطبيق
APP_NAME=نبراس
APP_VERSION=1.1.1

# البريد الإلكتروني (مهم!)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-without-spaces
CONTACT_EMAIL_TO=your-email@gmail.com

# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### 📦 رفع المشروع على GitHub

```bash
# في مجلد المشروع
git init
git add .
git commit -m "🎉 Initial commit - نبراس v1.1.1"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/nabras-hadith.git
git push -u origin main
```

⚠️ **مهم:** لا تنس إضافة `.gitignore` لمنع رفع `.env`

---

## 1. النشر على Render (موصى به)

### ✅ لماذا Render؟
- ✅ مجاني (750 ساعة/شهر)
- ✅ نشر تلقائي من GitHub
- ✅ SSL مجاني
- ✅ سهل جداً

### 📝 الخطوات

#### 1. إنشاء حساب
1. اذهب إلى [render.com](https://render.com)
2. سجل دخول بحساب GitHub

#### 2. إنشاء Web Service
1. **"New +"** → **"Web Service"**
2. اختر repository: `nabras-hadith`
3. املأ المعلومات:

```
Name: nabras-hadith
Region: Frankfurt (أقرب للشرق الأوسط)
Branch: main
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### 3. إضافة المتغيرات البيئية

في قسم **Environment Variables**:

```env
APP_NAME=نبراس
APP_SUBTITLE=الأربعون النووية
APP_VERSION=1.1.1
ENVIRONMENT=production
DEBUG=False

# SMTP - مهم للغاية!
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=kingaoi.social@gmail.com
SMTP_PASSWORD=wslnwzjsgptpjrrn
CONTACT_EMAIL_TO=kingaoi.social@gmail.com
EMAIL_FROM_NAME=نبراس - الأربعون النووية

# Supabase
SUPABASE_URL=https://vwmmohptbezavnheabdh.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Security
SECRET_KEY=generate-random-string-here
ALLOWED_ORIGINS=*

# Site
SITE_URL=https://nabras-hadith.onrender.com
RATE_LIMIT_PER_MINUTE=60
CACHE_ENABLED=True
CACHE_TTL=3600
```

#### 4. النشر
اضغط **"Create Web Service"** وانتظر 5-10 دقائق

✅ الموقع سيكون على: `https://your-app-name.onrender.com`

### 🔄 التحديثات التلقائية

كل `git push` سيُحدّث الموقع تلقائياً! 🎉

---

## 2. النشر على Railway

### ✅ المميزات
- $5 رصيد مجاني شهرياً
- نشر سريع جداً
- واجهة ممتازة

### 📝 الخطوات

#### 1. إنشاء حساب
اذهب إلى [railway.app](https://railway.app)

#### 2. إنشاء مشروع
1. **"New Project"** → **"Deploy from GitHub repo"**
2. اختر `nabras-hadith`

#### 3. إضافة المتغيرات
في **Variables**، أضف نفس المتغيرات من Render أعلاه

#### 4. تعديل Start Command (إذا لزم)
في **Settings** → **Deploy**:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

✅ النشر سيبدأ تلقائياً!

---

## 3. النشر على Heroku

### ⚠️ ملاحظة
Heroku أصبح مدفوع ($7/شهر)

### 📝 الخطوات

#### 1. تثبيت Heroku CLI

**Windows:**
```bash
choco install heroku-cli
```

**macOS:**
```bash
brew install heroku/brew/heroku
```

**Linux:**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

#### 2. تسجيل الدخول
```bash
heroku login
```

#### 3. إنشاء تطبيق
```bash
heroku create nabras-hadith
```

#### 4. إضافة المتغيرات البيئية

**عبر Dashboard:**
1. اذهب إلى Dashboard → Settings → Config Vars
2. أضف المتغيرات واحداً تلو الآخر

**أو عبر CLI:**
```bash
heroku config:set APP_NAME=نبراس
heroku config:set APP_VERSION=1.1.1
heroku config:set SMTP_USERNAME=your-email@gmail.com
# ... إلخ
```

#### 5. النشر
```bash
git push heroku main
```

---

## 4. النشر على VPS

### 💰 الخيارات المتاحة
- DigitalOcean ($4-6/شهر) - موصى به
- Linode
- Vultr
- AWS EC2
- Google Cloud

### 📝 الخطوات (Ubuntu 22.04)

#### 1. الاتصال بالسيرفر
```bash
ssh root@your-server-ip
```

#### 2. تثبيت المتطلبات
```bash
# تحديث النظام
apt update && apt upgrade -y

# تثبيت Python و Nginx
apt install python3 python3-pip python3-venv nginx git -y
```

#### 3. نسخ المشروع
```bash
cd /var/www
git clone https://github.com/YOUR_USERNAME/nabras-hadith.git
cd nabras-hadith
```

#### 4. إعداد البيئة الافتراضية
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. إنشاء ملف .env
```bash
nano .env
```

الصق محتوى الإعدادات، ثم:
- `Ctrl + X`
- `Y`
- `Enter`

#### 6. إعداد Systemd Service
```bash
nano /etc/systemd/system/nabras.service
```

```ini
[Unit]
Description=Nabras Hadith App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/nabras-hadith
Environment="PATH=/var/www/nabras-hadith/venv/bin"
ExecStart=/var/www/nabras-hadith/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable nabras
systemctl start nabras
systemctl status nabras
```

#### 7. إعداد Nginx
```bash
nano /etc/nginx/sites-available/nabras
```

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/nabras-hadith/static;
        expires 30d;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/nabras /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

#### 8. إعداد SSL مجاني (Let's Encrypt)
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d your-domain.com -d www.your-domain.com
```

✅ الموقع الآن يعمل على HTTPS!

---

## المتغيرات البيئية المطلوبة

### ✅ إلزامية (لا يعمل بدونها)

```env
APP_NAME=نبراس
APP_VERSION=1.1.1
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### 📧 للبريد الإلكتروني (موصى به بشدة)

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-without-spaces
CONTACT_EMAIL_TO=your-email@gmail.com
EMAIL_FROM_NAME=نبراس - الأربعون النووية
```

### 🔒 للأمان

```env
SECRET_KEY=generate-random-string
ALLOWED_ORIGINS=https://yourdomain.com
```

**توليد SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 🌐 للموقع

```env
SITE_URL=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=60
CACHE_ENABLED=True
CACHE_TTL=3600
```

---

## ما بعد النشر

### ✅ قائمة التحقق

- [ ] الموقع يعمل ويفتح بشكل صحيح
- [ ] اختبر نموذج "اتصل بنا" - أرسل رسالة تجريبية
- [ ] تحقق من التعليقات - أضف تعليق تجريبي
- [ ] اختبر الإعدادات:
  - [ ] الوضع الليلي يعمل
  - [ ] تكبير النص يعمل
  - [ ] التنبيهات تطلب إذن
- [ ] اختبر على الموبايل
- [ ] تحقق من SSL (HTTPS)

### 🔍 فحص السجلات

**Render:**
Dashboard → Logs

**Railway:**
Project → Logs

**VPS:**
```bash
journalctl -u nabras -f
```

### 🔄 تحديث الموقع

**Render / Railway (تلقائي):**
```bash
git add .
git commit -m "Update features"
git push origin main
```

**VPS (يدوي):**
```bash
cd /var/www/nabras-hadith
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
systemctl restart nabras
```

---

## 🐛 حل المشاكل الشائعة

### ❌ "Application failed to start"
**الحل:** تحقق من السجلات، غالباً متغير بيئي ناقص

### ❌ "Port already in use"
**الحل:** استخدم `$PORT` environment variable

### ❌ "Module not found"
**الحل:** تأكد من `requirements.txt` محدّث:
```bash
pip freeze > requirements.txt
```

### ❌ البريد الإلكتروني لا يعمل
**الحل:**
1. تأكد من App Password صحيح وبدون مسافات
2. فعّل التحقق بخطوتين في Gmail
3. تحقق من السجلات للأخطاء

### ❌ الموقع بطيء
**الحل:**
- Render: ترقية إلى خطة مدفوعة
- أو انتقل إلى VPS

---

## 🎯 توصياتنا

### للمبتدئين → **Render**
- ✅ مجاني
- ✅ سهل جداً
- ✅ نشر تلقائي

### للمحترفين → **VPS (DigitalOcean)**
- ✅ تحكم كامل
- ✅ أداء أفضل
- ✅ أرخص على المدى الطويل

### للتجريب → **Railway**
- ✅ أسرع نشر
- ✅ واجهة ممتازة

---

## 📚 روابط مفيدة

- [Render Documentation](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app)
- [Heroku Python Guide](https://devcenter.heroku.com/articles/getting-started-with-python)
- [DigitalOcean Tutorials](https://www.digitalocean.com/community/tutorials)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)

---

## 🆘 تحتاج مساعدة؟

1. راجع السجلات (Logs)
2. تحقق من المتغيرات البيئية
3. تأكد من `requirements.txt`
4. جرب على localhost أولاً

---

**الإصدار:** 1.1.1  
**آخر تحديث:** 2026-02-15  
**الحالة:** ✅ جاهز للنشر

---

🎉 **بالتوفيق في نشر موقعك!**
