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
        clock: document.getElementById('clock'), // Added clock

        // 快照按钮
        snapshotBtn: document.getElementById('snapshot-btn'),

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
    let isThinking = false; // Added thinking state
    let resultPollTimer = null;
    let resultPollAttempts = 0;
    const RESULT_POLL_INTERVAL = 1500;
    const RESULT_POLL_MAX_ATTEMPTS = 80;
    let lastResetAt = 0;

    // 聊天分页状态
    let chatData = [];
    let chatPage = 1;
    const CHAT_PAGE_SIZE = 4;

    // ===============================
    // SSE 事件监听
    // ===============================
    console.log('初始化SSE连接到 /stream');
    const eventSource = new EventSource('/stream');

    eventSource.onopen = () => {
        console.log('SSE连接已建立');
    };

    eventSource.onerror = (error) => {
        console.error('SSE连接错误:', error);
        // SSE断开时启动兜底轮询，确保结果仍能加载
        if (currentState === UI_STATES.LOADING) {
            startResultPolling('sse_error');
        }
    };

    eventSource.onmessage = (e) => {
        try {
            const event = JSON.parse(e.data);
            handleServerEvent(event);
        } catch (err) {
            console.error('解析SSE消息失败:', err, e.data);
        }
    };

    // 处理服务器事件
    function handleServerEvent(event) {
        console.log('收到服务器事件:', event);

        // 忽略 reset 之前的旧事件，防止加载上一次结果
        if (lastResetAt && event && event.timestamp) {
            const eventTime = Date.parse(event.timestamp);
            if (!Number.isNaN(eventTime) && eventTime < lastResetAt) {
                console.log('忽略 reset 前事件');
                return;
            }
        }

        // 忽略keepalive消息
        if (event.type === 'keepalive') return;

        // ========== 拍照分析事件 ==========
        if (event.state === 'processing') {
            // AI正在处理，切换到加载状态
            console.log('AI开始处理...');
            setState(UI_STATES.LOADING);
            startSystemLogs();
            startResultPolling('processing');
        } else if (event.state === 'complete' && event.data) {
            // AI处理完成，显示结果
            console.log('AI处理完成，构建结果页面');
            clearInterval(logInterval);
            stopResultPolling();
            buildSlides(event.data);
            setState(UI_STATES.RESULT);
        } else if (event.state === 'error') {
            // 处理错误
            console.error('AI处理错误:', event.message);
            clearInterval(logInterval);
            stopResultPolling();
            alert('处理失败: ' + event.message);
            setState(UI_STATES.INPUT);
        }

        // ========== 语音交互事件 ==========
        else if (event.state === 'voice_recording') {
            // 录音中，不需要切换页面
            console.log('录音中:', event.message);
        }
        else if (event.state === 'voice_user') {
            // 用户语音已识别
            console.log('用户语音:', event.message);
            setThinking(true);
            addChatMessageWithSplit('user', event.message);
        }
        else if (event.state === 'voice_processing') {
            // AI正在思考
            console.log('AI思考中:', event.message);
            setThinking(true);
        }
        else if (event.state === 'voice_response') {
            // AI回复（自动拆分长消息并清理markdown）
            console.log('AI回复:', event.message);
            setThinking(false);
            try {
                addChatMessageWithSplit('ai', event.message);
            } catch (err) {
                console.error('Render AI response failed:', err);
            }
        }
        else if (event.state === 'voice_error') {
            // 语音错误
            console.error('语音错误:', event.message);
            setThinking(false);
            try {
                addChatMessageWithSplit('system', '错误: ' + event.message);
            } catch (err) {
                console.error('Render error message failed:', err);
            }
        }
    }

    // 初始化完成日志
    console.log('=== SparkBox UI 初始化完成 ===');
    console.log('DOM元素检查:', {
        snapshotBtn: dom.snapshotBtn ? '✓ 已找到' : '✗ 未找到',
        inputSection: dom.inputSection ? '✓' : '✗',
        loadingSection: dom.loadingSection ? '✓' : '✗',
        resultSection: dom.resultSection ? '✓' : '✗'
    });

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

        // 注释：user-input已删除
        /*
        if (currentState === UI_STATES.VOICE) {
            dom.userInput.blur();
        }
        */
    }

    function setState(state) {
        if (currentState === state) return;
        currentState = state;
        renderState();
    }

    function setThinking(thinking) {
        isThinking = thinking;
        if (dom.voiceStatus) {
            dom.voiceStatus.textContent = thinking ? "THINKING..." : "STANDBY";
        }
        if (dom.visualizerContainer) {
            if (thinking) {
                dom.visualizerContainer.classList.add('thinking');
            } else {
                dom.visualizerContainer.classList.remove('thinking');
            }
        }
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
    // 注释：user-input已从HTML中删除，不再需要此事件监听器
    /*
    dom.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && dom.userInput.value.trim()) {
            startGeneration(dom.userInput.value.trim());
        }
    });
    */

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
            if (isThinking) {
                console.log('Thinking... Recording disabled.');
                return;
            }
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

    // 拍照按钮点击事件
    if (dom.snapshotBtn) {
        dom.snapshotBtn.addEventListener('click', () => {
            console.log('拍照按钮被点击');

            // 立即切换到加载状态
            setState(UI_STATES.LOADING);
            startSystemLogs();

            // 调用API触发快照
            fetch('/api/snapshot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(res => res.json())
                .then(data => {
                    console.log('快照API响应:', data);
                    if (data.status === 'snapshot_triggered') {
                        // 成功触发，等待SSE事件推送结果
                        console.log('快照已触发，等待AI处理完成...');
                    } else if (data.error) {
                        console.error('快照失败:', data.error);
                        clearInterval(logInterval);
                        alert('拍照失败: ' + data.error);
                        setState(UI_STATES.INPUT);
                    }
                })
                .catch(err => {
                    console.error('快照请求失败:', err);
                    clearInterval(logInterval);
                    alert('拍照请求失败，请检查网络连接');
                    setState(UI_STATES.INPUT);
                });
        });
    } else {
        console.error('✗ 拍照按钮未找到！检查HTML中是否有 id="snapshot-btn"');
    }

    if (dom.snapshotBtn) {
        console.log('✓ 拍照按钮事件已绑定');
    }


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
        chatData.push({ role, text });
        const totalPages = Math.ceil(chatData.length / CHAT_PAGE_SIZE);
        chatPage = totalPages; // 自动跳到最新页
        renderChatList(true);
    }

    // 清理markdown符号
    function stripMarkdown(text) {
        if (!text) return '';
        return text
            // 移除标题符号 ### ## #
            .replace(/^#{1,6}\s*/gm, '')
            // 移除粗体 **text** 或 __text__
            .replace(/\*\*(.*?)\*\*/g, '$1')
            .replace(/__(.*?)__/g, '$1')
            // 移除斜体 *text* 或 _text_
            .replace(/\*(.*?)\*/g, '$1')
            .replace(/_(.*?)_/g, '$1')
            // 移除代码块 ```code```
            .replace(/```[\s\S]*?```/g, '')
            // 移除行内代码 `code`
            .replace(/`(.*?)`/g, '$1')
            // 移除列表符号 * - 1.
            .replace(/^\s*[\*\-]\s+/gm, '• ')
            .replace(/^\s*\d+\.\s+/gm, '')
            // 移除链接 [text](url)
            .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
            // 移除图片 ![alt](url)
            .replace(/!\[([^\]]*)\]\([^\)]+\)/g, '')
            // 清理多余空行
            .replace(/\n{3,}/g, '\n\n')
            .trim();
    }

    // 将长消息拆分成多条（简化可靠版本）
    function splitLongMessage(text, maxLength = 180) {
        const cleaned = stripMarkdown(text);
        if (cleaned.length <= maxLength) {
            return [cleaned];
        }

        const chunks = [];

        // 先按段落拆分（双换行）
        const paragraphs = cleaned.split(/\n\n+/).filter(p => p.trim());

        for (const para of paragraphs) {
            if (para.length <= maxLength) {
                // 段落短，直接作为一个chunk
                chunks.push(para.trim());
            } else {
                // 段落长，按句子拆分（使用兼容性更好的方法）
                const withMarkers = para.replace(/([。！？.!?；;])/g, '$1|||SPLIT|||');
                const sentences = withMarkers.split('|||SPLIT|||').filter(s => s.trim());
                let currentChunk = '';

                for (const sent of sentences) {
                    const trimmedSent = sent.trim();
                    if (!trimmedSent) continue;

                    if (currentChunk.length + trimmedSent.length + 1 <= maxLength) {
                        currentChunk += (currentChunk ? ' ' : '') + trimmedSent;
                    } else {
                        if (currentChunk) chunks.push(currentChunk);

                        // 如果单个句子超长，按字符强制拆分
                        if (trimmedSent.length > maxLength) {
                            for (let i = 0; i < trimmedSent.length; i += maxLength) {
                                chunks.push(trimmedSent.slice(i, i + maxLength));
                            }
                            currentChunk = '';
                        } else {
                            currentChunk = trimmedSent;
                        }
                    }
                }
                if (currentChunk) chunks.push(currentChunk);
            }
        }

        return chunks.length > 0 ? chunks : [cleaned.slice(0, maxLength) + '...'];
    }

    // 添加聊天消息（支持长消息拆分）
    function addChatMessageWithSplit(role, text) {
        if (role === 'ai') {
            // AI消息：清理markdown并拆分
            const chunks = splitLongMessage(text);
            chunks.forEach((chunk, index) => {
                chatData.push({
                    role,
                    text: chunks.length > 1 ? `[${index + 1}/${chunks.length}] ${chunk}` : chunk
                });
            });
        } else {
            // 用户/系统消息：直接添加
            chatData.push({ role, text: stripMarkdown(text) });
        }
        const totalPages = Math.ceil(chatData.length / CHAT_PAGE_SIZE);
        chatPage = totalPages;
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idea })
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
                    // 优先使用 AI 返回的 preview_url，如果没有就使用备用图
                    preview_url: "/static/2.png"
                };
                buildSlides(mockData);
                setState(UI_STATES.RESULT);
            });
    }

    function reset() {
        // dom.userInput.value = ''; // 注释：userInput已删除
        lastResetAt = Date.now();
        currentSlideIndex = 0;
        slidesContent = [];
        chatData = [];
        chatPage = 1;
        if (logInterval) clearInterval(logInterval);
        stopResultPolling();
        if (dom.slider) dom.slider.innerHTML = '';
        if (dom.indicators) dom.indicators.innerHTML = '';
        fetch('/api/reset', { method: 'POST' }).catch(() => {});
        setState(UI_STATES.INPUT);
        // setTimeout(() => dom.userInput.focus(), 100); // 注释：userInput已删除
    }

    // ===============================
    // 7.5 结果兜底轮询
    // ===============================
    function startResultPolling(reason) {
        if (resultPollTimer) return;
        resultPollAttempts = 0;
        console.log('启动结果轮询:', reason);
        resultPollTimer = setInterval(() => {
            resultPollAttempts++;
            fetch('/api/result')
                .then(res => res.json())
                .then(data => {
                    if (data && !data.error && (data.preview_url || data.solution || data.vision)) {
                        console.log('轮询拿到结果，更新页面');
                        clearInterval(logInterval);
                        stopResultPolling();
                        buildSlides(data);
                        setState(UI_STATES.RESULT);
                    }
                })
                .catch(() => {
                    // 忽略轮询错误，继续尝试
                });

            if (resultPollAttempts >= RESULT_POLL_MAX_ATTEMPTS) {
                console.warn('结果轮询超时，停止轮询');
                stopResultPolling();
            }
        }, RESULT_POLL_INTERVAL);
    }

    function stopResultPolling() {
        if (resultPollTimer) {
            clearInterval(resultPollTimer);
            resultPollTimer = null;
        }
    }

    // ===============================
    // 8. 幻灯片构建
    // ===============================
    function buildSlides(data) {
        slidesContent = [];
        // 新结果到达时回到封面，确保预览图立即可见
        currentSlideIndex = 0;

        // 提取solution数据（后端返回的是嵌套结构）
        const solution = data.solution || data;
        // 添加时间戳参数强制刷新图片，避免缓存问题
        const timestamp = Date.now();
        let previewBase = data.preview_url || solution.preview_url || data.preview_image || '/static/placeholder.png';
        const preview = previewBase.includes('?') ? `${previewBase}&_t=${timestamp}` : `${previewBase}?_t=${timestamp}`;

        // 1. Cover
        slidesContent.push({
            html: `
            <div class="slide-content cover-slide">
                <div class="slide-header">
                    <span class="step-tag">PROJECT OVERVIEW</span>
                    <h2 class="project-title">${solution.project_name || data.project_name || 'Unknown'}</h2>
                </div>
                <div class="main-visual">
                    <img src="${preview}" alt="Preview">
                </div>
                <div class="core-info">
                    <div class="info-item">
                        <label>CORE IDEA</label>
                        <p id="type-core-idea"></p>
                    </div>
                    <div class="info-item compact">
                        <label>DIFFICULTY</label>
                        <p class="stars">${solution.difficulty || data.difficulty || '⭐⭐⭐'}</p>
                    </div>
                </div>
            </div>`,
            typingTargetSelector: '#type-core-idea',
            typingText: solution.core_idea || data.core_idea || ''
        });

        // 2. Materials
        const materials = solution.materials || data.materials || [];
        const matList = materials.map(m => `<li>${m}</li>`).join('');
        slidesContent.push({
            html: `
            <div class="slide-content list-slide">
                <div class="slide-header"><span class="step-tag">STEP 01</span><h2>准备清单 MATERIALS</h2></div>
                <ul class="material-list">${matList}</ul>
            </div>`
        });

        // 3. Steps
        const steps = solution.steps || data.steps || [];
        const stepList = steps.map((s, i) => `
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
        const outcomes = solution.learning_outcomes || data.learning_outcomes || [];
        const outList = outcomes.map(o => `<li>${o}</li>`).join('');
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
    // 9. 语音交互
    // ===============================
    function startVoiceRecording() {
        console.log('开始录音...');
        isRecording = true;
        dom.voiceStatus.textContent = "LISTENING...";
        if (dom.visualizerContainer) dom.visualizerContainer.classList.add('speaking');

        // 调用后端API开始录音
        fetch('/api/voice/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(res => res.json())
            .then(data => {
                console.log('录音API响应:', data);
                if (data.error) {
                    console.error('录音失败:', data.error);
                    dom.voiceStatus.textContent = "ERROR";
                    isRecording = false;
                    if (dom.visualizerContainer) dom.visualizerContainer.classList.remove('speaking');
                }
            })
            .catch(err => {
                console.error('录音请求失败:', err);
                dom.voiceStatus.textContent = "ERROR";
                isRecording = false;
                if (dom.visualizerContainer) dom.visualizerContainer.classList.remove('speaking');
            });
    }

    function stopVoiceRecording() {
        console.log('停止录音...');
        isRecording = false;
        dom.voiceStatus.textContent = "PROCESSING...";
        if (dom.visualizerContainer) dom.visualizerContainer.classList.remove('speaking');

        // 调用后端API停止录音并转录
        fetch('/api/voice/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(res => res.json())
            .then(data => {
                console.log('停止录音API响应:', data);
                if (data.error) {
                    console.error('停止录音失败:', data.error);
                    dom.voiceStatus.textContent = "STANDBY";
                }
                // 结果会通过SSE事件推送
            })
            .catch(err => {
                console.error('停止录音请求失败:', err);
                dom.voiceStatus.textContent = "STANDBY";
            });
    }

    // ===============================
    // 10. Clock
    // ===============================
    function updateClock() {
        if (!dom.clock) return;
        const now = new Date();
        dom.clock.textContent = now.toLocaleTimeString('zh-CN', { hour12: false });
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 初始化
    renderState();
});