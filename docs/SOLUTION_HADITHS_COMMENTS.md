# 🔧 حل مشكلة الأحاديث والتعليقات

## المشكلة 1: الأحاديث لا تظهر في الصفحة الرئيسية ❌

### التشخيص:
الكود في `main.py` صحيح لكن المشكلة قد تكون:
1. ملف `hadith.json` غير موجود أو فارغ
2. مسار الملف خاطئ
3. خطأ في JSON format
4. HADITHS_DATA فارغة

### الحل:

#### الخطوة 1: تحقق من ملف hadith.json

```bash
# في Terminal
cd /path/to/your/project
ls -la hadith.json
# يجب أن ترى الملف

# تحقق من محتواه
head -20 hadith.json
```

#### الخطوة 2: تحقق من الأخطاء في logs

```python
# في main.py - تحقق من السطر 62-83
# يجب أن ترى رسالة مثل:
# ✅ تم تحميل 42 حديث بنجاح

# إذا رأيت:
# ⚠️ الملف hadith.json غير موجود!
# أو
# ❌ خطأ في صيغة JSON

# فهذه هي المشكلة!
```

#### الخطوة 3: الحل النهائي - كود محسّن في main.py

استبدل دالة `load_hadiths()` في `main.py` بهذا الكود المحسّن:

```python
def load_hadiths() -> List[Dict]:
    """تحميل بيانات الأحاديث من ملف JSON"""
    # جرّب المسارات المختلفة
    possible_paths = [
        "hadith.json",
        "./hadith.json",
        os.path.join(os.path.dirname(__file__), "hadith.json"),
        "/app/hadith.json",  # للـ Docker
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        logger.error(f"❌ ملف hadith.json غير موجود في أي من المسارات: {possible_paths}")
        logger.error(f"المجلد الحالي: {os.getcwd()}")
        logger.error(f"محتويات المجلد: {os.listdir('.')}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            if not data or len(data) == 0:
                logger.warning(f"⚠️ ملف {file_path} فارغ!")
                return []
            
            logger.info(f"✅ تم تحميل {len(data)} حديث بنجاح من {file_path}")
            
            # تحقق من صحة البيانات
            for idx, hadith in enumerate(data):
                required_fields = ["id", "title", "text", "narrator"]
                for field in required_fields:
                    if field not in hadith:
                        logger.warning(f"⚠️ الحديث #{idx+1} يفتقد الحقل: {field}")
            
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
```

#### الخطوة 4: إضافة endpoint للتشخيص

أضف هذا الـ route في `main.py`:

```python
@app.get("/debug/hadiths")
async def debug_hadiths(request: Request):
    """صفحة تشخيص الأحاديث - للتطوير فقط"""
    if not settings.debug:
        raise HTTPException(status_code=404)
    
    return {
        "total_hadiths": len(HADITHS_DATA),
        "hadiths_loaded": len(HADITHS_DATA) > 0,
        "first_hadith": HADITHS_DATA[0] if HADITHS_DATA else None,
        "current_dir": os.getcwd(),
        "files_in_dir": os.listdir('.'),
        "hadith_json_exists": os.path.exists('hadith.json'),
    }
```

ثم زر: `http://localhost:8000/debug/hadiths`

---

## المشكلة 2: استخدام نفس form التعليقات في detail.html ✨

### الحل الكامل:

#### الملف: `templates/detail.html`

استبدل قسم التعليقات (من السطر 607 حتى 666) بهذا الكود:

