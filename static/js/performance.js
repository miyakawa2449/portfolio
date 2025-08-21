/**
 * Performance Optimization JavaScript
 * 画像遅延読み込み、パフォーマンス測定、GA4統合
 */

// ===== 画像遅延読み込み (Lazy Loading) =====
class LazyLoader {
    constructor() {
        this.imageObserver = null;
        this.init();
    }

    init() {
        // Intersection Observer がサポートされているかチェック
        if ('IntersectionObserver' in window) {
            this.imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        this.loadImage(img);
                        observer.unobserve(img);
                    }
                });
            }, {
                // 画像がビューポートに入る200px手前で読み込み開始
                rootMargin: '200px'
            });

            this.observeImages();
        } else {
            // フォールバック: 全ての画像を即座に読み込み
            this.loadAllImages();
        }
    }

    observeImages() {
        const lazyImages = document.querySelectorAll('.lazy-load');
        lazyImages.forEach(img => {
            this.imageObserver.observe(img);
        });
    }

    loadImage(img) {
        const src = img.dataset.src;
        const srcset = img.dataset.srcset;

        if (src) {
            img.src = src;
        }
        if (srcset) {
            img.srcset = srcset;
        }

        img.classList.add('loaded');
        
        // パフォーマンス測定
        img.addEventListener('load', () => {
            this.trackImageLoad(img);
        });

        img.addEventListener('error', () => {
            this.trackImageError(img);
        });
    }

    loadAllImages() {
        const lazyImages = document.querySelectorAll('.lazy-load');
        lazyImages.forEach(img => {
            this.loadImage(img);
        });
    }

    trackImageLoad(img) {
        // GA4での画像読み込み追跡
        if (typeof gtag !== 'undefined') {
            gtag('event', 'image_load', {
                'event_category': 'performance',
                'event_label': img.src,
                'value': 1
            });
        }
    }

    trackImageError(img) {
        // GA4での画像エラー追跡
        if (typeof gtag !== 'undefined') {
            gtag('event', 'image_error', {
                'event_category': 'performance',
                'event_label': img.dataset.src || img.src,
                'value': 1
            });
        }
    }
}

// ===== Core Web Vitals 測定 =====
class WebVitals {
    constructor() {
        this.vitals = {};
        this.init();
    }

    init() {
        // LCP (Largest Contentful Paint)
        this.measureLCP();
        
        // FID (First Input Delay)
        this.measureFID();
        
        // CLS (Cumulative Layout Shift)
        this.measureCLS();

        // カスタム指標
        this.measureCustomMetrics();
    }

    measureLCP() {
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                const lastEntry = entries[entries.length - 1];
                this.vitals.lcp = Math.round(lastEntry.startTime);
                this.sendToGA4('lcp', this.vitals.lcp);
            });

            observer.observe({ entryTypes: ['largest-contentful-paint'] });
        }
    }

    measureFID() {
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    this.vitals.fid = Math.round(entry.processingStart - entry.startTime);
                    this.sendToGA4('fid', this.vitals.fid);
                });
            });

            observer.observe({ entryTypes: ['first-input'] });
        }
    }

    measureCLS() {
        if ('PerformanceObserver' in window) {
            let clsValue = 0;
            const observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    if (!entry.hadRecentInput) {
                        clsValue += entry.value;
                    }
                });
                this.vitals.cls = Math.round(clsValue * 1000) / 1000;
                this.sendToGA4('cls', this.vitals.cls);
            });

            observer.observe({ entryTypes: ['layout-shift'] });
        }
    }

    measureCustomMetrics() {
        // DOM Content Loaded
        document.addEventListener('DOMContentLoaded', () => {
            const domContentLoaded = performance.now();
            this.sendToGA4('dom_content_loaded', Math.round(domContentLoaded));
        });

        // Page Load Complete
        window.addEventListener('load', () => {
            const pageLoadTime = performance.now();
            this.sendToGA4('page_load_complete', Math.round(pageLoadTime));
            
            // Navigation Timing API
            if (performance.navigation && performance.timing) {
                const timing = performance.timing;
                const navigation = performance.navigation;
                
                const dnsTime = timing.domainLookupEnd - timing.domainLookupStart;
                const connectTime = timing.connectEnd - timing.connectStart;
                const responseTime = timing.responseEnd - timing.requestStart;
                const domProcessingTime = timing.domComplete - timing.domLoading;
                
                this.sendToGA4('dns_time', dnsTime);
                this.sendToGA4('connect_time', connectTime);
                this.sendToGA4('response_time', responseTime);
                this.sendToGA4('dom_processing_time', domProcessingTime);
            }
        });
    }

    sendToGA4(metricName, value) {
        if (typeof gtag !== 'undefined') {
            gtag('event', 'web_vitals', {
                'event_category': 'performance',
                'event_label': metricName,
                'value': value,
                'custom_parameter_1': metricName
            });
        }
    }

    getVitals() {
        return this.vitals;
    }
}

// ===== ハンバーガーメニュー =====
class MobileMenu {
    constructor() {
        this.menuBtn = document.querySelector('.hamburger-btn');
        this.menu = document.querySelector('.navbar-menu');
        this.init();
    }

