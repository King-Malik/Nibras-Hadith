/**
 * ╔═══════════════════════════════════════════════════════════════╗
 * ║         HADITH APP - MAIN JAVASCRIPT FILE                     ║
 * ║         Supabase Style Interactions & Animations              ║
 * ╚═══════════════════════════════════════════════════════════════╝
 */

// ============================================
// 🎨 THEME TOGGLE
// ============================================
const themeToggle = document.getElementById('theme-toggle');
const themeIcon = document.getElementById('theme-icon');

if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('hadith-app-theme', isDark ? 'dark' : 'light');
        updateThemeIcon(isDark);
    });
}

function updateThemeIcon(isDark) {
    if (themeIcon) {
        themeIcon.textContent = isDark ? 'light_mode' : 'dark_mode';
    }
}

// Initialize theme icon on page load
document.addEventListener('DOMContentLoaded', () => {
    const isDark = document.documentElement.classList.contains('dark');
    updateThemeIcon(isDark);
});

// ============================================
// 🔔 TOAST NOTIFICATION SYSTEM
// ============================================
class ToastManager {
    constructor() {
        this.container = this.createContainer();
    }

    createContainer() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            container.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 12px;
            `;
            document.body.appendChild(container);
        }
        return container;
    }

    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = `
            background-color: var(--color-bg-card);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-md);
            padding: 12px 20px;
            box-shadow: 0 4px 12px var(--color-shadow);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 250px;
            animation: slideIn 0.3s ease-out forwards;
            color: var(--color-text-primary);
            font-size: 14px;
            font-weight: 500;
        `;

        // Add icon based on type
        const icon = document.createElement('span');
        icon.className = 'material-icons-outlined';
        icon.style.fontSize = '18px';
        
        switch(type) {
            case 'success':
                icon.textContent = 'check_circle';
                icon.style.color = 'var(--color-primary)';
                break;
            case 'error':
                icon.textContent = 'error';
                icon.style.color = '#ef4444';
                break;
            case 'warning':
                icon.textContent = 'warning';
                icon.style.color = '#f59e0b';
                break;
            default:
                icon.textContent = 'info';
                icon.style.color = 'var(--color-primary)';
        }

        const text = document.createElement('span');
        text.textContent = message;

        toast.appendChild(icon);
        toast.appendChild(text);
        this.container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

const toastManager = new ToastManager();

// ============================================
// 🔍 SMOOTH SCROLL
// ============================================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });
});

// ============================================
// 🎬 INTERSECTION OBSERVER FOR ANIMATIONS
// ============================================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe all elements with fade-in class
document.querySelectorAll('.fade-in').forEach(el => {
    observer.observe(el);
});

// ============================================
// 📋 FORM HANDLING
// ============================================
// General comment form
const generalCommentForm = document.getElementById('generalCommentForm');
if (generalCommentForm) {
    generalCommentForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('generalName').value;
        const email = document.getElementById('generalEmail').value;
        const comment = document.getElementById('generalComment').value;
        const submitBtn = generalCommentForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'جارٍ الإرسال...';

            const response = await fetch('/api/general-comments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, email, comment })
            });

            if (response.ok) {
                toastManager.show('شكراً لمشاركتك! تم نشر تأملك', 'success');
                generalCommentForm.reset();
                
                // Reload comments
                loadGeneralComments();
            } else {
                toastManager.show('حدث خطأ في إضافة التعليق', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            toastManager.show('حدث خطأ في الاتصال', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

// ============================================
// 💬 LOAD COMMENTS
// ============================================
async function loadComments(hadithId, listContainerId = 'comments-list') {
    try {
        const response = await fetch(`/api/comments/${hadithId}`);
        const comments = await response.json();
        
        const commentsList = document.getElementById(listContainerId);
        if (commentsList) {
            commentsList.innerHTML = '';
            
            if (comments.length > 0) {
                comments.forEach((comment, index) => {
                    const commentEl = document.createElement('div');
                    commentEl.className = 'comment-card'; // استخدم نفس الكلاس الموجود في الـ CSS
                    commentEl.style.animationDelay = `${(index * 0.1)}s`;
                    commentEl.style.opacity = '1'; // للتأكد من ظهورها
                    commentEl.innerHTML = `
                        <div class="comment-header">
                            <span class="comment-author">${comment.name}</span>
                            <span class="comment-time">${comment.created_at}</span>
                        </div>
                        <p class="comment-text">${comment.comment}</p>
                    `;
                    commentsList.appendChild(commentEl);
                });
            } else {
                commentsList.innerHTML = '<div class="no-comments"><p>لا توجد تعليقات بعد. كن أول من يشارك تأمله!</p></div>';
            }
        }
    } catch (error) {
        console.error('Error loading comments:', error);
    }
}


async function loadGeneralComments(containerId = 'commentsContainer') {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const response = await fetch('/api/general-comments');
        const comments = await response.json();
        
        container.innerHTML = ''; // مسح جملة "جاري التحميل"

        if (comments.length > 0) {
            comments.forEach((comment, index) => {
                const card = document.createElement('div');
                card.className = 'comment-card fade-in';
                card.style.animationDelay = `${index * 0.1}s`;
                card.innerHTML = `
                    <div class="comment-header">
                        <span class="comment-author">${comment.name}</span>
                        <span class="comment-time">${comment.created_at}</span>
                    </div>
                    <p class="comment-text">${comment.comment}</p>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = '<div class="no-comments"><p>لا توجد تعليقات بعد.</p></div>';
        }
    } catch (error) {
        console.error('Error:', error);
        container.innerHTML = '<p>تعذر تحميل التعليقات حالياً.</p>';
    }
}


