/* filepath: static/js/rdash-admin.js */
/* RDash Admin JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // サイドバートグル機能
    const pageWrapper = document.getElementById('page-wrapper');
    const mainMenuToggle = document.getElementById('main-menu-toggle');
    
    // メニュートグルクリック
    if (mainMenuToggle) {
        mainMenuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            pageWrapper.classList.toggle('toggled');
            
            // アイコンの回転
            const icon = this.querySelector('i');
            if (pageWrapper.classList.contains('toggled')) {
                icon.classList.remove('fa-angle-double-left');
                icon.classList.add('fa-angle-double-right');
            } else {
                icon.classList.remove('fa-angle-double-right');
                icon.classList.add('fa-angle-double-left');
            }
        });
    }
    
    // サブメニュートグル
    const submenuToggles = document.querySelectorAll('.has-submenu');
    submenuToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            
            const submenu = this.nextElementSibling;
            const arrow = this.querySelector('.arrow');
            
            // 他のサブメニューを閉じる
            submenuToggles.forEach(function(otherToggle) {
                if (otherToggle !== toggle) {
                    const otherSubmenu = otherToggle.nextElementSibling;
                    const otherArrow = otherToggle.querySelector('.arrow');
                    if (otherSubmenu) {
                        otherSubmenu.classList.remove('show');
                        otherToggle.classList.remove('active');
                        if (otherArrow) {
                            otherArrow.style.transform = 'translateY(-50%)';
                        }
                    }
                }
            });
            
            // 現在のサブメニューをトグル
            if (submenu) {
                submenu.classList.toggle('show');
                this.classList.toggle('active');
                
                if (arrow) {
                    if (submenu.classList.contains('show')) {
                        arrow.style.transform = 'translateY(-50%) rotate(90deg)';
                    } else {
                        arrow.style.transform = 'translateY(-50%)';
                    }
                }
            }
        });
    });
    
    // モバイルでのサイドバー自動閉じ
    if (window.innerWidth <= 768) {
        const sidebarLinks = document.querySelectorAll('.sidebar a');
        sidebarLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                if (!this.classList.contains('has-submenu')) {
                    pageWrapper.classList.remove('toggled');
                }
            });
        });
    }
    
    // ウィンドウリサイズ対応
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            pageWrapper.classList.remove('toggled');
            const icon = mainMenuToggle.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-angle-double-right');
                icon.classList.add('fa-angle-double-left');
            }
        }
    });
    
    // アラートの自動非表示（フラッシュメッセージのみ対象）
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(function(alert) {
        if (!alert.querySelector('.btn-close')) {
            setTimeout(function() {
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.remove();
                }, 300);
            }, 5000);
        }
    });
    
    // 統計カードのアニメーション
    const statsNumbers = document.querySelectorAll('.stats-number[data-count]');
    statsNumbers.forEach(function(element) {
        const targetValue = parseInt(element.getAttribute('data-count'));
        animateNumber(element, 0, targetValue, 2000);
    });
    
    // 数字アニメーション関数
    function animateNumber(element, start, end, duration) {
        const startTime = performance.now();
        
        function updateNumber(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const current = Math.floor(start + (end - start) * easeOutCubic(progress));
            element.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(updateNumber);
            }
        }
        
        requestAnimationFrame(updateNumber);
    }
    
    // イージング関数
    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }
    
    // テーブルソート機能（オプション）
    const sortableTables = document.querySelectorAll('.sortable');
    sortableTables.forEach(function(table) {
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(function(header) {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                sortTable(table, this.getAttribute('data-sort'));
            });
        });
    });
    
    // テーブルソート関数
    function sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = parseInt(column);
        
        rows.sort(function(a, b) {
            const aText = a.cells[columnIndex].textContent.trim();
            const bText = b.cells[columnIndex].textContent.trim();
            
            // 数値の場合
            if (!isNaN(aText) && !isNaN(bText)) {
                return parseFloat(aText) - parseFloat(bText);
            }
            
            // 文字列の場合
            return aText.localeCompare(bText);
        });
        
        // ソート結果をテーブルに反映
        rows.forEach(function(row) {
            tbody.appendChild(row);
        });
    }
    
    // フォームバリデーション
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('必須項目を入力してください。');
            }
        });
    });
});

// グローバル関数
window.rdashAdmin = {
    // サイドバーを開く
    openSidebar: function() {
        document.getElementById('page-wrapper').classList.remove('toggled');
    },
    
    // サイドバーを閉じる
    closeSidebar: function() {
        document.getElementById('page-wrapper').classList.add('toggled');
    },
    
    // サイドバーをトグル
    toggleSidebar: function() {
        document.getElementById('page-wrapper').classList.toggle('toggled');
    },
    
    // 通知を表示
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            ${message}
        `;
        
        const container = document.querySelector('.flash-messages') || document.querySelector('.page-content');
        if (container) {
            container.insertBefore(notification, container.firstChild);
            
            // 自動削除
            setTimeout(function() {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 5000);
        }
    }
};