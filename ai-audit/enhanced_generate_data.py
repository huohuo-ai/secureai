#!/usr/bin/env python3
"""
AI 审计平台 - 增强版演示数据生成器
生成更丰富、更真实的模拟数据
"""

import asyncio
import random
import string
import json
from datetime import datetime, timedelta, time
from uuid import uuid4
from database import init_db, insert_audit_logs
from risk_detector import detect_risk_level
from behavior_tagger import BehaviorTagger

# ============ 扩展配置 ============

DEPARTMENTS = {
    '研发部': {'weight': 0.40, 'users': ['张三', '李四', '王五', '赵六', '陈七', '刘八', '周九', '吴十', '郑十一', '孙十二']},
    '产品部': {'weight': 0.18, 'users': ['产品经理小王', '产品经理小李', '产品总监老张', '需求分析师小刘', '用户研究员小赵']},
    '市场部': {'weight': 0.15, 'users': ['市场专员小美', '市场经理大力', '内容运营小陈', '活动策划小王', '品牌经理小周']},
    '运营部': {'weight': 0.12, 'users': ['数据运营小赵', '用户运营小钱', '活动运营小孙', '社区运营小李', '增长黑客小周']},
    '设计部': {'weight': 0.08, 'users': ['UI设计师小丽', 'UX设计师小芳', '视觉设计师小明', '插画师小红', '动效设计师小刚']},
    '财务部': {'weight': 0.04, 'users': ['会计小周', '财务主管小吴', '审计小郑', '出纳小王']},
    '人事部': {'weight': 0.03, 'users': ['HR小赵', '招聘专员小钱']},
}