// Load comments on page load
document.addEventListener('DOMContentLoaded', () => {
    const commentsList = document.getElementById('comments-list');
    if (commentsList) {
        const hadithId = commentsList.dataset.hadithId;
        loadComments(hadithId);
    }

    const commentsContainer = document.getElementById('commentsContainer');
    if (commentsContainer) {
        loadGeneralComments();
    }
});

// ============================================
// 📤 SHARE FUNCTIONALITY
// ============================================
document.querySelectorAll('.share-btn').forEach(btn => {
    btn.addEventListener('click', async function() {
        const hadithId = this.dataset.hadithId;
        const hadithTitle = this.dataset.hadithTitle;
        const shareText = `${hadithTitle} - الأربعون النووية`;
        const shareUrl = `${window.location.origin}/hadith/${hadithId}`;

        if (navigator.share) {
            try {
                await navigator.share({
                    title: shareText,
                    url: shareUrl
                });
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Error sharing:', error);
                }
            }
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(shareUrl).then(() => {
                toastManager.show('تم نسخ الرابط إلى الحافظة', 'success');
            }).catch(() => {
                toastManager.show('فشل نسخ الرابط', 'error');
            });
        }
    });
});

// ============================================
// 📋 COPY TO CLIPBOARD
// ============================================
document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', function() {
        const text = this.dataset.copy;
        navigator.clipboard.writeText(text).then(() => {
            toastManager.show('تم نسخ النص بنجاح', 'success');
        }).catch(() => {
            toastManager.show('فشل نسخ النص', 'error');
        });
    });
});

// ============================================
// 🔗 SHARE WITH WEB SHARE API
// ============================================
document.querySelectorAll('[data-share]').forEach(btn => {
    btn.addEventListener('click', async function() {
        const url = this.dataset.shareUrl;
        const title = this.dataset.shareTitle;

        if (navigator.share) {
            try {
                await navigator.share({
                    title: title,
                    url: url
                });
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Error sharing:', error);
                }
            }
        } else {
            navigator.clipboard.writeText(url).then(() => {
                toastManager.show('تم نسخ الرابط إلى الحافظة', 'success');
            }).catch(() => {
                toastManager.show('فشل نسخ الرابط', 'error');
            });
        }
    });
});

// ============================================
// 🎯 BUTTON INTERACTIONS
// ============================================
document.querySelectorAll('button, a.btn, input[type="submit"]').forEach(btn => {
    btn.addEventListener('mousedown', function() {
        this.style.transform = 'scale(0.98)';
    });

    btn.addEventListener('mouseup', function() {
        this.style.transform = 'scale(1)';
    });

    btn.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
    });
});

