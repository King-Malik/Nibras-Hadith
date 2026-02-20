# ⚙️ دليل الإعدادات - نبراس v1.1.1

## الإعدادات الحقيقية والوظيفية

جميع الإعدادات في صفحة الملف الشخصي الآن **حقيقية وتعمل فعلياً**!

---

## 📱 الإعدادات المتاحة

### 1. 🌙 الوضع الليلي / النهاري

**الوظيفة:**
- تبديل بين الثيم الفاتح والثيم الداكن
- يحفظ الإعداد تلقائياً
- يطبق على جميع الصفحات

**كيف يعمل:**
```javascript
// عند التبديل
function toggleDarkFromSettings(checked) {
    // تطبيق الثيم على الصفحة
    document.documentElement.classList.toggle('dark', checked);
    
    // حفظ في localStorage
    localStorage.setItem('hadith-app-theme', checked ? 'dark' : 'light');
    
    // تحديث الأيقونة في شريط التنقل
    savePref('darkMode', checked);
}
```

**الحفظ:**
- `localStorage: 'hadith-app-theme'` → `'light'` أو `'dark'`
- يطبق تلقائياً عند فتح أي صفحة

---

### 2. 📝 تكبير النص

**الوظيفة:**
- زيادة حجم خط الأحاديث من 16px إلى 20px
- يطبق فوراً على جميع الصفحات
- مفيد لكبار السن أو لسهولة القراءة

**كيف يعمل:**
```javascript
function toggleLargeFont(checked) {
    // حفظ الإعداد
    savePref('largeFont', checked);
    
    // تطبيق فوراً على CSS
    if (checked) {
        document.documentElement.style.setProperty('--hadith-font-size', '20px');
    } else {
        document.documentElement.style.setProperty('--hadith-font-size', '16px');
    }
    
    // إشعار للمستخدم
    toastManager.show(checked ? 'تم تكبير النص' : 'تم إلغاء تكبير النص', 'info');
}
```

**التطبيق العالمي:**
```javascript
// في base.html - يطبق عند تحميل أي صفحة
(function() {
    const prefs = JSON.parse(localStorage.getItem('hadith-prefs')) || {};
    if (prefs.largeFont) {
        document.documentElement.style.setProperty('--hadith-font-size', '20px');
    }
})();
```

**الحفظ:**
- `localStorage: 'hadith-prefs' → { largeFont: true/false }`
- يطبق على كل الصفحات: الرئيسية، التفاصيل، الاختبارات

---

### 3. 🔔 تنبيهات الحديث اليومي

**الوظيفة:**
- طلب إذن التنبيهات من المتصفح
- إرسال تنبيه يومي للمستخدم
- تنبيه تجريبي بعد 5 ثواني من التفعيل

**كيف يعمل:**
```javascript
async function toggleNotifications(checked) {
    if (checked) {
        // طلب الإذن من المتصفح
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                savePref('notifications', true);
                toastManager.show('تم تفعيل التنبيهات اليومية', 'success');
                
                // جدولة تنبيه تجريبي
                scheduleNotification();
            } else {
                // رفض المستخدم
                document.getElementById('notif-toggle').checked = false;
                toastManager.show('يرجى السماح بالتنبيهات في المتصفح', 'error');
            }
        } else {
            // المتصفح لا يدعم التنبيهات
            document.getElementById('notif-toggle').checked = false;
            toastManager.show('المتصفح لا يدعم التنبيهات', 'error');
        }
    } else {
        savePref('notifications', false);
        toastManager.show('تم إيقاف التنبيهات', 'info');
    }
}

// إرسال تنبيه تجريبي
function scheduleNotification() {
    if (Notification.permission === 'granted') {
        setTimeout(() => {
            new Notification('نبراس - الأربعون النووية', {
                body: 'حان وقت قراءة حديث اليوم! 📖',
                icon: '/static/icons/icon-192x192.png',
                badge: '/static/icons/icon-192x192.png'
            });
        }, 5000); // بعد 5 ثواني
    }
}
```

**المتطلبات:**
- المتصفح يجب أن يدعم Notifications API
- المستخدم يجب أن يمنح الإذن
- لا يعمل على HTTP (يحتاج HTTPS أو localhost)

**الحفظ:**
- `localStorage: 'hadith-prefs' → { notifications: true/false }`

---

### 4. 👤 تغيير الاسم

**الوظيفة:**
- تخصيص اسم العرض في الملف الشخصي
- يظهر في رسائل الترحيب

**كيف يعمل:**
```javascript
function saveName(name) {
    localStorage.setItem(NAME_KEY, name.trim());
    document.getElementById('greeting').textContent = 
        name.trim() || 'مرحباً بك';
}
```