PROVIDERS = {
    'openai': {'weight': 0.55, 'models': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o']},
    'claude': {'weight': 0.25, 'models': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku']},
    'qwen': {'weight': 0.12, 'models': ['qwen-turbo', 'qwen-plus', 'qwen-max']},
    'baidu': {'weight': 0.05, 'models': ['ernie-bot', 'ernie-bot-turbo']},
    'azure': {'weight': 0.03, 'models': ['gpt-4', 'gpt-35-turbo']},
}

# 扩展场景模板
SCENARIOS = {
    # 正常办公场景
    'code_review': {
        'weight': 0.20,
        'templates': [
            '请帮我 review 这段代码，检查是否有潜在的性能问题：\n```\n{code}\n```',
            '优化这段 Python 代码，提高可读性：\n{code}',
            '这段 SQL 查询很慢，如何优化？\n{sql}',
            '帮我找出这段 JavaScript 代码中的内存泄漏问题',
            '请将这段代码重构为使用设计模式：\n{code}',
            '检查这段代码的安全性，有没有 SQL 注入风险？',
            '帮我写单元测试覆盖这段代码',
            '将这个函数改为异步实现，提高并发性能',
        ],
        'code_snippets': [
            'def process_data(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    return result',
            'SELECT * FROM users WHERE status = 1',
            'for (let i = 0; i < items.length; i++) {\n    items[i].addEventListener("click", function() {})\n}',
            'import requests\nresponse = requests.get(url)\ndata = response.json()',
        ]
    },
    
    # 数据分析场景
    'data_analysis': {
        'weight': 0.15,
        'templates': [
            '分析这组销售数据，找出增长趋势和异常点：\n{data}',
            '帮我解读这个用户留存率报表，计算环比增长率',
            '预测下个月的销售额，基于过去 6 个月的数据：\n{data}',
            '分析竞品 {竞品} 的产品策略和市场定位',
            '帮我做一份 Q3 业务复盘的数据分析',
            '计算这个营销活动的 ROI，分析哪些渠道效果最好',
            '分析用户流失的原因，基于行为数据：\n{data}',
            '帮我生成一份周报数据摘要',
        ],
        'data': [
            '1月: 100万, 2月: 120万, 3月: 115万, 4月: 140万, 5月: 160万, 6月: 180万',
            '日活: 10000, 周活: 45000, 月活: 120000, 留存率: 35%',
            '新用户: 500, 激活: 320, 付费: 45, 客单价: ¥299',
        ]
    },
    
    # 文档写作场景
    'document_writing': {
        'weight': 0.15,
        'templates': [
            '帮我写一封正式的商务邮件，主题是 {主题}',
            '生成一份 {文档类型}，包含目录和核心要点',
            '润色这段文案，让它更有吸引力和说服力：\n{text}',
            '写一份项目计划书，包含背景、目标、里程碑和资源需求',
            '生成一份会议纪要，提取以下讨论要点：\n{points}',
            '帮我写一份述职报告，突出业绩和成长性',
            '写一段产品发布会的开场白，面向 {受众}',
            '生成一份用户调研问卷，包含 10 个核心问题',
        ],
        'topics': ['产品合作意向', '项目延期说明', '需求变更申请', '年度汇报'],
        'doc_types': ['产品需求文档', '技术方案文档', '测试用例文档', '用户操作手册'],
    },
    
    # 学习研究场景
    'learning': {
        'weight': 0.12,
        'templates': [
            '解释 {概念} 的工作原理，用通俗的语言',
            '帮我理解 {技术} 和 {技术} 的区别和适用场景',
            '介绍一下大语言模型的技术架构和训练方法',
            '什么是 {概念}？请举例说明',
            '帮我梳理 {领域} 的知识体系和学习路径',
            '解释机器学习中的 {算法} 算法，给出代码示例',
            '{技术} 的最佳实践是什么？有哪些常见坑？',
        ],
        'concepts': ['区块链', '微服务', '容器化', 'CI/CD', 'OAuth2.0', 'GraphQL'],
        'technologies': ['Python', 'Go', 'Rust', 'Node.js', 'Java', 'Kotlin'],
        'fields': ['云计算', '人工智能', '数据工程', '网络安全', '前端开发'],
        'algorithms': ['随机森林', '梯度下降', '神经网络', '聚类分析'],
    },
    
    # 创意生成场景
    'creative': {
        'weight': 0.08,
        'templates': [
            '帮我想 10 个 {产品} 的创新功能点',
            '生成 5 个 {节日} 营销活动的创意主题',
            '帮我想一个 {产品} 的品牌 slogan',
            '设计一个提升用户留存的产品功能方案',
            '生成一些短视频脚本创意，关于 {主题}',
            '帮我想一个用户增长黑客方案',
            '设计一个裂变活动，目标是新增 10000 用户',
        ],
        'products': ['AI 助手', '电商平台', '社交 App', '在线教育', '健身应用'],
        'festivals': ['双十一', '618', '春节', '圣诞节', '黑色星期五'],
        'themes': ['职场效率', '生活方式', '科技前沿', '情感共鸣'],
    },
    
    # 客服/支持场景
    'customer_support': {
        'weight': 0.05,
        'templates': [
            '客户投诉 {问题}，帮我写一封回复邮件',
            '生成 FAQ，回答关于 {功能} 的常见问题',
            '帮我想一些降低客服工单量的方案',
            '分析客户反馈：{feedback}，提取关键问题和改进建议',
            '写一份产品使用指南，针对新用户入门',
        ],
        'issues': ['退款问题', '账户异常', '功能不会用', '性能太慢', '数据丢失'],
        'features': ['订阅管理', '数据导出', '权限设置', 'API 接入'],
    },
    
    # 敏感信息场景（高风险）
    'with_sensitive': {
        'weight': 0.08,
        'templates': [
            '我的身份证号是 {身份证}，帮我验证下格式是否正确',
            '银行卡号 {银行卡}，查询开户行和余额',
            '手机号 {手机号}，分析归属地和运营商',
            '这个密码 {密码} 强度如何？',
            '邮箱 {邮箱}，检查是否存在泄露风险',
            '机密文件内容：{content}，提取关键信息',
            '内部数据：{data}，生成分析报告',
            'AKID={akid}\nAKSecret={secret}\n帮我测试这个 API 密钥',
        ]
    },
    
    # 异常行为场景
    'high_frequency': {
        'weight': 0.05,
        'templates': [
            'test {item}',
            'debug {item}',
            'check {item}',
            'test connection',
            'ping test',
        ],
        'items': ['API', 'database', 'cache', 'queue', 'redis', 'mongodb']
    },
    
    'night_usage': {
        'weight': 0.05,
        'templates': [
            '紧急！生产环境出现 {problem}，请帮忙排查',
            '出大事了！{problem}，需要立即解决',
            '帮忙看看 {problem}，客户一直在催',
            '这个问题很急，{problem}',
        ],
        'problems': [
            '数据库连接池耗尽', 'Redis 内存溢出', 'API 响应超时', 
            '服务器 CPU 100%', '内存泄漏', '大量 500 错误'
        ]
    },
    
    'large_token': {
        'weight': 0.04,
        'templates': [
            '分析这段长文本：{long_text}',
            '总结这份 50 页的技术文档：{long_text}',
            '处理这个大型数据集：{long_text}',
            '帮我 review 这份代码库：{long_text}',
        ]
    },
    
    # 多轮对话场景
    'conversation': {
        'weight': 0.03,
        'templates': [
            '继续上面的讨论，我还有几个问题：\n{questions}',
            '基于你之前的回答，我想深入了解一下 {topic}',
            '刚才的方案很好，但是如果考虑 {condition} 呢？',
            '补充一些背景信息：{context}，请重新分析',
        ]
    }
}

# 会话上下文存储
class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def get_or_create_session(self, user_id, timestamp):
        """获取或创建会话"""
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'session_id': str(uuid4())[:12],
                'turn_count': 0,
                'last_time': timestamp,
                'context': []
            }
        
        session = self.sessions[user_id]
        
        # 超过 30 分钟创建新会话
        if (timestamp - session['last_time']).total_seconds() > 1800:
            self.sessions[user_id] = {
                'session_id': str(uuid4())[:12],
                'turn_count': 0,
                'last_time': timestamp,
                'context': []
            }
        
        self.sessions[user_id]['turn_count'] += 1
        self.sessions[user_id]['last_time'] = timestamp
        
        return self.sessions[user_id]

session_manager = SessionManager()
tagger = BehaviorTagger()


def generate_sensitive_data():
    """生成敏感数据"""
    return {
        '身份证': ''.join(random.choices(string.digits, k=17)) + random.choice('0123456789X'),
        '银行卡': ''.join(random.choices(string.digits, k=16)),
        '手机号': '1' + random.choice('3456789') + ''.join(random.choices(string.digits, k=9)),
        '密码': random.choice(['Password123!', 'Admin@2024', 'Qwerty!@#', 'Test123456']),
        '邮箱': random.choice(['user@example.com', 'admin@test.com', 'test@gmail.com']),
        'akid': 'AKID' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=20)),
        'secret': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
        'content': '内部机密信息，严禁外传',
        'data': 'Q3 营收 5000 万，利润 800 万，同比增长 35%',
        'long_text': '这是一段测试内容。' * 200  # 约 2000 字符
    }


