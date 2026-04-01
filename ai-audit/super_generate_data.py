#!/usr/bin/env python3
"""
AI 审计平台 - 超级增强版演示数据生成器
生成超大规模、超真实的模拟数据
"""

import asyncio
import random
import string
import json
from datetime import datetime, timedelta
from uuid import uuid4
from database import init_db, insert_audit_logs
from risk_detector import detect_risk_level
from behavior_tagger import BehaviorTagger

# ============ 超大规模配置 ============

DEPARTMENTS = {
    '研发部': {
        'weight': 0.38,
        'users': ['张三', '李四', '王五', '赵六', '陈七', '刘八', '周九', '吴十', 
                 '郑十一', '孙十二', '钱十三', '朱十四', '秦十五', '尤十六'],
        'scenarios': ['code_review', 'debugging', 'architecture', 'learning']
    },
    '产品部': {
        'weight': 0.16,
        'users': ['产品经理小王', '产品经理小李', '产品总监老张', '需求分析师小刘', 
                 '用户研究员小赵', '数据产品经理小周', '策略产品经理小吴'],
        'scenarios': ['document_writing', 'data_analysis', 'user_research', 'competitive_analysis']
    },
    '市场部': {
        'weight': 0.14,
        'users': ['市场专员小美', '市场经理大力', '内容运营小陈', '活动策划小王', 
                 '品牌经理小周', 'SEO专员小郑', '投放专员小孙'],
        'scenarios': ['content_creation', 'marketing', 'creative', 'data_analysis']
    },
    '运营部': {
        'weight': 0.13,
        'users': ['数据运营小赵', '用户运营小钱', '活动运营小孙', '社区运营小李', 
                 '增长黑客小周', '内容运营小吴', '直播运营小郑'],
        'scenarios': ['data_analysis', 'user_operation', 'content_creation', 'automation']
    },
    '设计部': {
        'weight': 0.08,
        'users': ['UI设计师小丽', 'UX设计师小芳', '视觉设计师小明', '插画师小红', 
                 '动效设计师小刚', '品牌设计师小静'],
        'scenarios': ['creative', 'design_review', 'inspiration', 'documentation']
    },
    '财务部': {
        'weight': 0.05,
        'users': ['会计小周', '财务主管小吴', '审计小郑', '出纳小王', '财务分析师小冯'],
        'scenarios': ['data_analysis', 'reporting', 'automation', 'compliance']
    },
    '人事部': {
        'weight': 0.04,
        'users': ['HR小赵', '招聘专员小钱', 'HRBP小孙', '培训专员小李', '薪酬专员小周'],
        'scenarios': ['document_writing', 'interview', 'training', 'policy']
    },
    '法务部': {
        'weight': 0.02,
        'users': ['法务经理小陈', '合规专员小林'],
        'scenarios': ['compliance', 'contract_review', 'risk_assessment']
    }
}

PROVIDERS = {
    'openai': {
        'weight': 0.52,
        'models': [
            ('gpt-4', 0.25), ('gpt-4-turbo', 0.20), ('gpt-4o', 0.25),
            ('gpt-3.5-turbo', 0.25), ('gpt-3.5-turbo-16k', 0.05)
        ]
    },
    'claude': {
        'weight': 0.26,
        'models': [
            ('claude-3-opus', 0.20), ('claude-3-sonnet', 0.50), ('claude-3-haiku', 0.30)
        ]
    },
    'qwen': {
        'weight': 0.12,
        'models': [
            ('qwen-turbo', 0.45), ('qwen-plus', 0.35), ('qwen-max', 0.20)
        ]
    },
    'baidu': {
        'weight': 0.06,
        'models': [
            ('ernie-bot-4', 0.30), ('ernie-bot', 0.50), ('ernie-bot-turbo', 0.20)
        ]
    },
    'azure': {
        'weight': 0.04,
        'models': [
            ('gpt-4', 0.60), ('gpt-35-turbo', 0.40)
        ]
    }
}

