document.addEventListener('DOMContentLoaded', () => {

    // ===============================
    // 1. 状态定义
    // ===============================
    const UI_STATES = {
        INPUT: 'input',
        LOADING: 'loading',
        RESULT: 'result',
        VOICE: 'voice'
    };
    let currentState = UI_STATES.INPUT;

    // ===============================
    // 2. DOM 缓存
    // ===============================
    const dom = {
        inputSection: document.getElementById('input-section'),
        loadingSection: document.getElementById('loading-section'),
        resultSection: document.getElementById('result-section'),
        voiceSection: document.getElementById('voice-section'),

        userInput: document.getElementById('user-input'),
        slider: document.getElementById('slider'),
        indicators: document.getElementById('indicators'),
        navHint: document.querySelector('.nav-hint'),
        sysLogs: document.getElementById('sys-logs'),

        // 语音相关
        chatHistory: document.getElementById('chat-history'),
        chatPageStatus: document.getElementById('chat-page-status'),
        voiceStatus: document.getElementById('voice-status'),
        visualizerContainer: document.querySelector('.audio-visualizer-container')
    };

    let currentSlideIndex = 0;
    let slidesContent = [];
    let logInterval = null;
    let isRecording = false;

    // 聊天分页状态
    let chatData = [];
    let chatPage = 1;
    const CHAT_PAGE_SIZE = 4;

    // ===============================
    // 3. 状态管理
    // ===============================
    function renderState() {
        // 隐藏所有 Screen (配合 !important)
        [dom.inputSection, dom.loadingSection, dom.resultSection, dom.voiceSection].forEach(el => {
            if (el) {
                el.classList.remove('active');
                el.style.display = 'none';
            }
        });

        // 显式映射
        const activeMap = {
            [UI_STATES.INPUT]: dom.inputSection,
            [UI_STATES.LOADING]: dom.loadingSection,
            [UI_STATES.RESULT]: dom.resultSection,
            [UI_STATES.VOICE]: dom.voiceSection
        };

        const target = activeMap[currentState];
        if (target) {
            target.style.display = 'flex';
            void target.offsetWidth; // 强制重绘
            target.classList.add('active');
        }

        if (currentState === UI_STATES.VOICE) {
            dom.userInput.blur();
        }
    }

    function setState(state) {
        if (currentState === state) return;
        currentState = state;
        renderState();
    }

    // ===============================
    // 4. 特效逻辑
    // ===============================
    function startSystemLogs() {
        const logs = [
            "Initializing Neural Network...", "Connecting to Mainframe...",
            "Analyzing Semantics...", "Retrieving Materials Database...",
            "Calibrating 3D Models...", "Optimizing Geometry...",
            "Rendering Textures...", "Compiling Project Data...",
            "Verifying Integrity...", "System Ready."
        ];

        if (dom.sysLogs) {
            dom.sysLogs.innerHTML = '';
            let index = 0;
            if (logInterval) clearInterval(logInterval);

            logInterval = setInterval(() => {
                const p = document.createElement('span');
                p.className = 'log-line';
                p.textContent = logs[index % logs.length] + (Math.random() > 0.5 ? " [OK]" : " ...");
                dom.sysLogs.appendChild(p);
                if (dom.sysLogs.children.length > 3) dom.sysLogs.removeChild(dom.sysLogs.firstChild);
                index++;
            }, 300);
        }
    }

    function typeWriter(element, text, speed = 20) {
        if (!text || !element) return;
        element.textContent = '';
        element.classList.add('typing-active');
        let i = 0;

        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            } else {
                element.classList.remove('typing-active');
            }
        }

        type();
    }

    // ===============================
    // 5. 交互逻辑
    // ===============================
    dom.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && dom.userInput.value.trim()) {
            startGeneration(dom.userInput.value.trim());
        }
    });

    document.addEventListener('keydown', (e) => {
        // Result -> Voice
        if (currentState === UI_STATES.RESULT && (e.key === 'v' || e.key === 'V')) {
            setState(UI_STATES.VOICE);
            if (chatData.length === 0) {
                addChatMessage('system', '语音模块已加载。按住 [空格] 说话。');
            }
            return;
        }
        // Voice -> Result
        if (currentState === UI_STATES.VOICE && e.key === 'Escape') {
            setState(UI_STATES.RESULT);
            return;
        }
        // PTT
        if (currentState === UI_STATES.VOICE && e.key === ' ' && !isRecording) {
            e.preventDefault();
            startVoiceRecording();
        }
        // Voice Pagination
        if (currentState === UI_STATES.VOICE) {
            if (e.key === 'ArrowLeft') prevChatPage();
            if (e.key === 'ArrowRight') nextChatPage();
        }
        // Result Nav
        if (currentState === UI_STATES.RESULT) {
            if (e.key === 'Escape') reset();
            if (e.key === 'ArrowRight') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        }
    });

    document.addEventListener('keyup', (e) => {
        if (currentState === UI_STATES.VOICE && e.key === ' ' && isRecording) {
            stopVoiceRecording();
        }
    });

    dom.navHint.addEventListener('click', (e) => {
        const text = e.target.textContent;
        if (text.includes('ESC')) reset();
        if (text.includes('上')) prevSlide();
        if (text.includes('下')) nextSlide();
        if (text.includes('V')) {
            setState(UI_STATES.VOICE);
            if (chatData.length === 0) addChatMessage('system', '语音模块已加载。按住 [空格] 说话。');
        }
    });

    // ===============================
    // 6. 聊天分页逻辑
    // ===============================
    function renderChatList(animateLast = false) {
        const totalPages = Math.ceil(chatData.length / CHAT_PAGE_SIZE) || 1;
        if (chatPage > totalPages) chatPage = totalPages;
        if (chatPage < 1) chatPage = 1;

        dom.chatPageStatus.textContent = `PAGE ${chatPage}/${totalPages}`;
        dom.chatHistory.innerHTML = '';

        const start = (chatPage - 1) * CHAT_PAGE_SIZE;
        const end = start + CHAT_PAGE_SIZE;
        const pageMessages = chatData.slice(start, end);

        pageMessages.forEach((msg, index) => {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-msg ${msg.role}`;
            let senderName = msg.role === 'user' ? '[USER]' : '[AI-CORE]';
            if (msg.role === 'system') senderName = '[SYSTEM]';

            msgDiv.innerHTML = `<span class="sender">${senderName}:</span><span class="text"></span>`;
            dom.chatHistory.appendChild(msgDiv);

            const textSpan = msgDiv.querySelector('.text');
            // 只对当前页最后一条且需要动画的消息进行打字机
            if (animateLast && index === pageMessages.length - 1 && chatPage === totalPages) {
                typeWriter(textSpan, msg.text, 10);
            } else {
                textSpan.textContent = msg.text;
            }
        });
    }

    function addChatMessage(role, text) {
        chatData.push({role, text});
        const totalPages = Math.ceil(chatData.length / CHAT_PAGE_SIZE);
        chatPage = totalPages; // 自动跳到最新页
        renderChatList(true);
    }

    function prevChatPage() {
        if (chatPage > 1) {
            chatPage--;
            renderChatList(false);
        }
    }

    function nextChatPage() {
        const totalPages = Math.ceil(chatData.length / CHAT_PAGE_SIZE);
        if (chatPage < totalPages) {
            chatPage++;
            renderChatList(false);
        }
    }

    // ===============================
    // 7. 核心生成流程
    // ===============================
    function startGeneration(idea) {
        setState(UI_STATES.LOADING);
        startSystemLogs();

        fetch('/api/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({idea})
        })
            .then(res => res.json())
            .then(data => {
                clearInterval(logInterval);
                if (data.error) {
                    alert(data.error);
                    reset();
                } else {
                    buildSlides(data);
                    setState(UI_STATES.RESULT);
                }
            })
            .catch(() => {
                clearInterval(logInterval);
                // Mock Data
                const mockData = {
                    project_name: "火星探测全向车 (离线演示)",
                    target_user: "初中一年级",
                    difficulty: "⭐⭐⭐⭐",
                    core_idea: "基于麦克纳姆轮的全向移动底盘，模拟火星采样任务。",
                    materials: ["ESP32 主控", "麦克纳姆轮 x4", "N20电机 x4", "SG90舵机 x2"],
                    steps: ["组装底盘结构", "连接电机驱动", "烧录全向运动算法", "调试机械臂"],
                    learning_outcomes: ["麦轮运动学", "PID控制", "无线通讯"],
                    preview_image: "/static/2.png"
                };
                buildSlides(mockData);
                setState(UI_STATES.RESULT);
            });
    }

    function reset() {
        dom.userInput.value = '';
        currentSlideIndex = 0;
        slidesContent = [];
        chatData = [];
        chatPage = 1;
        if (logInterval) clearInterval(logInterval);
        setState(UI_STATES.INPUT);
        setTimeout(() => dom.userInput.focus(), 100);
    }

    // ===============================
    // 8. 幻灯片构建
    // ===============================
    function buildSlides(data) {
        slidesContent = [];

        // 1. Cover
        slidesContent.push({
            html: `
            <div class="slide-content cover-slide">
                <div class="slide-header">
                    <span class="step-tag">PROJECT OVERVIEW</span>
                    <h2 class="project-title">${data.project_name}</h2>
                </div>
                <div class="main-visual">
                    <img src="${data.preview_image}" alt="Preview">
                </div>
                <div class="core-info">
                    <div class="info-item">
                        <label>CORE IDEA</label>
                        <p id="type-core-idea"></p>
                    </div>
                    <div class="info-item compact">
                        <label>DIFFICULTY</label>
                        <p class="stars">${data.difficulty}</p>
                    </div>
                    <div class="info-item compact">
                        <label>TARGET</label>
                        <p>${data.target_user}</p>
                    </div>
                </div>
            </div>`,
            typingTargetSelector: '#type-core-idea',
            typingText: data.core_idea
        });

        // 2. Materials
        const matList = data.materials.map(m => `<li>${m}</li>`).join('');
        slidesContent.push({
            html: `
            <div class="slide-content list-slide">
                <div class="slide-header"><span class="step-tag">STEP 01</span><h2>准备清单 MATERIALS</h2></div>
                <ul class="material-list">${matList}</ul>
            </div>`
        });

        // 3. Steps
        const stepList = data.steps.map((s, i) => `
            <li class="step-item">
                <span class="step-num">${String(i + 1).padStart(2, '0')}</span>
                <span class="step-text">${s}</span>
            </li>`).join('');
        slidesContent.push({
            html: `
            <div class="slide-content list-slide">
                <div class="slide-header"><span class="step-tag">STEP 02</span><h2>制作流程 BUILD STEPS</h2></div>
                <div class="steps-container">${stepList}</div>
            </div>`
        });

        // 4. Outcomes
        const outList = data.learning_outcomes.map(o => `<li>${o}</li>`).join('');
        slidesContent.push({
            html: `
            <div class="slide-content list-slide">
                <div class="slide-header"><span class="step-tag">SUMMARY</span><h2>知识与收获 OUTCOMES</h2></div>
                <ul class="outcome-list">${outList}</ul>
            </div>`
        });

        renderSlide();
        updateIndicators();
    }

    function renderSlide() {
        if (!slidesContent[currentSlideIndex]) return;
        dom.slider.innerHTML = slidesContent[currentSlideIndex].html;

        const content = dom.slider.querySelector('.slide-content');
        if (content) {
            content.style.opacity = 0;
            requestAnimationFrame(() => content.style.opacity = 1);
        }

        const slideData = slidesContent[currentSlideIndex];
        if (slideData.typingTargetSelector && slideData.typingText) {
            const targetEl = dom.slider.querySelector(slideData.typingTargetSelector);
            if (targetEl) setTimeout(() => typeWriter(targetEl, slideData.typingText), 300);
        }
    }

    function updateIndicators() {
        dom.indicators.innerHTML = '';
        slidesContent.forEach((_, i) => {
            const dot = document.createElement('div');
            dot.className = `indicator ${i === currentSlideIndex ? 'active' : ''}`;
            dom.indicators.appendChild(dot);
        });
    }

    function nextSlide() {
        if (currentSlideIndex < slidesContent.length - 1) {
            currentSlideIndex++;
            renderSlide();
            updateIndicators();
        }
    }

    function prevSlide() {
        if (currentSlideIndex > 0) {
            currentSlideIndex--;
            renderSlide();
            updateIndicators();
        }
    }

    // ===============================
    // 9. 语音交互模拟
    // ===============================
    function startVoiceRecording() {
        isRecording = true;
        dom.voiceStatus.textContent = "LISTENING...";
        if (dom.visualizerContainer) dom.visualizerContainer.classList.add('speaking');
    }

    function stopVoiceRecording() {
        isRecording = false;
        dom.voiceStatus.textContent = "PROCESSING...";
        if (dom.visualizerContainer) dom.visualizerContainer.classList.remove('speaking');

        setTimeout(() => {
            addChatMessage('user', "这个部分能不能用更轻的材料？");
            dom.voiceStatus.textContent = "GENERATING...";

            setTimeout(() => {
                addChatMessage('ai', "建议将车架材料更换为碳纤维复合板，可减轻约 40% 重量。");
                dom.voiceStatus.textContent = "STANDBY";
            }, 1000);
        }, 600);
    }

    // 初始化
    renderState();
});