def generate_prompt(scenario):
    """生成提示词"""
    template = random.choice(SCENARIOS[scenario]['templates'])
    
    if scenario == 'code_review':
        code = random.choice(SCENARIOS[scenario]['code_snippets'])
        return template.format(code=code)
    
    elif scenario == 'data_analysis':
        data = random.choice(SCENARIOS[scenario]['data'])
        竞品 = random.choice(['腾讯', '阿里', '字节', '美团', '拼多多'])
        return template.format(data=data, 竞品=竞品)
    
    elif scenario == 'document_writing':
        if '{主题}' in template:
            return template.format(主题=random.choice(SCENARIOS[scenario]['topics']))
        elif '{文档类型}' in template:
            return template.format(文档类型=random.choice(SCENARIOS[scenario]['doc_types']))
        elif '{受众}' in template:
            return template.format(受众=random.choice(['投资人', '客户', '内部团队']))
        elif '{text}' in template:
            return template.format(text='这是一款创新产品，具有独特的功能和优秀的用户体验。')
        elif '{points}' in template:
            return template.format(points='1. Q4 目标 2. 资源需求 3. 风险评估')
        return template
    
    elif scenario == 'learning':
        if '{概念}' in template:
            return template.format(概念=random.choice(SCENARIOS[scenario]['concepts']))
        elif '{技术}' in template:
            techs = SCENARIOS[scenario]['technologies']
            return template.format(技术=random.choice(techs), 技术2=random.choice(techs))
        elif '{领域}' in template:
            return template.format(领域=random.choice(SCENARIOS[scenario]['fields']))
        elif '{算法}' in template:
            return template.format(算法=random.choice(SCENARIOS[scenario]['algorithms']))
        return template
    
    elif scenario == 'creative':
        if '{产品}' in template:
            return template.format(产品=random.choice(SCENARIOS[scenario]['products']))
        elif '{节日}' in template:
            return template.format(节日=random.choice(SCENARIOS[scenario]['festivals']))
        elif '{主题}' in template:
            return template.format(主题=random.choice(SCENARIOS[scenario]['themes']))
        return template
    
    elif scenario == 'customer_support':
        if '{问题}' in template:
            return template.format(问题=random.choice(SCENARIOS[scenario]['issues']))
        elif '{功能}' in template:
            return template.format(功能=random.choice(SCENARIOS[scenario]['features']))
        elif '{feedback}' in template:
            return template.format(feedback='产品很难用，找不到功能入口，希望改进')
        return template
    
    elif scenario in ['with_sensitive', 'high_frequency', 'night_usage']:
        sensitive = generate_sensitive_data()
        try:
            return template.format(**sensitive)
        except:
            return template.format(item=random.choice(SCENARIOS[scenario].get('items', ['test'])))
    
    elif scenario == 'large_token':
        long_text = '这是一段长文本内容，用于测试大 Token 场景。' * 500
        return template.format(long_text=long_text)
    
    elif scenario == 'conversation':
        return template.format(
            questions='1. 性能如何优化？ 2. 成本怎么控制？',
            topic='扩展性和维护性',
            condition='用户量增长 10 倍',
            context='我们是 ToB 业务，客户对数据安全要求很高'
        )
    
    return template


