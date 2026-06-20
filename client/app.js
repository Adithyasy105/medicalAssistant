document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const messagesContainer = document.getElementById('messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const fileList = document.getElementById('file-list');
    const themeToggle = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

    // --- Theme Logic ---
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        htmlElement.classList.add('dark');
    }

    themeToggle.addEventListener('click', () => {
        htmlElement.classList.toggle('dark');
        localStorage.setItem('theme', htmlElement.classList.contains('dark') ? 'dark' : 'light');
    });

    // --- Helper Functions ---
    const scrollToBottom = () => {
        chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    };

    const addMessage = (role, data, title = null) => {
        const div = document.createElement('div');
        div.className = role === 'user' 
            ? 'flex justify-end gap-3 pl-12 md:pl-24' 
            : 'flex justify-start gap-3 pr-12 md:pr-24';

        if (role === 'user') {
            div.innerHTML = `
                <div class="bg-primary text-white p-4 rounded-xl rounded-tr-xs shadow-sm max-w-2xl">
                    <p class="text-sm">${data}</p>
                    <span class="text-[10px] opacity-70 mt-2 block text-right">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
            `;
        } else {
            let sourcesHtml = '';
            if (data.sources && data.sources.length > 0) {
                sourcesHtml = '<div class="mt-4 pt-3 border-t border-blue-200 dark:border-blue-900/50">';
                sourcesHtml += '<p class="text-[10px] font-bold text-slate-500 uppercase mb-2">Sources Used:</p>';
                data.sources.forEach(s => {
                    sourcesHtml += `
                        <div class="bg-white dark:bg-[#242c36] p-2 rounded border border-slate-200 dark:border-slate-700 mb-1 flex items-start gap-2">
                            <span class="material-symbols-outlined text-[14px] text-blue-500 mt-0.5">description</span>
                            <div class="overflow-hidden">
                                <p class="text-[11px] font-bold text-slate-700 dark:text-slate-300 truncate">${s.document} <span class="font-normal opacity-70">(Page ${s.page})</span></p>
                                <p class="text-[10px] text-slate-500 truncate w-full">${s.text}</p>
                            </div>
                        </div>
                    `;
                });
                sourcesHtml += '</div>';
            }

            let confidenceHtml = '';
            if (data.confidence !== undefined) {
                let color = data.confidence > 70 ? 'text-green-700 bg-green-100 dark:bg-green-900/40 dark:text-green-400' : 'text-orange-700 bg-orange-100 dark:bg-orange-900/40 dark:text-orange-400';
                confidenceHtml = `<span class="float-right text-[10px] font-bold px-2 py-0.5 rounded-full border border-current ${color}">Confidence: ${data.confidence}%</span>`;
            }

            const answerText = data.answer || data;

            div.innerHTML = `
                <div class="w-10 h-10 rounded-lg bg-primary-container dark:bg-primary/20 flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-on-primary-container dark:text-primary-fixed-dim">clinical_notes</span>
                </div>
                <div class="bg-[#E8F0F8] dark:bg-[#1a212a] border border-blue-100 dark:border-blue-900/30 p-5 rounded-xl rounded-tl-xs shadow-sm max-w-2xl w-full">
                    ${confidenceHtml}
                    ${title ? `<h5 class="text-primary dark:text-primary-fixed-dim font-bold text-sm mb-2">${title}</h5>` : ''}
                    <div class="prose dark:prose-invert text-on-surface dark:text-slate-300 text-sm leading-relaxed space-y-3">${marked.parse(answerText)}</div>
                    ${sourcesHtml}
                    <span class="text-[10px] text-secondary dark:text-slate-500 mt-3 block">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
            `;
        }
        
        messagesContainer.appendChild(div);
        scrollToBottom();
    };

    const showLoading = () => {
        const div = document.createElement('div');
        div.id = 'loading-indicator';
        div.className = 'flex justify-start gap-3 pr-12 md:pr-24';
        div.innerHTML = `
            <div class="w-10 h-10 rounded-lg bg-primary-container dark:bg-primary/20 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-on-primary-container dark:text-primary-fixed-dim">clinical_notes</span>
            </div>
            <div class="bg-surface-container-low dark:bg-slate-800/30 border border-slate-200 dark:border-slate-800 p-5 rounded-xl rounded-tl-xs shadow-sm flex items-center gap-4">
                <div class="flex gap-1.5">
                    <div class="w-2.5 h-2.5 rounded-full bg-primary loading-dot"></div>
                    <div class="w-2.5 h-2.5 rounded-full bg-primary loading-dot" style="animation-delay: 0.2s"></div>
                    <div class="w-2.5 h-2.5 rounded-full bg-primary loading-dot" style="animation-delay: 0.4s"></div>
                </div>
                <span class="text-sm text-secondary italic">Consulting MediBot...</span>
            </div>
        `;
        messagesContainer.appendChild(div);
        scrollToBottom();
    };

    const removeLoading = () => {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) indicator.remove();
    };

    // --- Chat Logic ---
    const handleChat = async () => {
        const text = userInput.value.trim();
        if (!text) return;

        userInput.value = '';
        addMessage('user', text);
        showLoading();

        try {
            const response = await fetch('/ask/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            });
            const data = await response.json();
            
            removeLoading();
            if (data.error) {
                addMessage('bot', { answer: `Error: ${data.error}` }, 'System Error');
            } else {
                addMessage('bot', data, 'MediBot Response');
            }
        } catch (error) {
            removeLoading();
            addMessage('bot', 'Failed to connect to server.', 'System Error');
        }
    };

    sendBtn.addEventListener('click', handleChat);
    userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleChat(); } });

    // --- File Upload Logic ---
    uploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async () => {
        const files = fileInput.files;
        if (files.length === 0) return;

        uploadStatus.textContent = 'Uploading...';
        uploadStatus.classList.remove('hidden');
        uploadStatus.className = 'mt-2 text-[10px] text-center text-primary';

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const response = await fetch('/upload_pdfs/', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (response.ok) {
                uploadStatus.textContent = '✅ Upload Success';
                uploadStatus.className = 'mt-2 text-[10px] text-center text-green-500';
                
                // Add to sidebar
                if (fileList.querySelector('p.italic')) fileList.innerHTML = '';
                Array.from(files).forEach(f => {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'group p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-primary/50 cursor-pointer bg-white dark:bg-[#111820]';
                    fileDiv.innerHTML = `
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
                                <span class="material-symbols-outlined text-red-500">picture_as_pdf</span>
                            </div>
                            <div class="overflow-hidden">
                                <p class="text-xs font-bold truncate">${f.name}</p>
                                <p class="text-[10px] text-secondary">${(f.size / 1024 / 1024).toFixed(1)} MB</p>
                            </div>
                        </div>
                    `;
                    fileList.prepend(fileDiv);
                });
            } else {
                uploadStatus.textContent = data.error ? `⚠️ ${data.error}` : '❌ Upload Failed';
                uploadStatus.className = 'mt-2 text-[10px] text-center text-red-500 font-bold break-words whitespace-normal';
            }
        } catch (error) {
            uploadStatus.textContent = '❌ Connection Error';
            uploadStatus.className = 'mt-2 text-[10px] text-center text-red-500 break-words whitespace-normal';
        }

        setTimeout(() => { if(!uploadStatus.textContent.includes('⚠️')) uploadStatus.classList.add('hidden'); }, 4000);
    });
});
