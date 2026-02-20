# 🚀 دليل GitHub السريع

## رفع المشروع على GitHub في 5 دقائق

---

## الخطوة 1: إنشاء Repository

1. اذهب إلى [github.com](https://github.com)
2. اضغط **"+"** → **"New repository"**
3. املأ المعلومات:

```
Repository name: nabras-hadith
Description: نبراس - الأربعون النووية | منصة تفاعلية للأحاديث النبوية الشريفة
☑️ Public (أو Private حسب رغبتك)
❌ لا تضف README
❌ لا تضف .gitignore  
❌ لا تضف License
```

4. اضغط **"Create repository"**

---

## الخطوة 2: رفع المشروع

### افتح Terminal في مجلد المشروع

```bash
# التهيئة الأولى
git init
git branch -M main

# إضافة جميع الملفات
git add .

# أول Commit
git commit -m "🎉 Initial commit - نبراس v1.1.1"

# ربط مع GitHub (استبدل YOUR_USERNAME باسمك)
git remote add origin https://github.com/YOUR_USERNAME/nabras-hadith.git

# رفع الملفات
git push -u origin main
```

✅ **تم! المشروع الآن على GitHub**

---

## الخطوة 3: تحديثات مستقبلية

بعد أي تعديل على الكود:

```bash
git add .
git commit -m "✨ وصف التغيير"
git push origin main
```

### أمثلة على رسائل Commit:

```bash
git commit -m "🐛 Fix email sending issue"
git commit -m "✨ Add new feature"
git commit -m "📝 Update documentation"
git commit -m "🎨 Improve UI design"
git commit -m "⚡ Improve performance"
```

---

## ⚠️ ملاحظات مهمة

### 🔒 الأمان

ملف `.gitignore` موجود ويمنع رفع:
- ❌ `.env` (المتغيرات السرية)
- ❌ `__pycache__/` (ملفات مؤقتة)
- ❌ `venv/` (البيئة الافتراضية)

**لا ترفع ملف `.env` أبداً!**

---

## 📁 الملفات المرفوعة

### ✅ سيتم رفع:
- الكود المصدري (`.py`)
- القوالب (`templates/`)
- الملفات الثابتة (`static/`)
- الوثائق (`.md`)
- المتطلبات (`requirements.txt`)
- إعدادات النشر (`Procfile`, `render.yaml`)

### ❌ لن يتم رفع:
- `.env` (المتغيرات السرية) 🔒
- `__pycache__/`
- `venv/`
- `*.log`

---

## 🔄 النشر التلقائي

### بعد رفع المشروع على GitHub:

#### على Render:
1. [render.com](https://render.com) → **New** → **Web Service**
2. اختر repository: `nabras-hadith`
3. أضف المتغيرات البيئية
4. **كل `git push` سينشر التحديث تلقائياً!** 🎉

#### على Railway:
1. [railway.app](https://railway.app) → **New Project**
2. **Deploy from GitHub**
3. اختر repository
4. النشر سيبدأ تلقائياً!

---

## 📝 أوامر Git الأساسية

```bash
# حالة الملفات
git status

# إضافة ملف محدد
git add filename.py

# إضافة كل الملفات
git add .

# حفظ التغييرات
git commit -m "رسالة التغيير"

# رفع للسيرفر
git push origin main

# سحب آخر التحديثات
git pull origin main

# عرض السجل
git log --oneline

# التراجع عن آخر commit (قبل push)
git reset --soft HEAD~1

# التراجع عن تغييرات ملف معين
git checkout -- filename.py
```

---

## 🌿 العمل بالفروع (Branches)

```bash
# إنشاء فرع جديد
git checkout -b feature/new-feature

# التبديل بين الفروع
git checkout main
git checkout feature/new-feature

# دمج فرع مع main
git checkout main
git merge feature/new-feature

# حذف فرع
git branch -d feature/new-feature
```

---

## 🆘 حل المشاكل الشائعة

### ❌ خطأ: "remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/nabras-hadith.git
```

### ❌ خطأ: "failed to push"

```bash
git pull origin main --rebase
git push origin main
```

### ❌ خطأ: "Permission denied"

**الحل:**
1. تأكد من تسجيل دخولك في GitHub
2. استخدم Personal Access Token بدلاً من كلمة المرور:
   - GitHub → Settings → Developer settings → Personal access tokens
   - Generate new token (classic)
   - اختر `repo` permissions
   - انسخ التوكن واستخدمه كـ password

### ❌ نسيت إضافة ملف قبل commit

```bash
git add forgotten-file.py
git commit --amend --no-edit
```

### ❌ أريد إلغاء جميع التغييرات المحلية

```bash
git reset --hard HEAD
git clean -fd
```

---

## 🎯 الخطوات التالية

بعد رفع المشروع على GitHub:

1. ✅ انسخ URL الخاص بـ repository
2. ✅ اذهب إلى [DEPLOYMENT.md](DEPLOYMENT.md)
3. ✅ اتبع دليل النشر على Render أو Railway
4. ✅ أضف المتغيرات البيئية من `.env`
5. ✅ استمتع بموقعك الحي! 🎉

---

## 💡 نصائح للمحترفين

### 1. استخدم Commits وصفية
```bash
# ❌ سيء
git commit -m "update"

# ✅ جيد
git commit -m "✨ Add email notification feature"
```

### 2. Commit بشكل منتظم
لا تنتظر حتى تنتهي من كل شيء - اعمل commits صغيرة ومتكررة

### 3. استخدم .gitignore
تأكد من عدم رفع ملفات غير ضرورية

### 4. اقرأ السجلات
```bash
git log --oneline --graph --all
```

### 5. استخدم GitHub Desktop (اختياري)
إذا لم تكن مرتاحاً مع Command Line:
- حمّل [GitHub Desktop](https://desktop.github.com/)
- واجهة رسومية سهلة

---

## 📚 موارد إضافية

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [Git Cheat Sheet](https://education.github.com/git-cheat-sheet-education.pdf)

---

**الإصدار:** 1.1.1  
**آخر تحديث:** 2026-02-15

---

🎉 **مبروك! مشروعك الآن على GitHub**

الخطوة التالية: [DEPLOYMENT.md](DEPLOYMENT.md) لنشر الموقع