def generate_call_record(timestamp, user_call_counts):
    """生成单条调用记录"""
    # 选择场景
    scenarios = list(SCENARIOS.keys())
    weights = [SCENARIOS[s]['weight'] for s in scenarios]
    scenario = random.choices(scenarios, weights=weights)[0]
    
    # 生成用户信息
    dept_name = random.choices(
        list(DEPARTMENTS.keys()),
        weights=[d['weight'] for d in DEPARTMENTS.values()]
    )[0]
    dept = DEPARTMENTS[dept_name]
    user = random.choice(dept['users'])
    user_id = f"{user}_{random.randint(1000, 9999)}"
    
    # 生成调用信息
    provider_name = random.choices(
        list(PROVIDERS.keys()),
        weights=[p['weight'] for p in PROVIDERS.values()]
    )[0]
    provider = PROVIDERS[provider_name]
    model = random.choice(provider['models'])
    
    # 生成提示词
    prompt = generate_prompt(scenario)
    
    # 生成 Token 数（根据场景调整）
    if scenario == 'large_token':
        tokens_input = random.randint(8000, 20000)
    elif scenario == 'with_sensitive':
        tokens_input = random.randint(100, 1000)
    elif scenario == 'code_review':
        tokens_input = random.randint(500, 3000)
    elif scenario == 'data_analysis':
        tokens_input = random.randint(800, 4000)
    else:
        tokens_input = random.randint(200, 3000)
    
    # 输出 Token 通常是输入的 0.5-2 倍
    tokens_output = int(tokens_input * random.uniform(0.5, 2.0))
    
    # 计算成本（基于不同模型的定价）
    pricing = {
        'gpt-4': 0.03, 'gpt-4-turbo': 0.01, 'gpt-4o': 0.005,
        'gpt-3.5-turbo': 0.0015,
        'claude-3-opus': 0.015, 'claude-3-sonnet': 0.003, 'claude-3-haiku': 0.00025,
        'qwen-turbo': 0.0005, 'qwen-plus': 0.002, 'qwen-max': 0.01,
        'ernie-bot': 0.002, 'ernie-bot-turbo': 0.001,
        'gpt-35-turbo': 0.0015
    }
    price_per_1k = pricing.get(model, 0.002)
    cost = (tokens_input + tokens_output) / 1000 * price_per_1k
    
    # 获取会话
    session = session_manager.get_or_create_session(user_id, timestamp)
    
    # 检测风险
    user_history = user_call_counts.get(user_id, [])
    risk_level, risk_reasons = detect_risk_level(
        prompt=prompt,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        timestamp=timestamp.isoformat(),
        user_call_history=user_history
    )
    
    # 生成行为标签
    behavior_tags = tagger.tag(
        user_id=user_id,
        prompt=prompt,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost,
        timestamp=timestamp.isoformat(),
        model=model,
        session_id=session['session_id']
    )
    
    # 记录调用时间
    if user_id not in user_call_counts:
        user_call_counts[user_id] = []
    user_call_counts[user_id].append(timestamp)
    
    return {
        'timestamp': timestamp.isoformat(),
        'user_id': user_id,
        'department': dept_name,
        'provider': provider_name,
        'model': model,
        'prompt': prompt[:800],  # 截断存储
        'prompt_length': len(prompt),
        'response_length': tokens_output * 4,
        'tokens_input': tokens_input,
        'tokens_output': tokens_output,
        'cost_usd': round(cost, 6),
        'risk_level': risk_level,
        'risk_reasons': risk_reasons,
        'behavior_tags': behavior_tags,
        'session_id': session['session_id'],
        'client_ip': f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        'scenario': scenario
    }


