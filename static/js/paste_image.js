/*
 * Attach clipboard image paste handler to a textarea or contenteditable element.
 * When user pastes an image, the image blob is uploaded via /api/upload_image
 * and an <img src="url"> tag is inserted at caret position.
 */
function attachImagePaste(element) {
    if (!element) return;
    // 防止重复添加事件监听器
    if (element.dataset.imagePasteAttached === 'true') return;
    element.dataset.imagePasteAttached = 'true';
    element.addEventListener('paste', async function (e) {
        if (!e.clipboardData) return;
        const items = Array.from(e.clipboardData.items || []);
        const imgItem = items.find(it => it.kind === 'file' && it.type.startsWith('image/'));
        if (!imgItem) return; // no image in clipboard
        const file = imgItem.getAsFile();
        if (!file) return;
        e.preventDefault();
        try {
            const formData = new FormData();
            formData.append('file', file, 'pasted.' + file.type.split('/')[1]);
            const resp = await fetch('/api/upload_image', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.url) {
                insertAtCursor(element, `<img src="${data.url}"/>`);
            } else {
                alert('图片上传失败');
            }
        } catch (err) {
            console.error(err);
            alert('图片上传异常');
        }
    });
}

function insertAtCursor(textarea, text) {
    // works for textarea & input
    if (document.activeElement !== textarea) textarea.focus();
    
    // 如果是图片标签，先移除所有现有的图片标签（只保留最后一张）
    if (text.includes('<img')) {
        // 移除所有现有的图片标签
        textarea.value = textarea.value.replace(/<img[^>]*>/g, '');
    }
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = textarea.value.substring(0, start);
    const after = textarea.value.substring(end);
    textarea.value = before + text + after;
    const newPos = before.length + text.length;
    textarea.setSelectionRange(newPos, newPos);
    
    // 更新字数统计
    updateCharCount(textarea);
}

// 更新字数统计
function updateCharCount(textarea) {
    const questionId = textarea.dataset.questionId;
    if (!questionId) return;
    
    // 计算纯文本字数（排除HTML标签）
    const textOnly = textarea.value.replace(/<[^>]*>/g, '');
    const charCount = textOnly.length;
    
    const countSpan = document.getElementById('charCount_' + questionId);
    if (countSpan) {
        countSpan.textContent = charCount;
        
        // 如果超过600字，显示警告颜色
        if (charCount >= 600) {
            countSpan.style.color = 'red';
            countSpan.style.fontWeight = 'bold';
        } else if (charCount >= 540) {
            countSpan.style.color = 'orange';
        } else {
            countSpan.style.color = '';
            countSpan.style.fontWeight = '';
        }
    }
}

// 初始化：等待 DOMReady
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('textarea.allow-img-paste').forEach(el => {
        attachImagePaste(el);
        
        // 添加输入事件监听，实时更新字数统计
        el.addEventListener('input', function() {
            updateCharCount(this);
        });
        
        // 初始化字数统计
        updateCharCount(el);
    });
    
    // 将函数暴露到全局，便于后续动态调用
    window.attachImagePaste = attachImagePaste;
    window.updateCharCount = updateCharCount;
}); 