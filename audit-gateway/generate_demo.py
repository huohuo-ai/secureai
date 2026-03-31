#!/usr/bin/env python3
"""
AI 审计网关 - Demo 数据生成脚本
使用方法: docker-compose exec audit-gateway python generate_demo.py
"""

import random
import string
import json
from datetime import datetime, timedelta
from uuid import uuid4
import sys
import os

# 将 app 目录加入路径
sys.path.insert(0, '/app')

from app.database import ch_client
from app.config import settings

# 模拟数据池
DEPARTMENTS = [
    ("研发部", 0.35), ("产品部", 0.20), ("市场部", 0.15),
    ("运营部", 0.15), ("设计部", 0.10), ("财务部", 0.05),
]

USERS = {
    "研发部": ["张三", "李四", "王五", "赵六", "陈七", "刘八", "周九", "吴十"],
    "产品部": ["产品经理小王", "产品经理小李", "产品总监老张", "需求分析师小刘"],
    "市场部": ["市场专员小美", "市场经理大力", "内容运营小陈", "活动策划小王"],
    "运营部": ["数据运营小赵", "用户运营小钱", "活动运营小孙", "社区运营小李"],
    "设计部": ["UI设计师小丽", "UX设计师小芳", "视觉设计师小明", "插画师小红"],
    "财务部": ["会计小周", "财务主管小吴", "审计小郑"],
}

PROVIDERS = [("openai", 0.60), ("claude", 0.25), ("qwen", 0.10), ("azure", 0.05)]

MODELS = {
    "openai": [("gpt-4", 0.40), ("gpt-4-turbo", 0.35), ("gpt-3.5-turbo", 0.25)],
    "claude": [("claude-3-opus", 0.30), ("claude-3-sonnet", 0.50), ("claude-3-haiku", 0.20)],
    "qwen": [("qwen-turbo", 0.60), ("qwen-plus", 0.30), ("qwen-max", 0.10)],
    "azure": [("gpt-4", 0.70), ("gpt-35-turbo", 0.30)],
}

QUERY_TEMPLATES = {
    "code": [
        "帮我优化这段Python代码，提高执行效率",
        "解释这段JavaScript代码的作用",
        "写一个快速排序算法，用Go语言实现",
        "帮我找出这段代码的bug",
        "生成一个React组件，实现文件上传功能",
        "写一个SQL查询，统计每个用户的订单总数",
        "帮我review这段代码，看看有没有安全问题",
        "生成一个Dockerfile，用于部署Python Flask应用",
        "写一个正则表达式，匹配邮箱地址",
        "帮我重构这段代码，使用设计模式",
    ],
    "writing": [
        "帮我写一封给客户的商务邮件",
        "生成一份产品需求文档的模板",
        "帮我润色这段文案，让它更有吸引力",
        "写一份周报，总结本周工作进展",
        "生成一份会议纪要，包含行动项",
        "帮我写一份项目计划书",
        "写一段产品推广文案，突出核心卖点",
        "生成一份用户调研报告的分析框架",
        "帮我翻译这段英文，保持专业术语准确",
        "写一份新员工入职培训手册",
    ],
    "analysis": [
        "分析这组数据，找出趋势和规律",
        "帮我解读这个财务报表的关键指标",
        "分析竞争对手的产品策略",
        "预测下个季度的销售趋势",
        "分析用户流失的原因",
        "帮我做一份SWOT分析",
        "分析这个市场的增长潜力",
        "解读这份合同的风险点",
        "分析这个产品的用户画像",
        "帮我做一份竞品分析报告",
    ],
    "creative": [
        "帮我想一些产品创新的点子",
        "生成一些营销活动的创意方案",
        "帮我想一个品牌slogan",
        "设计一个用户体验优化方案",
        "帮我想一些社交媒体内容创意",
        "生成一些节日促销的主题",
        "帮我想一个产品名称",
        "设计一个用户增长策略",
        "帮我想一些团队建设活动",
        "生成一些视频脚本创意",
    ],
    "learning": [
        "解释机器学习中的梯度下降原理",
        "帮我理解区块链的工作原理",
        "介绍一下大语言模型的技术架构",
        "解释什么是API网关",
        "帮我理解微服务的优缺点",
        "介绍一下云计算的三种服务模式",
        "解释什么是Docker和容器化",
        "帮我理解RESTful API设计规范",
        "介绍一下敏捷开发的方法论",
        "解释什么是CI/CD",
    ],
}

SENSITIVE_KEYWORDS = ["身份证", "银行卡", "密码", "密钥", "secret", "password", "机密文件", "内部资料"]
RISK_LEVELS = [("low", 0.70), ("medium", 0.25), ("high", 0.05)]


def weighted_choice(choices):
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    return choices[-1][0]


def generate_user():
    dept = weighted_choice(DEPARTMENTS)
    user = random.choice(USERS[dept])
    return {
        "user_id": f"{user}_{random.randint(1000, 9999)}",
        "department": dept,
        "project": random.choice(["AI助手", "智能客服", "数据分析", "内容生成", "代码助手"]),
    }


def generate_query_content():
    category = random.choice(list(QUERY_TEMPLATES.keys()))
    template = random.choice(QUERY_TEMPLATES[category])
    contexts = ["", "，要求详细一些", "，请给出具体的例子", "，需要考虑到性能问题", "，时间比较紧急"]
    content = template + random.choice(contexts)
    if random.random() < 0.05:
        content += "，我的身份证号是" + "".join(random.choices(string.digits, k=18))
    return content