# 超详细的场景模板库
SCENARIO_TEMPLATES = {
    # 代码审查场景
    'code_review': {
        'weight': 0.18,
        'templates': [
            {
                'type': 'performance',
                'prompts': [
                    '请帮我 review 这段 Python 代码的性能瓶颈：\n```python\n{code}\n```',
                    '这段 JavaScript 代码执行很慢，如何优化？\n```javascript\n{code}\n```',
                    'SQL 查询执行超时，帮我优化：\n```sql\n{sql}\n```',
                    '这段 Go 代码内存占用太高，如何改进？'
                ]
            },
            {
                'type': 'security',
                'prompts': [
                    '检查这段代码是否有 SQL 注入风险',
                    '这段登录逻辑有安全隐患吗？如何改进？',
                    '帮我审查 API 接口的权限控制',
                    '这个文件上传功能是否安全？'
                ]
            },
            {
                'type': 'refactor',
                'prompts': [
                    '将这个函数重构为使用策略模式',
                    '这段代码太长了，帮我拆分成多个函数',
                    '请用更优雅的写法重构这段代码',
                    '将这个类改为使用依赖注入'
                ]
            },
            {
                'type': 'test',
                'prompts': [
                    '为这段代码生成单元测试用例',
                    '帮我写集成测试覆盖这个 API',
                    '生成边界条件的测试数据',
                    '这个函数的测试覆盖率不够，帮我补充'
                ]
            }
        ],
        'code_snippets': [
            'def process_data(data):\n    result = []\n    for i in range(len(data)):\n        result.append(data[i] * 2)\n    return result',
            'async function fetchData() {\n    const res = await fetch(url);\n    const data = await res.json();\n    return data;\n}',
            'SELECT * FROM orders WHERE status = 1 ORDER BY created_at',
            'for item in items:\n    if item["status"] == "active":\n        process(item)',
            'function calculate(a, b, c, d, e) {\n    return a + b + c + d + e;\n}'
        ]
    },
    
    # 调试场景
    'debugging': {
        'weight': 0.12,
        'templates': [
            '程序报错：{error}，帮我定位问题',
            '这个 bug 很难复现，帮我分析可能的原因',
            '服务器 CPU 突然飙升到 100%，怎么排查？',
            '数据库连接池经常耗尽，是什么原因？',
            '这个内存泄漏问题困扰我很久了',
            'API 偶尔超时，如何定位？',
            '测试环境正常，生产环境报错',
            '这个异步函数没有按预期执行'
        ],
        'errors': [
            'ConnectionTimeout', 'NullPointerException', 'IndexError', 
            'MemoryError', 'TimeoutError', 'KeyError', 'ValueError',
            'Segmentation fault', 'Deadlock', 'Race condition'
        ]
    },
    
    # 架构设计场景
    'architecture': {
        'weight': 0.08,
        'templates': [
            '设计一个高并发的订单系统架构',
            '帮我评估微服务拆分的方案',
            '这个数据库表结构设计合理吗？',
            '如何设计一个可扩展的权限系统？',
            '推荐一个适合我们业务的缓存策略',
            '这个 API 网关设计有什么缺陷？',
            '帮我设计一个实时消息推送方案',
            '如何选择：单体架构 vs 微服务？'
        ]
    },
    
    # 数据分析场景
    'data_analysis': {
        'weight': 0.15,
        'templates': [
            '分析这个月的销售数据：{data}',
            '用户留存率在下降，帮我分析原因',
            '计算这个营销活动的 ROI',
            '预测下个月的 GMV',
            '这个用户行为数据有什么异常？',
            '帮我做竞品分析：{competitor}',
            '这个漏斗转化率怎么优化？',
            '生成一份业务复盘报告'
        ],
        'data': [
            '日活 10万，周活 45万，月活 120万',
            '新增用户 5000，次日留存 45%，7日留存 25%',
            '订单量 12000，GMV 360万，客单价 300元',
            '广告消耗 50万，转化 1200单，ROI 1:2.4'
        ],
        'competitors': ['腾讯', '阿里', '字节跳动', '美团', '拼多多', '京东', '百度']
    },
    
    # 文档写作场景
    'document_writing': {
        'weight': 0.14,
        'templates': [
            '帮我写一份 {doc_type}',
            '润色这段文案：{text}',
            '生成一份 {meeting} 的会议纪要',
            '写一封给 {audience} 的商务邮件',
            '帮我准备 {presentation} 的 PPT 大纲',
            '写一份 {report_type} 报告',
            '生成用户调研问卷',
            '帮我写述职报告'
        ],
        'doc_types': [
            '产品需求文档', '技术方案文档', 'API 接口文档', '测试用例文档',
            '用户操作手册', '项目计划书', '验收报告', '故障复盘'
        ],
        'meetings': ['周会', '项目启动会', '需求评审会', '技术方案评审', '复盘会'],
        'audiences': ['客户', '投资人', '合作伙伴', '内部团队', '领导'],
        'presentations': ['产品发布', '项目汇报', '融资路演', '技术分享'],
        'report_types': ['周报', '月报', '季度复盘', '年度总结'],
        'texts': [
            '我们推出了一款革命性的 AI 产品',
            '这次活动取得了圆满成功',
            '用户反馈非常积极'
        ]
    },
    
    # 学习研究场景
    'learning': {
        'weight': 0.11,
        'templates': [
            '解释 {concept} 的工作原理',
            '{tech1} 和 {tech2} 应该怎么选？',
            '帮我梳理 {field} 的知识体系',
            '什么是 {concept}？举个例子',
            '学习 {tech} 的最佳路径是什么？',
            '这个算法的复杂度是多少？',
            '推荐几本关于 {field} 的好书',
            '这个技术的底层原理是什么？'
        ],
        'concepts': [
            '区块链', '机器学习', '容器化', '微服务', 'CQRS', 'Event Sourcing',
            'CAP 定理', 'OAuth 2.0', 'JWT', 'GraphQL', 'WebSocket', 'gRPC'
        ],
        'techs': [
            'Python', 'Go', 'Rust', 'TypeScript', 'Java', 'Kotlin',
            'React', 'Vue', 'Angular', 'Svelte',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
            'Docker', 'Kubernetes', 'Terraform', 'Ansible'
        ],
        'fields': [
            '云计算', '人工智能', '大数据', '网络安全', '分布式系统',
            '前端开发', '后端开发', 'DevOps', '数据科学'
        ]
    },
    
    # 内容创作场景
    'content_creation': {
        'weight': 0.08,
        'templates': [
            '生成 10 个 {product} 的营销文案',
            '帮我想一些 {festival} 的活动创意',
            '为 {product} 起一个有创意的名字',
            '设计一个裂变活动的方案',
            '写一段短视频脚本，关于 {topic}',
            '生成一些社交媒体推文',
            '帮我想品牌 slogan',
            '设计用户增长策略'
        ],
        'products': [
            'AI 助手', '智能客服', '数据分析平台', '在线教育 App',
            '健身应用', '电商小程序', '企业协作工具', '云存储服务'
        ],
        'festivals': ['双十一', '618', '春节', '圣诞节', '情人节', '黑五'],
        'topics': ['职场效率', '生活方式', '科技前沿', '情感共鸣', '搞笑娱乐']
    },
    
    # 客服支持场景
    'user_operation': {
        'weight': 0.06,
        'templates': [
            '客户投诉 {issue}，怎么回复？',
            '用户反馈找不到功能入口',
            '帮我设计降低客诉率的方案',
            '这个退款申请如何处理？',
            '用户账号异常，需要安抚',
            '生成常见问题 FAQ',
            '这个用户流失预警怎么处理？',
            'VIP 用户提出了特殊需求'
        ],
        'issues': [
            '产品质量问题', '物流太慢', '价格太贵', '功能不会用',
            '想要退款', '账号被封', '数据丢失', '客服态度差'
        ]
    },
    
    # 敏感信息场景
    'with_sensitive': {
        'weight': 0.04,
        'templates': [
            '我的身份证：{idcard}，验证格式',
            '银行卡号：{bankcard}，查询开户行',
            '手机号 {phone}，分析运营商',
            '这个密码强度：{password}',
            '邮箱 {email}，检查泄露',
            '机密：{secret}，分析风险',
            'API 密钥：{key}，测试连通性'
        ]
    },
    
    # 自动化/批量操作场景
    'automation': {
        'weight': 0.02,
        'templates': [
            '帮我写脚本批量处理数据',
            '自动化测试这个 API',
            '批量生成测试数据',
            '脚本定时备份数据库',
            '自动化的报表生成',
            '批量发送邮件脚本',
            '数据迁移脚本'
        ]
    },
    
    # 多轮对话场景
    'multi_turn': {
        'weight': 0.02,
        'templates': [
            '继续刚才的讨论，如果考虑 {condition} 呢？',
            '基于之前的方案，我有几个问题',
            '补充一下背景：{context}',
            '这个方案的优缺点是什么？',
            '能不能给几个备选方案？',
            '这个实现的时间成本如何？'
        ],
        'conditions': [
            '用户量增长 10 倍', '预算减半', '时间压缩一半',
            '需要支持多语言', '数据安全要求更高'
        ],
        'contexts': [
            '我们是 ToB 业务', '主要面向海外市场',
            '客户对 SLA 要求很高', '技术团队规模较小'
        ]
    }
}