def is_workday(date):
    """判断是否工作日（简化：周一到周五）"""
    return date.weekday() < 5


def get_call_intensity(timestamp):
    """根据时间获取调用强度（0-1）"""
    hour = timestamp.hour
    
    # 深夜（0-6点）
    if hour < 6:
        return random.uniform(0.02, 0.1)
    
    # 早上（6-9点）
    elif hour < 9:
        return random.uniform(0.1, 0.3)
    
    # 工作时间（9-12点）
    elif hour < 12:
        return random.uniform(0.6, 1.0)
    
    # 午休（12-14点）
    elif hour < 14:
        return random.uniform(0.2, 0.4)
    
    # 下午工作时间（14-18点）
    elif hour < 18:
        return random.uniform(0.7, 1.0)
    
    # 晚上（18-22点）
    elif hour < 22:
        return random.uniform(0.2, 0.5)
    
    # 深夜（22-24点）
    else:
        return random.uniform(0.05, 0.15)


async def generate_enhanced_demo_data(days: int = 60, total_records: int = 50000):
    """生成增强版演示数据"""
    print(f"🚀 开始生成增强版演示数据")
    print(f"   时间跨度: {days} 天")
    print(f"   预期记录: {total_records:,} 条")
    print("=" * 50)
    
    await init_db()
    
    records = []
    user_call_counts = {}
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # 按小时生成
    current = start_time
    records_per_hour = total_records / (days * 24)
    
    batch_count = 0
    total_inserted = 0
    
    while current < end_time:
        # 根据时间和是否工作日调整强度
        intensity = get_call_intensity(current)
        if not is_workday(current):
            intensity *= 0.3  # 周末降低到 30%
        
        # 计算当前小时生成的记录数
        base_count = records_per_hour * intensity
        count = max(0, int(base_count * random.uniform(0.7, 1.3)))
        
        # 生成记录
        for _ in range(count):
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            record_time = current.replace(minute=minute, second=second)
            
            if record_time < end_time:
                record = generate_call_record(record_time, user_call_counts)
                records.append(record)
        
        # 批量插入
        if len(records) >= 1000:
            await insert_audit_logs(records)
            batch_count += 1
            total_inserted += len(records)
            
            if batch_count % 10 == 0:
                progress = (current - start_time) / (end_time - start_time) * 100
                print(f"  [{progress:5.1f}%] 已插入 {total_inserted:,} 条记录...")
            
            records = []
        
        current += timedelta(hours=1)
    
    # 插入剩余记录
    if records:
        await insert_audit_logs(records)
        total_inserted += len(records)
    
    print("=" * 50)
    print(f"✅ 演示数据生成完成！")
    print(f"   实际记录: {total_inserted:,} 条")
    print(f"   时间跨度: {days} 天")
    print(f"   平均每日: {total_inserted // days:,} 条")
    
    # 统计摘要
    from database import aiosqlite, DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        # 风险分布
        cursor = await db.execute("""
            SELECT risk_level, COUNT(*) as count 
            FROM audit_logs 
            GROUP BY risk_level
        """)
        print("\n📊 风险等级分布:")
        for row in await cursor.fetchall():
            print(f"   {row[0]:12s}: {row[1]:6,} ({row[1]/total_inserted*100:5.1f}%)")
        
        # Top 5 行为标签
        cursor = await db.execute("SELECT behavior_tags FROM audit_logs")
        tag_counts = {}
        for row in await cursor.fetchall():
            tags = json.loads(row[0] or '[]')
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print("\n🏷️ Top 5 行为标签:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"   {tag}: {count:,}")


if __name__ == "__main__":
    asyncio.run(generate_enhanced_demo_data(days=60, total_records=50000))