def generate_conversation():
    num_messages = random.choices([1, 2, 3, 4, 5], weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0]
    contents = []
    roles = ["user", "assistant", "user", "assistant", "user"]
    for i in range(num_messages):
        role = roles[i]
        if role == "user":
            content = generate_query_content()
        else:
            content = "好的，我来帮您处理。" + "这是详细的解决方案..." * random.randint(1, 5)
        contents.append({"role": role, "content": content, "length": len(content)})
    return contents


def generate_audit_log(timestamp):
    provider = weighted_choice(PROVIDERS)
    model = weighted_choice(MODELS[provider])
    user_info = generate_user()
    conversation = generate_conversation()
    total_chars = sum(c["length"] for c in conversation)
    
    risk_level = weighted_choice(RISK_LEVELS)
    sensitive_words = []
    
    if risk_level == "high" or random.random() < 0.1:
        all_content = " ".join(c["content"] for c in conversation)
        for keyword in SENSITIVE_KEYWORDS:
            if keyword in all_content or random.random() < 0.02:
                sensitive_words.append(keyword)
        if sensitive_words:
            risk_level = "high" if len(sensitive_words) >= 2 else "medium"
    
    has_image = random.random() < 0.08
    
    return {
        "v": "1.0",
        "request_id": str(uuid4()),
        "timestamp": timestamp.isoformat(),
        "received_at": (timestamp + timedelta(milliseconds=random.randint(5, 50))).isoformat(),
        "provider": provider,
        "model": model,
        "stream": random.random() < 0.4,
        "user": {
            "user_id": user_info["user_id"],
            "department": user_info["department"],
            "project": user_info["project"],
            "client_ip": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "user_agent": random.choice([
                "Python/3.11 aiohttp/3.8",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cursor/0.40.0",
            ]),
            "key_type": "company",
        },
        "request": {
            "method": "POST",
            "path": f"/v1/{provider}/chat/completions",
            "content_summary": {
                "message_count": len(conversation),
                "total_chars": total_chars,
                "has_image": has_image,
                "body_truncated": total_chars > 50000,
            },
            "contents": conversation,
        },
        "edge": {
            "node": f"edge-{random.choice(['bj', 'sh', 'gz', 'sz', 'hz', 'cd'])}-{random.randint(1, 99):02d}",
            "start_time": int(timestamp.timestamp() * 1000),
        },
        "risk_level": risk_level,
        "sensitive_words": sensitive_words,
    }


def generate_time_series_data():
    now = datetime.now()
    start_time = now - timedelta(hours=24)
    
    data_points = []
    current = start_time
    
    while current <= now:
        hour = current.hour
        if 9 <= hour <= 18:
            base_count = random.randint(50, 150)
        elif 19 <= hour <= 22:
            base_count = random.randint(20, 60)
        else:
            base_count = random.randint(5, 25)
        
        count = max(1, int(base_count * random.uniform(0.7, 1.3)))
        
        for _ in range(count):
            offset_seconds = random.randint(0, 300)
            record_time = current + timedelta(seconds=offset_seconds)
            data_points.append(generate_audit_log(record_time))
        
        current += timedelta(minutes=5)
    
    return data_points


def print_statistics(data):
    total = len(data)
    print(f"\n总记录数: {total}")
    
    print("\n按部门分布:")
    dept_count = {}
    for item in data:
        dept = item["user"]["department"]
        dept_count[dept] = dept_count.get(dept, 0) + 1
    for dept, count in sorted(dept_count.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {dept:8s}: {count:5d} ({pct:5.1f}%) {bar}")
    
    print("\n按供应商分布:")
    prov_count = {}
    for item in data:
        prov = item["provider"]
        prov_count[prov] = prov_count.get(prov, 0) + 1
    for prov, count in sorted(prov_count.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {prov:8s}: {count:5d} ({pct:5.1f}%)")
    
    print("\n按风险等级分布:")
    risk_count = {}
    for item in data:
        risk = item["risk_level"]
        risk_count[risk] = risk_count.get(risk, 0) + 1
    for risk, count in sorted(risk_count.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
        print(f"  {emoji} {risk:8s}: {count:5d} ({pct:5.1f}%)")
    
    high_risk = [item for item in data if item["risk_level"] == "high"]
    print(f"\n⚠️  高风险记录: {len(high_risk)} 条")


def main():
    print("🚀 AI 审计网关 - Demo 数据生成器")
    print("="*60)
    
    print("\n1. 生成测试数据...")
    data = generate_time_series_data()
    print(f"   生成 {len(data)} 条记录")
    
    print("\n2. 插入到 ClickHouse...")
    
    # 分批插入
    batch_size = 1000
    total = len(data)
    for i in range(0, total, batch_size):
        batch = data[i:i+batch_size]
        ch_client.insert_audit_logs(batch)
        print(f"   已插入 {min(i+batch_size, total)}/{total}")
    
    print_statistics(data)
    
    print("\n" + "="*60)
    print("✅ Demo 数据生成完成！")
    print("\n访问 http://localhost:8000/admin 查看演示数据")


if __name__ == "__main__":
    main()
