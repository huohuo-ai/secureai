"""
演示数据生成器
生成 30 天的模拟数据，包含各种风险场景和行为标签
"""
import random
import string
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from database import init_db, insert_audit_logs
from risk_detector import detect_risk_level
from behavior_tagger import BehaviorTagger

# 配置
DEPARTMENTS = ['研发部', '产品部', '市场部', '运营部', '设计部', '财务部']
USERS = {
    '研发部': ['张三', '李四', '王五', '赵六', '陈七'],
    '产品部': ['产品经理小王', '产品经理小李', '产品总监老张'],
    '市场部': ['市场专员小美', '市场经理大力', '内容运营小陈'],
    '运营部': ['数据运营小赵', '用户运营小钱', '活动运营小孙'],
    '设计部': ['UI设计师小丽', 'UX设计师小芳'],
    '财务部': ['会计小周', '财务主管小吴']
}
PROVIDERS = ['openai', 'claude', 'qwen', 'baidu']
MODELS = {
    'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    'claude': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
    'qwen': ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    'baidu': ['ernie-bot', 'ernie-bot-turbo']
}

# 场景模板
SCENARIOS = {
    'normal': {
        'weight': 0.70,
        'templates': [
            '帮我写一个Python函数，实现{功能}',
            '优化这段代码：{代码片段}',
            '解释什么是{技术概念}',
            '写一个{类型}的SQL查询',
            '生成一份{文档类型}的模板',
            '帮我润色这段文案：{文案内容}',
            '分析这组数据：{数据描述}',
            '写一个正则表达式，匹配{匹配目标}',
            '帮我review这段代码',
            '生成一个{框架}组件'
        ],
        'functions': ['数据清洗', '文件上传', '用户认证', '数据可视化', 'API接口'],
        'concepts': ['机器学习', '区块链', '微服务', '容器化', 'CI/CD'],
        'docs': ['需求文档', '技术方案', '测试用例', '用户手册', '项目计划']
    },
    'with_sensitive': {
        'weight': 0.15,
        'templates': [
            '我的身份证号是{身份证}，帮我验证格式',
            '银行卡号{银行卡}，查询开户行',
            '手机号{手机号}，分析归属地',
            '密码是{密码}，检查强度',
            '这个邮箱{邮箱}，验证格式',
            '机密文件：{内容}，分析风险',
            '内部资料：{内容}，生成摘要'
        ]
    },
    'high_frequency': {
        'weight': 0.08,
        'templates': [
            '测试{item}',
            'debug {item}',
            '检查{item}'
        ],
        'items': ['API', '数据库连接', '缓存', '队列', '配置']
    },
    'night_usage': {
        'weight': 0.05,
        'templates': [
            '紧急：{问题}',
            '帮忙看看{问题}',
            '解决{问题}'
        ],
        'problems': ['生产环境报错', '数据异常', '性能问题', '安全告警']
    },
    'large_token': {
        'weight': 0.02,
        'templates': [
            '分析这段长文本：{长文本}',
            '总结这份文档：{文档内容}',
            '处理这个数据：{大量数据}'
        ]
    }
}


def generate_prompt(scenario: str) -> str:
    """生成提示词"""
    if scenario == 'normal':
        template = random.choice(SCENARIOS['normal']['templates'])
        if '{功能}' in template:
            return template.replace('{功能}', random.choice(SCENARIOS['normal']['functions']))
        elif '{技术概念}' in template:
            return template.replace('{技术概念}', random.choice(SCENARIOS['normal']['concepts']))
        elif '{文档类型}' in template:
            return template.replace('{文档类型}', random.choice(SCENARIOS['normal']['docs']))
        elif '{代码片段}' in template:
            return template.replace('{代码片段}', 'def foo(): pass')
        elif '{文案内容}' in template:
            return template.replace('{文案内容}', '这是一个产品描述文案')
        elif '{数据描述}' in template:
            return template.replace('{数据描述}', '用户行为数据，包含PV/UV/转化率')
        elif '{匹配目标}' in template:
            return template.replace('{匹配目标}', '手机号码')
        elif '{框架}' in template:
            return template.replace('{框架}', 'React')
        return template
    
    elif scenario == 'with_sensitive':
        template = random.choice(SCENARIOS['with_sensitive']['templates'])
        if '{身份证}' in template:
            idcard = ''.join(random.choices(string.digits, k=17)) + random.choice('0123456789X')
            return template.replace('{身份证}', idcard)
        elif '{银行卡}' in template:
            card = ''.join(random.choices(string.digits, k=16))
            return template.replace('{银行卡}', card)
        elif '{手机号}' in template:
            phone = '1' + random.choice('3456789') + ''.join(random.choices(string.digits, k=9))
            return template.replace('{手机号}', phone)
        elif '{密码}' in template:
            return template.replace('{密码}', 'Password123!')
        elif '{邮箱}' in template:
            return template.replace('{邮箱}', 'user@example.com')
        else:
            return template.replace('{内容}', '内部机密信息')
    
    elif scenario == 'high_frequency':
        template = random.choice(SCENARIOS['high_frequency']['templates'])
        return template.replace('{item}', random.choice(SCENARIOS['high_frequency']['items']))
    
    elif scenario == 'night_usage':
        template = random.choice(SCENARIOS['night_usage']['templates'])
        return template.replace('{问题}', random.choice(SCENARIOS['night_usage']['problems']))
    
    elif scenario == 'large_token':
        template = random.choice(SCENARIOS['large_token']['templates'])
        # 生成长文本
        long_text = '这是测试内容。' * 500  # 约 5000 字符
        return template.replace('{长文本}', long_text).replace('{文档内容}', long_text).replace('{大量数据}', long_text)
    
    return 'Hello'


