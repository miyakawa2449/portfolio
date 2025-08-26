// Profile Page Animations and Interactions
(function() {
    'use strict';
    
    // スキルバーアニメーション
    const animateSkillBars = () => {
        const observeSkillBars = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const bars = entry.target.querySelectorAll('.profile-skill-progress-bar');
                    bars.forEach((bar, index) => {
                        setTimeout(() => {
                            const width = bar.dataset.width;
                            if (width) {
                                bar.style.width = width + '%';
                            }
                        }, index * 100);
                    });
                    observeSkillBars.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        
        // 初期化
        document.querySelectorAll('.profile-skill-progress-bar').forEach(bar => {
            bar.style.width = '0%';
        });
        
        // 観察開始
        document.querySelectorAll('.profile-skills-category').forEach(section => {
            observeSkillBars.observe(section);
        });
    };
    
    // フェードインアニメーション
    const setupFadeInAnimations = () => {
        const fadeElements = document.querySelectorAll('.profile-fade-in');
        
        if (fadeElements.length === 0) return;
        
        const fadeInObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    fadeInObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
        
        fadeElements.forEach(el => {
            fadeInObserver.observe(el);
        });
    };
    
    // スムーズスクロール
    const setupSmoothScroll = () => {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    };
    
    // プロフィール写真ホバーエフェクト
    const setupProfilePhotoEffect = () => {
        const profilePhoto = document.querySelector('.profile-photo');
        if (profilePhoto) {
            profilePhoto.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05) rotate(3deg)';
            });
            
            profilePhoto.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1) rotate(0deg)';
            });
        }
    };
    
    // タイムラインアニメーション
    const setupTimelineAnimation = () => {
        const timelineItems = document.querySelectorAll('.profile-timeline-item');
        
        if (timelineItems.length === 0) return;
        
        const timelineObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateX(0)';
                    }, index * 100);
                    timelineObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        
        timelineItems.forEach(item => {
            item.style.opacity = '0';
            item.style.transform = 'translateX(-20px)';
            item.style.transition = 'all 0.6s ease';
            timelineObserver.observe(item);
        });
    };
    
    // プロジェクトカードホバー効果
    const setupProjectCardEffects = () => {
        const projectCards = document.querySelectorAll('.profile-project-card');
        
        projectCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.querySelector('.card-img-top')?.classList.add('hover');
            });
            
            card.addEventListener('mouseleave', function() {
                this.querySelector('.card-img-top')?.classList.remove('hover');
            });
        });
    };
    
    // PDFダウンロードボタンの表示制御
    const setupPDFButton = () => {
        const pdfButton = document.querySelector('.profile-pdf-download');
        if (!pdfButton) return;
        
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > 300) {
                if (currentScroll > lastScroll) {
                    // スクロールダウン時は非表示
                    pdfButton.style.transform = 'translateX(100px)';
                } else {
                    // スクロールアップ時は表示
                    pdfButton.style.transform = 'translateX(0)';
                }
            }
            
            lastScroll = currentScroll;
        });
    };
    
    // 初期化
    document.addEventListener('DOMContentLoaded', () => {
        animateSkillBars();
        setupFadeInAnimations();
        setupSmoothScroll();
        setupProfilePhotoEffect();
        setupTimelineAnimation();
        setupProjectCardEffects();
        setupPDFButton();
    });
    
    // ウィンドウリサイズ時の再計算
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            // 必要に応じて再計算処理を追加
        }, 250);
    });
})();