    init() {
        if (this.menuBtn && this.menu) {
            this.menuBtn.addEventListener('click', () => {
                this.toggle();
            });

            // メニュー外クリックで閉じる
            document.addEventListener('click', (e) => {
                if (!this.menuBtn.contains(e.target) && !this.menu.contains(e.target)) {
                    this.close();
                }
            });

            // ESCキーで閉じる
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.close();
                }
            });
        }
    }

    toggle() {
        const isActive = this.menuBtn.classList.toggle('active');
        this.menu.classList.toggle('active');
        
        // アクセシビリティ
        this.menuBtn.setAttribute('aria-expanded', isActive);
        
        // GA4でメニュー操作を追跡
        if (typeof gtag !== 'undefined') {
            gtag('event', 'mobile_menu_toggle', {
                'event_category': 'engagement',
                'event_label': isActive ? 'open' : 'close'
            });
        }
    }

    close() {
        this.menuBtn.classList.remove('active');
        this.menu.classList.remove('active');
        this.menuBtn.setAttribute('aria-expanded', 'false');
    }
}

// ===== 読了時間計算 =====
class ReadTimeCalculator {
    constructor() {
        this.wordsPerMinute = 200; // 日本語の平均読書速度
        this.init();
    }

    init() {
        const articles = document.querySelectorAll('[data-content]');
        articles.forEach(article => {
            const readTime = this.calculateReadTime(article);
            this.displayReadTime(article, readTime);
        });
    }

    calculateReadTime(element) {
        const content = element.textContent || element.innerText || '';
        // 日本語文字数を語数として計算（英語より密度が高いため係数調整）
        const words = content.length * 0.5;
        const minutes = Math.ceil(words / this.wordsPerMinute);
        return Math.max(1, minutes); // 最低1分
    }

    displayReadTime(element, minutes) {
        const readTimeElement = element.querySelector('.read-time');
        if (readTimeElement) {
            readTimeElement.innerHTML = `
                <i class="bi bi-clock"></i>
                <span>約${minutes}分</span>
            `;
        }
    }
}

// ===== スムーススクロール =====
class SmoothScroll {
    constructor() {
        this.init();
    }

    init() {
        // アンカーリンクのスムーススクロール
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // GA4でアンカークリックを追跡
                    if (typeof gtag !== 'undefined') {
                        gtag('event', 'anchor_click', {
                            'event_category': 'engagement',
                            'event_label': anchor.getAttribute('href')
                        });
                    }
                }
            });
        });
    }
}

// ===== パフォーマンス監視 =====
class PerformanceMonitor {
    constructor() {
        this.longTasks = [];
        this.init();
    }

    init() {
        // Long Task API
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    this.longTasks.push({
                        startTime: entry.startTime,
                        duration: entry.duration
                    });
                    
                    // 50ms以上のタスクをGA4に送信
                    if (entry.duration > 50) {
                        this.sendLongTaskToGA4(entry);
                    }
                });
            });

            observer.observe({ entryTypes: ['longtask'] });
        }

        // メモリ使用量監視
        this.monitorMemory();
    }

    sendLongTaskToGA4(entry) {
        if (typeof gtag !== 'undefined') {
            gtag('event', 'long_task', {
                'event_category': 'performance',
                'event_label': 'blocking_task',
                'value': Math.round(entry.duration)
            });
        }
    }

    monitorMemory() {
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                
                // メモリ使用量が過度な場合はGA4に送信
                const usedPercent = (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100;
                if (usedPercent > 80) {
                    if (typeof gtag !== 'undefined') {
                        gtag('event', 'high_memory_usage', {
                            'event_category': 'performance',
                            'value': Math.round(usedPercent)
                        });
                    }
                }
            }, 30000); // 30秒間隔
        }
    }

    getLongTasks() {
        return this.longTasks;
    }
}

// ===== 初期化 =====
document.addEventListener('DOMContentLoaded', () => {
    // 各機能を初期化
    const lazyLoader = new LazyLoader();
    const webVitals = new WebVitals();
    const mobileMenu = new MobileMenu();
    const readTimeCalculator = new ReadTimeCalculator();
    const smoothScroll = new SmoothScroll();
    const performanceMonitor = new PerformanceMonitor();

    // デバッグ用（開発環境でのみ）
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.debugPerformance = {
            lazyLoader,
            webVitals,
            performanceMonitor,
            getVitals: () => webVitals.getVitals(),
            getLongTasks: () => performanceMonitor.getLongTasks()
        };
    }

    // GA4でページビューを追跡（ページ読み込み完了後）
    window.addEventListener('load', () => {
        if (typeof gtag !== 'undefined') {
            gtag('event', 'page_view_complete', {
                'event_category': 'engagement',
                'page_load_time': Math.round(performance.now())
            });
        }
    });
});

// ===== Critical CSS 読み込み後の遅延CSS読み込み =====
function loadDeferredCSS() {
    const links = document.querySelectorAll('link[data-defer]');
    links.forEach(link => {
        link.rel = 'stylesheet';
        link.removeAttribute('data-defer');
    });
}

// Critical CSS読み込み後に遅延CSSを読み込む
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadDeferredCSS);
} else {
    loadDeferredCSS();
}