// ============================================
// ⌨️ KEYBOARD SHORTCUTS
// ============================================
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Escape to close modals (if any)
    if (e.key === 'Escape') {
        // Add modal closing logic here
    }
});

// ============================================
// 🌐 NETWORK STATUS
// ============================================
window.addEventListener('online', () => {
    toastManager.show('تم استعادة الاتصال بالإنترنت', 'success');
});

window.addEventListener('offline', () => {
    toastManager.show('فقدت الاتصال بالإنترنت', 'warning');
});

// ============================================
// 📱 RESPONSIVE BEHAVIOR
// ============================================
const handleResponsive = () => {
    const isMobile = window.innerWidth < 768;
    
    // Adjust behavior based on screen size
    document.querySelectorAll('[data-mobile-hidden]').forEach(el => {
        el.style.display = isMobile ? 'none' : 'block';
    });
};

window.addEventListener('resize', handleResponsive);
handleResponsive();

// ============================================
// 🎬 CUSTOM ANIMATIONS
// ============================================
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .fade-in {
        animation: fadeIn 0.6s ease-out forwards;
    }

    .stagger-1 { animation-delay: 0.1s; }
    .stagger-2 { animation-delay: 0.2s; }
    .stagger-3 { animation-delay: 0.3s; }
`;
document.head.appendChild(style);

// ============================================
// 🔧 UTILITY FUNCTIONS
// ============================================

/**
 * Debounce function for optimizing frequent events
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format date to Arabic
 */
function formatDateArabic(date) {
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(date).toLocaleDateString('ar-SA', options);
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// ============================================
// 🚀 PERFORMANCE OPTIMIZATION
// ============================================

// Lazy load images
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

// ============================================
// 📊 ANALYTICS (Optional)
// ============================================
function trackEvent(eventName, eventData = {}) {
    // Add your analytics tracking here
    console.log('Event tracked:', eventName, eventData);
}

// Track page view
trackEvent('page_view', {
    page: window.location.pathname,
    timestamp: new Date().toISOString()
});

console.log('✅ Hadith App - Main JS loaded successfully');



// أضف هذه الدالة في Main.js أو داخل وسم script في Detail.html
async function handleCommentSubmit(event, hadithId, listContainerId) {
    event.preventDefault();
    const form = event.target;
    
    // جلب الزر
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    // جلب القيم (بذكاء لدعم Index و Detail)
    const nameVal = (document.getElementById('generalName') || document.getElementById('comment-name')).value;
    const emailVal = (document.getElementById('generalEmail') || document.getElementById('comment-email')).value;
    const commentVal = (document.getElementById('generalComment') || document.getElementById('comment-text')).value;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'جارٍ الإرسال...';

        // إرسال الطلب فقط دون تخزينه في متغير response
        await fetch('/api/comments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hadith_id: hadithId,
                name: nameVal,
                email: emailVal,
                comment: commentVal
            })
        });

        // تنفيذ النجاح مباشرة بمجرد انتهاء الطلب (تجاوزنا فحص ok أو status)
        form.reset();
        
        if (hadithId === 0) {
            loadGeneralComments(listContainerId);
        } else {
            loadComments(hadithId, listContainerId);
        }

        if (typeof toastManager !== 'undefined') {
            toastManager.show('تم النشر بنجاح', 'success');
        }

    } catch (error) {
        // لن يظهر الخطأ إلا إذا انقطع الإنترنت تماماً أو انهار السيرفر
        console.error('Network Error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}



// هذا السطر هو المسؤول عن جلب التعليقات عند إعادة تحميل الصفحة (Refresh)
document.addEventListener('DOMContentLoaded', () => {
    // لصفحة الحديث
    const commentsList = document.getElementById('comments-list');
    if (commentsList && commentsList.dataset.hadithId) {
        loadComments(commentsList.dataset.hadithId, 'comments-list');
    }

    // للصفحة الرئيسية
    if (document.getElementById('commentsContainer')) {
        loadGeneralComments('commentsContainer');
    }
});
