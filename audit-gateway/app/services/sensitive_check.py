import re
from typing import List, Tuple
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SensitiveChecker:
    """敏感词检测服务"""
    
    def __init__(self):
        self.keywords = []
        self.patterns = []
        self._load_keywords()
    
    def _load_keywords(self):
        """加载敏感词库"""
        # 默认敏感词
        default_keywords = [
            # 个人信息
            '身份证', '手机号', '银行卡', '密码', '验证码',
            # 企业敏感
            '机密', '内部资料', '未公开', '商业计划',
            # 安全相关
            '密钥', 'secret', 'password', 'api_key', 'token'
        ]
        
        self.keywords = default_keywords
        
        # 正则模式
        self.patterns = [
            (re.compile(r'\b1[3-9]\d{9}\b'), 'mobile_phone'),
            (re.compile(r'\b\d{17}[\dXx]\b'), 'id_card'),
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 'email'),
        ]
        
        logger.info(f"Loaded {len(self.keywords)} sensitive keywords and {len(self.patterns)} patterns")
    
    def check(self, contents: List[dict]) -> Tuple[str, List[str], int]:
        """
        检测敏感内容
        返回: (risk_level, matched_words, risk_score)
        """
        all_text = ' '.join([item.get('content', '') for item in contents])
        matched = []
        risk_score = 0
        
        # 关键词匹配
        for keyword in self.keywords:
            if keyword.lower() in all_text.lower():
                matched.append(keyword)
                risk_score += 10
        
        # 正则匹配
        for pattern, pattern_name in self.patterns:
            if pattern.search(all_text):
                matched.append(pattern_name)
                risk_score += 20
        
        # 去重
        matched = list(set(matched))
        
        # 风险等级
        if risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 20:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return risk_level, matched, risk_score


# 全局实例
sensitive_checker = SensitiveChecker()