def generate_call_record(timestamp: datetime, tagger: BehaviorTagger) -> dict:
    """生成单条调用记录"""
    # 选择场景
    scenarios = list(SCENARIOS.keys())
    weights = [SCENARIOS[s]['weight'] for s in scenarios]
    scenario = random.choices(scenarios, weights=weights)[0]
    
    # 生成用户信息
    dept = random.choice(DEPARTMENTS)
    user = random.choice(USERS[dept])
    user_id = f"{user}_{random.randint(1000, 9999)}"
    
    # 生成调用信息
    provider = random.choices(
        PROVIDERS, 
        weights=[0.60, 0.25, 0.10, 0.05]
    )[0]
    model = random.choice(MODELS[provider])
    
    # 生成提示词
    prompt = generate_prompt(scenario)
    
    # 生成 Token 数
    if scenario == 'large_token':
        tokens_input = random.randint(8000, 15000)
    elif scenario == 'with_sensitive':
        tokens_input = random.randint(500, 2000)
    else:
        tokens_input = random.randint(200, 4000)
    
    tokens_output = int(tokens_input * random.uniform(0.5, 1.5))
    
    # 计算成本（粗略估算）
    cost = (tokens_input + tokens_output) / 1000 * 0.002
    
    # 检测风险
    risk_level, risk_reasons = detect_risk_level(
        prompt=prompt,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        timestamp=timestamp.isoformat()
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
        session_id=str(uuid4())[:8]
    )
    
    return {
        'timestamp': timestamp.isoformat(),
        'user_id': user_id,
        'department': dept,
        'provider': provider,
        'model': model,
        'prompt': prompt[:500],  # 截断存储
        'prompt_length': len(prompt),
        'response_length': tokens_output * 4,  # 估算
        'tokens_input': tokens_input,
        'tokens_output': tokens_output,
        'cost_usd': round(cost, 4),
        'risk_level': risk_level,
        'risk_reasons': risk_reasons,
        'behavior_tags': behavior_tags,
        'session_id': str(uuid4())[:8],
        'client_ip': f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    }


async def generate_demo_data(days: int = 30, total_records: int = 10000):
    """生成演示数据"""
    print(f"🚀 开始生成 {days} 天的演示数据，约 {total_records} 条记录...")
    
    await init_db()
    
    tagger = BehaviorTagger()
    records = []
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # 按天生成
    current = start_time
    records_per_day = total_records // days
    
    while current < end_time:
        # 确定当天生成多少条
        hour = current.hour
        if 9 <= hour <= 18:  # 工作时间
            count = int(records_per_day * random.uniform(1.2, 1.5) / 10)
        elif 19 <= hour <= 22:  # 晚上
            count = int(records_per_day * random.uniform(0.5, 0.8) / 10)
        else:  # 深夜
            count = int(records_per_day * random.uniform(0.1, 0.3) / 10)
        
        # 每小时的记录分散在 60 分钟内
        for _ in range(max(1, count)):
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            record_time = current.replace(minute=minute, second=second)
            
            if record_time < end_time:
                record = generate_call_record(record_time, tagger)
                records.append(record)
        
        current += timedelta(hours=1)
        
        # 批量插入
        if len(records) >= 1000:
            await insert_audit_logs(records)
            print(f"  已插入 {len(records)} 条记录...")
            records = []
    
    # 插入剩余记录
    if records:
        await insert_audit_logs(records)
        print(f"  已插入 {len(records)} 条记录...")
    
    print(f"\n✅ 演示数据生成完成！")


if __name__ == "__main__":
    asyncio.run(generate_demo_data())
