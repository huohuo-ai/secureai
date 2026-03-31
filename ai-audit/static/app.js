// AI 审计平台 - 前端逻辑

// 全局状态
const state = {
    currentTab: 'dashboard',
    currentPage: 1,
    pageSize: 20,
    config: null
};

// ==================== 工具函数 ====================

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', { 
        month: '2-digit', 
        day: '2-digit', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function formatDate(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleDateString('zh-CN');
}

function formatCost(cost) {
    if (!cost) return '$0';
    return '$' + parseFloat(cost).toFixed(2);
}

// ==================== API 请求 ====================

async function apiRequest(url, options = {}) {
    try {
        const res = await fetch(url, {
            ...options,
            credentials: 'include'
        });
        
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        
        return res.json();
    } catch (err) {
        console.error('API Error:', err);
        throw err;
    }
}

// ==================== Tab 切换 ====================

function switchTab(tabName) {
    state.currentTab = tabName;
    
    // 更新导航
    document.querySelectorAll('.header-nav a').forEach(a => {
        a.classList.toggle('active', a.dataset.tab === tabName);
    });
    
    // 更新内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabName);
    });
    
    // 加载数据
    if (tabName === 'dashboard') loadDashboard();
    if (tabName === 'logs') loadLogs();
    if (tabName === 'users') loadUsers();
    if (tabName === 'risk') loadRisk();
}

// ==================== 仪表盘 ====================

async function loadDashboard() {
    try {
        const data = await apiRequest('/api/stats/dashboard?days=30');
        
        // 更新统计卡片
        document.getElementById('totalCalls').textContent = formatNumber(data.total_calls);
        document.getElementById('totalCost').textContent = formatCost(data.total_cost);
        document.getElementById('uniqueUsers').textContent = formatNumber(data.unique_users);
        document.getElementById('totalTokens').textContent = formatNumber(data.total_tokens);
        
        // 风险分布
        renderRiskChart(data.risk_distribution);
        
        // 供应商分布
        renderProviderChart(data.provider_distribution);
        
        // 趋势图
        renderTrendChart(data.trend);
        
        // Top 标签
        renderTopTags(data.top_behavior_tags);
        
        // 部门排行
        renderDeptRanking(data.department_distribution);
        
    } catch (err) {
        console.error('Load dashboard failed:', err);
    }
}

