document.addEventListener('DOMContentLoaded', () => {

    // ===============================
    // 状态定义
    // ===============================
    const UI_STATES = {
        INPUT: 'input',
        LOADING: 'loading',
        RESULT: 'result'
    };

    let currentState = UI_STATES.INPUT;

    // ===============================
    // DOM 缓存
    // ===============================
    const dom = {
        inputSection: document.getElementById('input-section'),
        loadingSection: document.getElementById('loading-section'),
        resultSection: document.getElementById('result-section'),
        userInput: document.getElementById('user-input'),
        slider: document.getElementById('slider'),
        indicators: document.getElementById('indicators'),
        navHint: document.querySelector('.nav-hint')
    };

    // ===============================
    // 幻灯片状态
    // ===============================
    let currentSlideIndex = 0;
    let slidesContent = [];

    // ===============================
    // 状态渲染器（核心）
    // ===============================
    function renderState() {
        const map = {
            [UI_STATES.INPUT]: dom.inputSection,
            [UI_STATES.LOADING]: dom.loadingSection,
            [UI_STATES.RESULT]: dom.resultSection
        };

        Object.values(map).forEach(section => {
            section.classList.remove('active');
            section.style.display = 'none';
        });

        const activeSection = map[currentState];
        activeSection.style.display = 'flex';

        requestAnimationFrame(() => {
            activeSection.classList.add('active');
        });
    }

    // ===============================
    // 状态切换器
    // ===============================
    function setState(state) {
        if (currentState === state) return;
        currentState = state;
        renderState();
    }

    // ===============================
    // 输入逻辑
    // ===============================
    dom.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && dom.userInput.value.trim()) {
            startGeneration(dom.userInput.value.trim());
        }
    });

    // ===============================
    // 全局按键
    // ===============================
    document.addEventListener('keydown', (e) => {
        if (currentState === UI_STATES.RESULT) {
            if (e.key === 'Escape') reset();
            if (e.key === 'ArrowRight') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        }
    });

    // ===============================
    // 底部按钮
    // ===============================
    dom.navHint.addEventListener('click', (e) => {
        const text = e.target.textContent;
        if (text.includes('ESC')) reset();
        if (text.includes('上一页')) prevSlide();
        if (text.includes('下一页')) nextSlide();
    });

    // ===============================
    // 核心流程
    // ===============================
    function startGeneration(idea) {
        setState(UI_STATES.LOADING);

        fetch('/api/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idea })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                reset();
            } else {
                buildSlides(data);
                setState(UI_STATES.RESULT);
            }
        })
        .catch(() => {
            alert('网络错误或超时');
            reset();
        });
    }

    function reset() {
        dom.userInput.value = '';
        currentSlideIndex = 0;
        slidesContent = [];
        setState(UI_STATES.INPUT);
        dom.userInput.focus();
    }

    // ===============================
    // 幻灯片构建
    // ===============================
    function buildSlides(data) {
        slidesContent = [];

        slidesContent.push(buildCoverSlide(data));
        slidesContent.push(buildMaterialsSlide(data));
        slidesContent.push(buildStepsSlide(data));
        slidesContent.push(buildOutcomesSlide(data));

        renderSlide();
        updateIndicators();
    }

    function buildCoverSlide(data) {
        return `
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
                    <p>${data.core_idea}</p>
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
        </div>`;
    }

    function buildMaterialsSlide(data) {
        const list = data.materials.map(m => `<li>${m}</li>`).join('');
        return `
        <div class="slide-content list-slide">
            <div class="slide-header">
                <span class="step-tag">STEP 01</span>
                <h2>准备清单 MATERIALS</h2>
            </div>
            <ul class="material-list">${list}</ul>
        </div>`;
    }

    function buildStepsSlide(data) {
        const list = data.steps.map((s, i) => `
            <li class="step-item">
                <span class="step-num">${String(i + 1).padStart(2, '0')}</span>
                <span class="step-text">${s}</span>
            </li>`).join('');

        return `
        <div class="slide-content list-slide">
            <div class="slide-header">
                <span class="step-tag">STEP 02</span>
                <h2>制作流程 BUILD STEPS</h2>
            </div>
            <div class="steps-container">${list}</div>
        </div>`;
    }

    function buildOutcomesSlide(data) {
        const list = data.learning_outcomes.map(o => `<li>${o}</li>`).join('');
        return `
        <div class="slide-content list-slide">
            <div class="slide-header">
                <span class="step-tag">SUMMARY</span>
                <h2>知识与收获 OUTCOMES</h2>
            </div>
            <ul class="outcome-list">${list}</ul>
        </div>`;
    }

    // ===============================
    // 幻灯片控制
    // ===============================
    function renderSlide() {
        dom.slider.innerHTML = slidesContent[currentSlideIndex];

        const content = dom.slider.querySelector('.slide-content');
        if (content) {
            content.style.opacity = 0;
            requestAnimationFrame(() => {
                content.style.opacity = 1;
            });
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
    // 初始化
    // ===============================
    renderState();
});