# 定价配置（每 1K tokens）
PRICING = {
    'gpt-4': 0.03, 'gpt-4-turbo': 0.01, 'gpt-4o': 0.005,
    'gpt-3.5-turbo': 0.0005, 'gpt-3.5-turbo-16k': 0.001,
    'claude-3-opus': 0.015, 'claude-3-sonnet': 0.003, 'claude-3-haiku': 0.00025,
    'qwen-turbo': 0.0005, 'qwen-plus': 0.002, 'qwen-max': 0.01,
    'ernie-bot-4': 0.004, 'ernie-bot': 0.002, 'ernie-bot-turbo': 0.001,
    'gpt-35-turbo': 0.0015
}

# 24小时调用强度曲线（模拟真实工作模式）
HOURLY_INTENSITY = {
    0: 0.03, 1: 0.02, 2: 0.01, 3: 0.01, 4: 0.01, 5: 0.02,
    6: 0.05, 7: 0.10, 8: 0.25, 9: 0.85, 10: 0.95, 11: 0.90,
    12: 0.60, 13: 0.55, 14: 0.88, 15: 0.92, 16: 0.90, 17: 0.85,
    18: 0.50, 19: 0.35, 20: 0.25, 21: 0.20, 22: 0.10, 23: 0.05
}


class SessionManager:
    """会话管理器"""
    def __init__(self):
        self.sessions = {}
    
    def get_or_create(self, user_id, timestamp, dept):
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'session_id': f"{dept[:2]}{uuid4().hex[:10].upper()}",
                'count': 0,
                'last_time': timestamp
            }
        
        session = self.sessions[user_id]
        
        # 30分钟无活动新建会话
        if (timestamp - session['last_time']).total_seconds() > 1800:
            session['session_id'] = f"{dept[:2]}{uuid4().hex[:10].upper()}"
            session['count'] = 0
        
        session['count'] += 1
        session['last_time'] = timestamp
        return session['session_id'], session['count']