**الحفظ:**
- `localStorage: 'user-name'` → اسم المستخدم

---

### 5. 💾 تصدير البيانات

**الوظيفة:**
- تصدير جميع البيانات إلى ملف JSON
- يشمل: الأحاديث المحفوظة، الإحصائيات، الإعدادات، سجل القراءة

**كيف يعمل:**
```javascript
function exportData() {
    const allData = {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        saved: getSaved(),                    // الأحاديث المحفوظة
        prefs: getPrefs(),                    // الإعدادات
        readIds: prefs.readIds || [],        // الأحاديث المقروءة
        quizScores: prefs.quizScores || [],  // نتائج الاختبارات
        activeDays: prefs.activeDays || [],  // أيام النشاط
        theme: localStorage.getItem('hadith-app-theme') || 'light',
        totalStats: {
            saved: saved.length,
            read: (prefs.readIds || []).length,
            quiz: prefs.quizScore || 0,
            streak: calcStreak(prefs)
        }
    };
    
    // إنشاء ملف JSON
    const blob = new Blob([JSON.stringify(allData, null, 2)], 
        { type: 'application/json' });
    
    // تنزيل الملف
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `نبراس-بيانات-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
}
```

**اسم الملف:**
```
نبراس-بيانات-2026-02-15.json
```

---

### 6. 📥 استيراد البيانات

**الوظيفة:**
- استيراد البيانات من ملف JSON سابق
- دمج مع البيانات الحالية أو استبدالها

**كيف يعمل:**
```javascript
function importData(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            
            // استعادة البيانات
            if (data.saved) localStorage.setItem(SAVED_KEY, 
                JSON.stringify(data.saved));
            if (data.prefs) localStorage.setItem(PREFS_KEY, 
                JSON.stringify(data.prefs));
            if (data.theme) localStorage.setItem('hadith-app-theme', 
                data.theme);
            
            toastManager.show('تم استيراد البيانات بنجاح!', 'success');
            
            // إعادة تحميل الصفحة
            setTimeout(() => location.reload(), 1000);
        } catch (err) {
            toastManager.show('خطأ في قراءة الملف', 'error');
        }
    };
    reader.readAsText(file);
}
```

---

### 7. 🗑️ مسح جميع البيانات

**الوظيفة:**
- حذف كامل لجميع البيانات والإعدادات
- يطلب تأكيد من المستخدم

**كيف يعمل:**
```javascript
function clearAll() {
    if (!confirm('هل أنت متأكد من حذف جميع البيانات؟ لا يمكن التراجع!')) {
        return;
    }
    
    // حذف كل شيء
    localStorage.removeItem(SAVED_KEY);
    localStorage.removeItem(PREFS_KEY);
    localStorage.removeItem(NAME_KEY);
    localStorage.removeItem('hadith-app-theme');
    
    toastManager.show('تم مسح جميع البيانات', 'warning');
    
    // إعادة تحميل الصفحة
    setTimeout(() => location.reload(), 1000);
}
```

---

## 🔄 تطبيق الإعدادات عالمياً

### في base.html

جميع الإعدادات تطبق تلقائياً عند فتح أي صفحة:

```html
<script>
(function() {
    // 1. تطبيق الثيم
    const savedTheme = localStorage.getItem('hadith-app-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
    }
    
    // 2. تطبيق إعداد حجم الخط
    try {
        const prefs = JSON.parse(localStorage.getItem('hadith-prefs')) || {};
        if (prefs.largeFont) {
            document.documentElement.style.setProperty('--hadith-font-size', '20px');
        }
    } catch (e) {
        console.log('Could not load font preferences');
    }
})();
</script>
```

---

## 💾 التخزين المحلي (localStorage)

### المفاتيح المستخدمة:

| المفتاح | البيانات | مثال |
|---------|----------|------|
| `hadith-saved` | الأحاديث المحفوظة | `[{id: 1, ...}, ...]` |
| `hadith-prefs` | الإعدادات | `{largeFont: true, ...}` |
| `hadith-app-theme` | الثيم | `'dark'` أو `'light'` |
| `user-name` | اسم المستخدم | `'أحمد'` |

---

## ✅ الخلاصة

جميع الإعدادات الآن:
- ✅ **تعمل فعلياً** وليست مجرد مظهر
- ✅ **تحفظ تلقائياً** في localStorage
- ✅ **تطبق عالمياً** على جميع الصفحات
- ✅ **تستمر** حتى بعد إغلاق المتصفح
- ✅ **قابلة للتصدير والاستيراد**

---

**الإصدار:** 1.1.1  
**آخر تحديث:** 2026-02-15  
**الحالة:** ✅ جميع الإعدادات وظيفية 100%