function renderRiskChart(distribution) {
    const container = document.getElementById('riskChart');
    const levels = ['low', 'medium', 'high', 'critical'];
    const labels = { low: '低风险', medium: '中风险', high: '高风险', critical: '严重' };
    const colors = { low: '#52c41a', medium: '#faad14', high: '#fa8c16', critical: '#f5222d' };
    
    let html = '<div class="risk-legend">';
    let total = Object.values(distribution).reduce((a, b) => a + b, 0);
    
    levels.forEach(level => {
        const count = distribution[level] || 0;
        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
        html += `
            <div class="risk-legend-item">
                <div class="risk-legend-dot" style="background: ${colors[level]}"></div>
                <span>${labels[level]}: ${formatNumber(count)} (${pct}%)</span>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

function renderProviderChart(distribution) {
    const container = document.getElementById('providerChart');
    if (!distribution || Object.keys(distribution).length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        return;
    }
    
    const sorted = Object.entries(distribution).sort((a, b) => b[1] - a[1]);
    const total = sorted.reduce((sum, [, count]) => sum + count, 0);
    
    let html = '';
    sorted.forEach(([provider, count]) => {
        const pct = ((count / total) * 100).toFixed(1);
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
                <span style="text-transform: uppercase; font-weight: 500;">${provider}</span>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 100px; height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden;">
                        <div style="width: ${pct}%; height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);"></div>
                    </div>
                    <span style="font-size: 13px; color: #666; min-width: 60px; text-align: right;">${formatNumber(count)}</span>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderTrendChart(trend) {
    const canvas = document.getElementById('trendChart');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    if (!trend || trend.length === 0) return;
    
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    const maxValue = Math.max(...trend.map(d => d.calls));
    const stepX = chartWidth / (trend.length - 1 || 1);
    
    // 网格
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + chartHeight * i / 5;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }
    
    // 折线
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    trend.forEach((point, index) => {
        const x = padding + index * stepX;
        const y = padding + chartHeight * (1 - point.calls / maxValue);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
    
    // 点
    ctx.fillStyle = '#667eea';
    trend.forEach((point, index) => {
        const x = padding + index * stepX;
        const y = padding + chartHeight * (1 - point.calls / maxValue);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
    });
}

function renderTopTags(tags) {
    const container = document.getElementById('topTags');
    if (!tags || tags.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        return;
    }
    
    const colors = state.config?.behavior_tags || {};
    let html = '<div class="tag-cloud">';
    tags.forEach(({ tag, count }) => {
        const color = colors[tag] || '#999';
        html += `<span class="behavior-tag" style="background: ${color}">${tag} (${count})</span>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function renderDeptRanking(departments) {
    const container = document.getElementById('deptRanking');
    if (!departments || departments.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        return;
    }
    
    let html = '';
    departments.slice(0, 5).forEach((dept, index) => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: ${index < 3 ? '#faad14' : '#f0f0f0'}; color: ${index < 3 ? 'white' : '#666'}; border-radius: 50%; font-size: 12px; font-weight: 600;">${index + 1}</span>
                    <span>${dept.department}</span>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 500;">${formatNumber(dept.calls)}</div>
                    <div style="font-size: 12px; color: #999;">${dept.users}人 · ${formatCost(dept.cost)}</div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// ==================== 审计日志 ====================

async function loadLogs(page = 1) {
    state.currentPage = page;
    
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', state.pageSize);
    
    const riskLevel = document.getElementById('filterRisk').value;
    const department = document.getElementById('filterDept').value;
    const userId = document.getElementById('filterUser').value;
    const provider = document.getElementById('filterProvider').value;
    const keyword = document.getElementById('filterKeyword').value;
    
    if (riskLevel) params.set('risk_level', riskLevel);
    if (department) params.set('department', department);
    if (userId) params.set('user_id', userId);
    if (provider) params.set('provider', provider);
    if (keyword) params.set('keyword', keyword);
    
    try {
        const data = await apiRequest(`/api/audit/logs?${params}`);
        renderLogsTable(data.items);
        renderPagination(data.total, data.page, data.total_pages);
    } catch (err) {
        console.error('Load logs failed:', err);
    }
}

function renderLogsTable(logs) {
    const tbody = document.getElementById('logsTableBody');
    if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state">暂无数据</td></tr>';
        return;
    }
    
    const riskLabels = { low: '低风险', medium: '中风险', high: '高风险', critical: '严重' };
    const riskColors = { low: '#52c41a', medium: '#faad14', high: '#fa8c16', critical: '#f5222d' };
    const tagColors = state.config?.behavior_tags || {};
    
    tbody.innerHTML = logs.map(log => {
        const tags = (log.behavior_tags || []).map(tag => {
            const color = tagColors[tag] || '#999';
            return `<span class="behavior-tag" style="background: ${color}; font-size: 11px; padding: 2px 6px;">${tag}</span>`;
        }).join(' ');
        
        return `
            <tr>
                <td>${formatTime(log.timestamp)}</td>
                <td>${log.user_id}</td>
                <td>${log.department}</td>
                <td><span class="risk-badge" style="background: ${riskColors[log.risk_level]}">${riskLabels[log.risk_level]}</span></td>
                <td>${tags || '-'}</td>
                <td>${log.model}</td>
                <td>${formatNumber(log.tokens_input + log.tokens_output)}</td>
                <td>${formatCost(log.cost_usd)}</td>
            </tr>
        `;
    }).join('');
}

function renderPagination(total, current, totalPages) {
    const container = document.getElementById('pagination');
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    
    html += `<button onclick="loadLogs(${current - 1})" ${current === 1 ? 'disabled' : ''}>上一页</button>`;
    
    const start = Math.max(1, current - 2);
    const end = Math.min(totalPages, current + 2);
    
    for (let i = start; i <= end; i++) {
        html += `<button class="${i === current ? 'active' : ''}" onclick="loadLogs(${i})">${i}</button>`;
    }
    
    html += `<button onclick="loadLogs(${current + 1})" ${current === totalPages ? 'disabled' : ''}>下一页</button>`;
    html += `<span style="margin-left: 10px; color: #666; font-size: 13px;">共 ${total} 条</span>`;
    
    container.innerHTML = html;
}

// ==================== 用户分析 ====================

async function loadUsers() {
    try {
        const data = await apiRequest('/api/stats/users?days=30');
        renderUsersList(data);
    } catch (err) {
        console.error('Load users failed:', err);
    }
}

function renderUsersList(users) {
    const container = document.getElementById('usersList');
    if (!users || users.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        return;
    }
    
    let html = '';
    users.slice(0, 10).forEach((user, index) => {
        const riskColor = user.max_risk === 'critical' ? '#f5222d' : 
                          user.max_risk === 'high' ? '#fa8c16' : 
                          user.max_risk === 'medium' ? '#faad14' : '#52c41a';
        
        html += `
            <div class="user-rank-item">
                <div class="user-rank ${index < 3 ? 'top3' : ''}">${index + 1}</div>
                <div class="user-info">
                    <div class="user-name">${user.user_id}</div>
                    <div class="user-dept">${user.department}</div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: ${riskColor};"></span>
                </div>
                <div class="user-stats">
                    <div class="user-calls">${formatNumber(user.total_calls)} 次</div>
                    <div class="user-cost">${formatCost(user.total_cost)}</div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// ==================== 风险分析 ====================

async function loadRisk() {
    try {
        const events = await apiRequest('/api/stats/risk-events?limit=20');
        renderRiskEvents(events);
    } catch (err) {
        console.error('Load risk events failed:', err);
    }
}

function renderRiskEvents(events) {
    const container = document.getElementById('riskEvents');
    if (!events || events.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无风险事件</div>';
        return;
    }
    
    const riskColors = { low: '#52c41a', medium: '#faad14', high: '#fa8c16', critical: '#f5222d' };
    
    let html = '<div class="alert-list">';
    events.forEach(event => {
        html += `
            <div class="alert-item">
                <div class="alert-icon" style="background: ${riskColors[event.risk_level]}"></div>
                <div class="alert-content">
                    <div class="alert-title">${event.user_id} · ${event.department}</div>
                    <div class="alert-meta">${formatTime(event.timestamp)} · ${event.model} · ${(event.risk_reasons || []).join(', ')}</div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

// ==================== 初始化 ====================

async function init() {
    // 加载配置
    try {
        state.config = await apiRequest('/api/config');
    } catch (err) {
        console.error('Load config failed:', err);
    }
    
    // 绑定 Tab 切换
    document.querySelectorAll('.header-nav a').forEach(a => {
        a.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(a.dataset.tab);
        });
    });
    
    // 初始加载
    loadDashboard();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