session_mgr = SessionManager()
tagger = BehaviorTagger()


def generate_sensitive_data():
    """生成敏感数据"""
    return {
        'idcard': ''.join(random.choices(string.digits, k=17)) + random.choice('0123456789X'),
        'bankcard': ''.join(random.choices(string.digits, k=16)),
        'phone': '1' + random.choice('3456789') + ''.join(random.choices(string.digits, k=9)),
        'password': random.choice(['Pass123!', 'Admin@2024', 'Qwerty!@#', 'Test#456']),
        'email': random.choice(['user@company.com', 'admin@corp.cn', 'test@example.com']),
        'key': 'sk-' + ''.join(random.choices(string.ascii_letters + string.digits, k=48)),
        'secret': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
    }


def generate_prompt(scenario):
    """生成提示词"""
    templates = SCENARIO_TEMPLATES[scenario]
    
    if scenario == 'code_review':
        category = random.choice(templates['templates'])
        prompt = random.choice(category['prompts'])
        if '{code}' in prompt or '{sql}' in prompt:
            code = random.choice(templates['code_snippets'])
            prompt = prompt.replace('{code}', code).replace('{sql}', code)
        return prompt
    
    elif scenario == 'debugging':
        prompt = random.choice(templates['templates'])
        error = random.choice(templates['errors'])
        return prompt.format(error=error)
    
    elif scenario == 'data_analysis':
        prompt = random.choice(templates['templates'])
        if '{data}' in prompt:
            data = random.choice(templates['data'])
            return prompt.format(data=data)
        elif '{competitor}' in prompt:
            comp = random.choice(templates['competitors'])
            return prompt.format(competitor=comp)
        return prompt
    
    elif scenario == 'document_writing':
        prompt = random.choice(templates['templates'])
        if '{doc_type}' in prompt:
            return prompt.format(doc_type=random.choice(templates['doc_types']))
        elif '{meeting}' in prompt:
            return prompt.format(meeting=random.choice(templates['meetings']))
        elif '{audience}' in prompt:
            return prompt.format(audience=random.choice(templates['audiences']))
        elif '{presentation}' in prompt:
            return prompt.format(presentation=random.choice(templates['presentations']))
        elif '{report_type}' in prompt:
            return prompt.format(report_type=random.choice(templates['report_types']))
        elif '{text}' in prompt:
            return prompt.format(text=random.choice(templates['texts']))
        return prompt
    
    elif scenario == 'learning':
        prompt = random.choice(templates['templates'])
        if '{concept}' in prompt:
            return prompt.format(concept=random.choice(templates['concepts']))
        elif '{tech1}' in prompt and '{tech2}' in prompt:
            techs = random.sample(templates['techs'], 2)
            return prompt.format(tech1=techs[0], tech2=techs[1])
        elif '{field}' in prompt:
            return prompt.format(field=random.choice(templates['fields']))
        elif '{tech}' in prompt:
            return prompt.format(tech=random.choice(templates['techs']))
        return prompt
    
    elif scenario == 'content_creation':
        prompt = random.choice(templates['templates'])
        if '{product}' in prompt:
            return prompt.format(product=random.choice(templates['products']))
        elif '{festival}' in prompt:
            return prompt.format(festival=random.choice(templates['festivals']))
        elif '{topic}' in prompt:
            return prompt.format(topic=random.choice(templates['topics']))
        return prompt
    
    elif scenario == 'user_operation':
        prompt = random.choice(templates['templates'])
        if '{issue}' in prompt:
            return prompt.format(issue=random.choice(templates['issues']))
        return prompt
    
    elif scenario in ['with_sensitive', 'automation']:
        prompt = random.choice(templates['templates'])
        sensitive = generate_sensitive_data()
        try:
            return prompt.format(**sensitive)
        except:
            return prompt
    
    elif scenario == 'multi_turn':
        prompt = random.choice(templates['templates'])
        if '{condition}' in prompt:
            return prompt.format(condition=random.choice(templates['conditions']))
        elif '{context}' in prompt:
            return prompt.format(context=random.choice(templates['contexts']))
        return prompt
    
    return random.choice(templates['templates'])