```html
<!-- Comments Section -->
<div class="comments-section">
    <div class="section-header">
        <div class="section-icon">
            <span class="material-icons-outlined" style="font-size: 32px;">forum</span>
        </div>
        <h2 class="section-title">التأملات والتعليقات</h2>
        <p class="section-subtitle">شاركنا فهمك وتأملك في هذا الحديث الشريف</p>
    </div>

    <!-- Comment Form - نفس النموذج من index.html -->
    <form id="hadithCommentForm" class="comment-form" onsubmit="handleCommentSubmit(event, HADITH_ID, 'commentsContainer')">
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">اسمك الكريم</label>
                <input type="text" id="hadithName" placeholder="مالك" required class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">بريدك الإلكتروني</label>
                <input type="email" id="hadithEmail" placeholder="example@mail.com" required class="form-input">
            </div>
        </div>

        <div class="form-group">
            <label class="form-label">شاركنا تأملك</label>
            <textarea id="hadithComment" placeholder="اكتب تأملك في هذا الحديث الشريف..." required class="form-textarea"></textarea>
        </div>

        <div class="form-actions">
            <span class="form-hint">
                <span class="material-icons-outlined" style="font-size: 16px;">auto_stories</span>
                تعليقك على هذا الحديث
            </span>
            <button type="submit" id="hadithSubmitBtn" class="btn btn-primary">
                <span class="material-icons-outlined">send</span>
                إرسال التأمل
            </button>
        </div>
    </form>

    <!-- Comments Grid -->
    <div id="commentsContainer" class="comments-grid">
        <div style="grid-column: 1/-1; text-align: center; padding: 48px 24px;">
            <p style="color: var(--color-text-secondary);">جارٍ تحميل التعليقات...</p>
        </div>
    </div>
</div>
```

#### الملف: `static/js/main.js`

حدّث دالة `handleCommentSubmit` لتدعم كلا الحالتين:

```javascript
/**
 * دالة معالجة إرسال التعليقات - تدعم الصفحة الرئيسية وصفحات الأحاديث
 * @param {Event} event - حدث الإرسال
 * @param {number} hadithId - رقم الحديث (0 للتعليقات العامة)
 * @param {string} commentsListId - معرف قائمة التعليقات
 */
async function handleCommentSubmit(event, hadithId, commentsListId) {
    event.preventDefault();
    
    // تحديد الحقول بناءً على hadithId
    let name, email, comment, submitBtn;
    
    if (hadithId === 0) {
        // التعليقات العامة (index.html)
        name = document.getElementById('generalName').value.trim();
        email = document.getElementById('generalEmail').value.trim();
        comment = document.getElementById('generalComment').value.trim();
        submitBtn = document.getElementById('generalSubmitBtn');
    } else {
        // تعليقات الأحاديث (detail.html)
        name = document.getElementById('hadithName').value.trim();
        email = document.getElementById('hadithEmail').value.trim();
        comment = document.getElementById('hadithComment').value.trim();
        submitBtn = document.getElementById('hadithSubmitBtn');
    }

    if (!submitBtn) {
        submitBtn = event.target.querySelector('button[type="submit"]');
    }

    const originalBtnContent = submitBtn.innerHTML;

    // التحقق من البيانات
    if (!name || !email || !comment) {
        toastManager.show('الرجاء ملء جميع الحقول', 'warning');
        return;
    }

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="material-icons-outlined">hourglass_empty</span> جارٍ الإرسال...';

        // اختيار الـ endpoint الصحيح
        const endpoint = hadithId === 0 ? '/api/general-comments' : '/api/comments';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                hadith_id: hadithId,
                name: name,
                email: email,
                comment: comment
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            const message = hadithId === 0 
                ? '✨ شكراً لمشاركتك! تم نشر تأملك بنجاح'
                : '✨ تم إضافة تأملك بنجاح! جزاك الله خيراً';
            
            toastManager.show(message, 'success', 4000);
            
            // مسح النموذج
            if (hadithId === 0) {
                document.getElementById('generalName').value = '';
                document.getElementById('generalEmail').value = '';
                document.getElementById('generalComment').value = '';
            } else {
                document.getElementById('hadithName').value = '';
                document.getElementById('hadithEmail').value = '';
                document.getElementById('hadithComment').value = '';
            }
            
            // إعادة تحميل التعليقات
            await loadComments(hadithId, commentsListId);
            
            // التمرير إلى قسم التعليقات
            const commentsList = document.getElementById(commentsListId);
            if (commentsList) {
                commentsList.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        } else {
            toastManager.show(result.error || 'حدث خطأ في إضافة التعليق', 'error');
        }
    } catch (error) {
        console.error('Error submitting comment:', error);
        toastManager.show('حدث خطأ في الاتصال. تأكد من اتصالك بالإنترنت', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnContent;
    }
}
```

#### إضافة الـ CSS المطلوب في detail.html

أضف هذا في `<style>` في detail.html (بعد السطر 240):

