document.addEventListener('DOMContentLoaded', () => {
    // 状态管理
    const state = {
        screen: 'input', // input, loading, result
        data: null,
        currentPage: 0,
        totalPages: 0
    };

    // DOM 元素
    const inputSection = document.getElementById('input-section');
    const loadingSection = document.getElementById('loading-section');
    const resultSection = document.getElementById('result-section');
    const userInput = document.getElementById('user-input');
    const slider = document.getElementById('slider');
    const indicators = document.getElementById('indicators');

    // 时钟
    setInterval(() => {
        const now = new Date();
        document.getElementById('clock').innerText = now.toLocaleTimeString();
    }, 1000);

    // 全局按键监听
    document.addEventListener('keydown', (e) => {
        if (state.screen === 'input') {
            if (e.key === 'Enter') handleSubmit();
        } else if (state.screen === 'result') {
            if (e.key === 'ArrowRight') changePage(1);
            if (e.key === 'ArrowLeft') changePage(-1);
            if (e.key === 'Escape') resetSystem();
        }
    });

    function handleSubmit() {
        const idea = userInput.value.trim();
        if (!idea) return;

        switchScreen('loading');

        // 调用后端 API
        fetch('/api/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idea: idea })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                switchScreen('input');
            } else {
                state.data = data;
                renderResult(data);
                switchScreen('result');
            }
        })
        .catch(err => {
            console.error(err);
            alert('网络错误');
            switchScreen('input');
        });
    }

    function switchScreen(screenName) {
        state.screen = screenName;
        inputSection.classList.remove('active');
        loadingSection.classList.remove('active');
        resultSection.classList.remove('active');

        if (screenName === 'input') {
            inputSection.classList.add('active');
            userInput.value = '';
            userInput.focus();
        } else if (screenName === 'loading') {
            loadingSection.classList.add('active');
        } else if (screenName === 'result') {
            resultSection.classList.add('active');
        }
    }

    function renderResult(data) {
        // 构建 4 个页面
        // Page 1: 概览 + 图片
        // Page 2: 材料清单
        // Page 3: 制作步骤
        // Page 4: 学习成果

        const pagesHtml = [
            // Page 1: Overview
            `
            <div class="slide-page split-layout active">
                <div class="left-panel">
                    <h3>PROJECT IDENTITY</h3>
                    <h2>${data.project_name}</h2>
                    <p style="font-size: 1.2rem; margin-top:20px; line-height:1.6">${data.core_idea}</p>
                    <div style="margin-top: 30px">
                        <span class="key-icon">难度: ${data.difficulty}</span>
                        <span class="key-icon">对象: ${data.target_user}</span>
                    </div>
                </div>
                <div class="right-panel">
                    <img src="${data.preview_image}" class="project-img" alt="Preview">
                </div>
            </div>
            `,
            // Page 2: Materials
            `
            <div class="slide-page" style="flex-direction: column; justify-content:center; align-items:flex-start">
                <h2>所需材料 / COMPONENTS</h2>
                <ul class="data-list" style="width: 100%">
                    ${data.materials.map(m => `<li>${m}</li>`).join('')}
                </ul>
            </div>
            `,
            // Page 3: Steps
            `
            <div class="slide-page" style="flex-direction: column; justify-content:center; align-items:flex-start">
                <h2>制作步骤 / ASSEMBLY PROTOCOL</h2>
                <ul class="data-list" style="width: 100%">
                    ${data.steps.map((s, i) => `<li>[STEP ${i+1}] ${s}</li>`).join('')}
                </ul>
            </div>
            `,
            // Page 4: Outcomes
            `
            <div class="slide-page" style="flex-direction: column; justify-content:center; align-items:center; text-align:center">
                <h2>学习成果 / KNOWLEDGE GAINED</h2>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; width:100%">
                     ${data.learning_outcomes.map(l => 
                         `<div style="border:1px solid var(--primary-color); padding:20px; font-size:1.5rem">${l}</div>`
                     ).join('')}
                </div>
            </div>
            `
        ];

        slider.innerHTML = pagesHtml.join('');

        // 渲染指示器
        state.totalPages = pagesHtml.length;
        state.currentPage = 0;
        updateIndicators();
    }

    function changePage(direction) {
        const newPage = state.currentPage + direction;
        if (newPage >= 0 && newPage < state.totalPages) {
            // 隐藏当前页
            slider.children[state.currentPage].classList.remove('active');
            // 显示新页
            state.currentPage = newPage;
            slider.children[state.currentPage].classList.add('active');
            updateIndicators();
        }
    }

    function updateIndicators() {
        indicators.innerHTML = '';
        for(let i=0; i<state.totalPages; i++) {
            const span = document.createElement('span');
            span.className = 'indicator ' + (i === state.currentPage ? 'active' : '');
            indicators.appendChild(span);
        }
    }

    function resetSystem() {
        switchScreen('input');
    }
});