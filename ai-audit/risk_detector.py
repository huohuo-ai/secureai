"""
风险等级检测器
"""
import re
from typing import List, Dict, Tuple
from datetime import datetime

# 敏感词配置
SENSITIVE_PATTERNS = {
    'critical': [
        r'\b\d{17}[\dXx]\b',  # 身份证号
        r'\b\d{16,19}\b',      # 银行卡号
        r'(机密文件|绝密|内部资料|未公开|商业机密)',
        r'(密码|password)\s*[=:]\s*\S+',
        r'(AKID|AKSecret|SecretKey)\s*[=:]',
    ],
    'high': [
        r'\b1[3-9]\d{9}\b',    # 手机号
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
        r'(密码|password|密钥|secret|token|apikey)',
        r'(身份证号|银行卡号|手机号|邮箱地址)',
    ],
    'medium': [
        r'(测试|test|debug|调试)',
        r'(临时|temp|草稿|draft)',
    ]
}

# Token 阈值
TOKEN_THRESHOLDS = {
    'critical': 10000,
    'high': 4000,
    'medium': 2000
}

# 深夜时段
NIGHT_HOURS = [0, 1, 2, 3, 4, 5]


def detect_risk_level(
    prompt: str,
    tokens_input: int,
    tokens_output: int,
    timestamp: str,
    user_call_history: List[datetime] = None
) -> Tuple[str, List[str]]:
    """
    检测风险等级
    返回: (risk_level, risk_reasons)
    """
    reasons = []
    
    # 检查敏感词 - Critical
    for pattern in SENSITIVE_PATTERNS['critical']:
        if re.search(pattern, prompt, re.IGNORECASE):
            reasons.append(f"包含高危敏感信息")
            break
    
    # 检查敏感词 - High
    if not reasons:
        for pattern in SENSITIVE_PATTERNS['high']:
            if re.search(pattern, prompt, re.IGNORECASE):
                reasons.append(f"包含敏感词")
                break
    
    # 检查 Token 消耗
    total_tokens = tokens_input + tokens_output
    if total_tokens > TOKEN_THRESHOLDS['critical']:
        reasons.append(f"Token消耗过高({total_tokens})")
    elif total_tokens > TOKEN_THRESHOLDS['high'] and 'Token消耗较高' not in [r for r in reasons]:
        reasons.append(f"Token消耗较高({total_tokens})")
    elif total_tokens > TOKEN_THRESHOLDS['medium'] and not reasons:
        reasons.append(f"Token消耗中等({total_tokens})")
    
    # 检查深夜使用
    try:
        hour = datetime.fromisoformat(timestamp).hour
        if hour in NIGHT_HOURS:
            reasons.append(f"深夜使用({hour}:00)")
    except:
        pass
    
    # 检查频率异常（1小时内 > 50次）
    if user_call_history and len(user_call_history) > 50:
        recent_calls = [
            t for t in user_call_history 
            if (datetime.now() - t).total_seconds() < 3600
        ]
        if len(recent_calls) > 50:
            reasons.append(f"频率异常(1小时内{len(recent_calls)}次)")
    
    # 确定风险等级
    if any("高危" in r or "Token消耗过高" in r or "频率异常" in r for r in reasons):
        return "critical", reasons
    elif any("敏感" in r or "Token消耗较高" in r or "深夜" in r for r in reasons):
        return "high", reasons
    elif reasons:
        return "medium", reasons
    else:
        return "low", []


def get_risk_color(risk_level: str) -> str:
    """获取风险等级颜色"""
    colors = {
        'low': '#52c41a',      # 绿色
        'medium': '#faad14',   # 黄色
        'high': '#fa8c16',     # 橙色
        'critical': '#f5222d'  # 红色
    }
    return colors.get(risk_level, '#999')


def get_risk_label(risk_level: str) -> str:
    """获取风险等级中文标签"""
    labels = {
        'low': '低风险',
        'medium': '中风险',
        'high': '高风险',
        'critical': '严重'
    }
    return labels.get(risk_level, '未知')