```css
/* Comments Section - نفس التنسيق من index.html */
.comments-section {
    max-width: 900px;
    margin: clamp(32px, 8vw, 64px) auto 0;
}

.section-header {
    text-align: center;
    margin-bottom: clamp(32px, 8vw, 48px);
}

.section-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: clamp(48px, 12vw, 64px);
    height: clamp(48px, 12vw, 64px);
    background-color: var(--color-primary-soft);
    border-radius: var(--radius-lg);
    color: var(--color-primary);
    margin-bottom: clamp(12px, 3vw, 16px);
}

.section-title {
    font-size: clamp(24px, 6vw, 28px);
    font-weight: 700;
    color: var(--color-text-primary);
    margin-bottom: 8px;
}

.section-subtitle {
    font-size: clamp(13px, 3vw, 15px);
    color: var(--color-text-secondary);
}

/* Comment Form */
.comment-form {
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: clamp(20px, 5vw, 32px);
    margin-bottom: clamp(32px, 8vw, 48px);
}

.form-group {
    margin-bottom: 20px;
}

.form-label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: var(--color-text-primary);
    font-size: 14px;
}

.form-input,
.form-textarea {
    width: 100%;
    padding: 12px 16px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background-color: var(--color-bg-hover);
    color: var(--color-text-primary);
    font-family: var(--font-family);
    font-size: 14px;
    transition: all 0.3s ease;
}

.form-input:focus,
.form-textarea:focus {
    outline: none;
    border-color: var(--color-primary);
    background-color: var(--color-bg-card);
    box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.form-textarea {
    resize: vertical;
    min-height: 120px;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.form-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 20px;
}

.form-hint {
    font-size: 12px;
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Comments Grid */
.comments-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 48px;
}

.comment-card {
    background-color: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 20px;
    transition: all 0.3s ease;
}

.comment-card:hover {
    border-color: var(--color-primary);
    box-shadow: 0 4px 12px var(--color-shadow);
}

.comment-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.comment-author {
    font-weight: 600;
    color: var(--color-text-primary);
    display: flex;
    align-items: center;
    gap: 6px;
}

.comment-time {
    font-size: 12px;
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    gap: 4px;
}

.comment-text {
    font-size: 14px;
    color: var(--color-text-secondary);
    line-height: 1.8;
    word-wrap: break-word;
}

/* Responsive */
@media (max-width: 768px) {
    .form-row {
        grid-template-columns: 1fr;
    }
    
    .form-actions {
        flex-direction: column;
        gap: 12px;
    }
    
    .comments-grid {
        grid-template-columns: 1fr;
    }
}
```

#### تحديث JavaScript في detail.html (بعد السطر 750):

```javascript
// تحميل التعليقات عند فتح الصفحة
document.addEventListener('DOMContentLoaded', () => {
    updateSaveBtn();
    // تحميل التعليقات الخاصة بهذا الحديث
    loadComments(HADITH_ID, 'commentsContainer');
});
```

---

## 📋 ملخص سريع

### لإصلاح مشكلة الأحاديث:
1. ✅ استخدم دالة `load_hadiths()` المحسّنة
2. ✅ زر `/debug/hadiths` للتشخيص
3. ✅ تأكد من وجود `hadith.json` في المجلد الصحيح

### لاستخدام نفس form التعليقات:
1. ✅ حدّث `detail.html` بالنموذج الجديد
2. ✅ حدّث `handleCommentSubmit()` في `main.js`
3. ✅ أضف الـ CSS المطلوب
4. ✅ غيّر IDs: `comment-name` → `hadithName` إلخ

---

## 🧪 الاختبار

### اختبار الأحاديث:
```bash
# 1. تشغيل المشروع
python3 start.py

# 2. زيارة الصفحة الرئيسية
http://localhost:8000/

# 3. يجب أن ترى الأحاديث
# إذا لم تظهر، زر:
http://localhost:8000/debug/hadiths
```

### اختبار التعليقات:
```bash
# 1. افتح أي حديث
http://localhost:8000/hadith/1

# 2. املأ النموذج
# 3. اضغط "إرسال التأمل"
# 4. يجب أن ترى:
#    - رسالة نجاح
#    - التعليق يظهر في الأسفل
#    - النموذج يُمسح
```

---

**بالتوفيق! 🚀**