def weighted_choice(items):
    """带权重的随机选择"""
    weights = [item[1] if isinstance(item, tuple) else 1 for item in items]
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for item, weight in (items if isinstance(items[0], tuple) else [(x, 1) for x in items]):
        if upto + weight >= r:
            return item
        upto += weight
    return items[-1][0] if isinstance(items[-1], tuple) else items[-1]


async def generate_super_data(days: int = 90, total_records: int = 150000):
    """生成超级增强版演示数据"""
    print("🚀 超级增强版演示数据生成器")
    print("=" * 60)
    print(f"时间跨度: {days} 天")
    print(f"预期记录: {total_records:,} 条")
    print(f"预估时间: 约 5-10 分钟")
    print("=" * 60)
    
    await init_db()
    
    records = []
    user_call_counts = {}
    total_inserted = 0
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # 计算每小时的基准记录数
    base_per_hour = total_records / (days * 24)
    
    current = start_time
    batch_num = 0
    
    while current < end_time:
        hour = current.hour
        is_weekend = current.weekday() >= 5
        
        # 计算强度
        intensity = HOURLY_INTENSITY.get(hour, 0.5)
        if is_weekend:
            intensity *= 0.25  # 周末大幅降低
        
        # 生成记录数
        target_count = int(base_per_hour * intensity * random.uniform(0.7, 1.3))
        
        for _ in range(target_count):
            # 选择部门
            dept_name = weighted_choice([(k, v['weight']) for k, v in DEPARTMENTS.items()])
            dept = DEPARTMENTS[dept_name]
            
            # 选择用户
            user = random.choice(dept['users'])
            user_id = f"{user}_{random.randint(1000, 9999)}"
            
            # 选择场景
            scenario = weighted_choice(list(SCENARIO_TEMPLATES.items()))
            
            # 选择供应商和模型
            provider_name = weighted_choice([(k, v['weight']) for k, v in PROVIDERS.items()])
            provider = PROVIDERS[provider_name]
            model = weighted_choice(provider['models'])
            
            # 生成时间
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            record_time = current.replace(minute=minute, second=second)
            
            if record_time >= end_time:
                continue
            
            # 生成提示词
            prompt = generate_prompt(scenario)
            
            # 根据场景调整 Token
            if scenario == 'code_review':
                tokens_in = random.randint(800, 4000)
            elif scenario == 'data_analysis':
                tokens_in = random.randint(500, 3000)
            elif scenario == 'document_writing':
                tokens_in = random.randint(300, 2500)
            elif scenario == 'learning':
                tokens_in = random.randint(200, 1500)
            elif scenario == 'with_sensitive':
                tokens_in = random.randint(100, 800)
            else:
                tokens_in = random.randint(200, 2000)
            
            # 输出通常是输入的 0.4-1.8 倍
            tokens_out = int(tokens_in * random.uniform(0.4, 1.8))
            
            # 计算成本
            cost = (tokens_in + tokens_out) / 1000 * PRICING.get(model, 0.002)
            
            # 会话管理
            session_id, session_turn = session_mgr.get_or_create(user_id, record_time, dept_name)
            
            # 风险检测
            history = user_call_counts.get(user_id, [])
            risk_level, risk_reasons = detect_risk_level(
                prompt, tokens_in, tokens_out, record_time.isoformat(), history
            )
            
            # 行为标签
            tags = tagger.tag(
                user_id, prompt, tokens_in, tokens_out, cost,
                record_time.isoformat(), model, session_id
            )
            
            # 记录历史
            if user_id not in user_call_counts:
                user_call_counts[user_id] = []
            user_call_counts[user_id].append(record_time)
            
            records.append({
                'timestamp': record_time.isoformat(),
                'user_id': user_id,
                'department': dept_name,
                'provider': provider_name,
                'model': model,
                'prompt': prompt[:1000],
                'prompt_length': len(prompt),
                'response_length': tokens_out * 4,
                'tokens_input': tokens_in,
                'tokens_output': tokens_out,
                'cost_usd': round(cost, 6),
                'risk_level': risk_level,
                'risk_reasons': risk_reasons,
                'behavior_tags': tags,
                'session_id': session_id,
                'client_ip': f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            })
        
        # 批量插入
        if len(records) >= 2000:
            await insert_audit_logs(records)
            total_inserted += len(records)
            batch_num += 1
            
            if batch_num % 5 == 0:
                progress = (current - start_time) / (end_time - start_time) * 100
                eta = (100 - progress) / progress * (current - start_time).total_seconds() / 3600 if progress > 0 else 0
                print(f"  [{progress:5.1f}%] 已插入 {total_inserted:,} 条 | 预计还需 {eta:.1f} 小时")
            
            records = []
        
        current += timedelta(hours=1)
    
    # 插入剩余
    if records:
        await insert_audit_logs(records)
        total_inserted += len(records)
    
    print("=" * 60)
    print(f"✅ 生成完成！")
    print(f"  实际记录: {total_inserted:,} 条")
    print(f"  时间跨度: {days} 天")
    
    # 统计摘要
    from database import aiosqlite, DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT risk_level, COUNT(*) FROM audit_logs GROUP BY risk_level")
        print(f"\n📊 风险分布:")
        for row in await cursor.fetchall():
            print(f"  {row[0]:12s}: {row[1]:8,} ({row[1]/total_inserted*100:5.1f}%)")
        
        cursor = await db.execute("SELECT behavior_tags FROM audit_logs")
        tag_counts = {}
        for row in await cursor.fetchall():
            for tag in json.loads(row[0] or '[]'):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        print(f"\n🏷️ Top 10 行为标签:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {tag}: {count:,}")
        
        cursor = await db.execute("SELECT department, COUNT(*) FROM audit_logs GROUP BY department ORDER BY COUNT(*) DESC")
        print(f"\n🏢 部门分布:")
        for row in await cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,}")


if __name__ == "__main__":
    asyncio.run(generate_super_data(days=90, total_records=150000))
