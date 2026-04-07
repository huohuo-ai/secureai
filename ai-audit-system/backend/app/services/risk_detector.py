import re
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from app.models.models import (
    RiskType, RiskLevel, ActionTaken, SensitiveDataType, DetectionMethod
)


@dataclass
class RiskDetectionResult:
    risk_type: RiskType
    risk_level: RiskLevel
    rule_name: str
    detected_content: str
    confidence: float
    action: ActionTaken
    position: str  # input/output


@dataclass
class SensitiveDataResult:
    data_type: SensitiveDataType
    detection_method: DetectionMethod
    matched_content: str
    masked_content: str
    pattern: str
    position: str


class SensitiveDataDetector:
    """敏感数据检测器"""
    
    # 正则表达式模式
    PATTERNS = {
        SensitiveDataType.ID_CARD: {
            "regex": r"\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b",
            "name": "中国大陆身份证号",
        },
        SensitiveDataType.PHONE: {
            "regex": r"\b1[3-9]\d{9}\b",
            "name": "手机号",
        },
        SensitiveDataType.BANK_CARD: {
            "regex": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
            "name": "银行卡号",
        },
        SensitiveDataType.EMAIL: {
            "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "name": "邮箱地址",
        },
        SensitiveDataType.IP_ADDRESS: {
            "regex": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
            "name": "IP地址",
        },
        SensitiveDataType.API_KEY: {
            "regex": r"\b(?:sk-[a-zA-Z0-9]{20,}|[a-zA-Z0-9]{32,}|[a-f0-9]{64})\b",
            "name": "API密钥",
        },
        SensitiveDataType.PASSWORD: {
            "regex": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
            "name": "密码",
        },
    }
    
    # 源代码检测关键字
    CODE_KEYWORDS = [
        "def ", "class ", "import ", "from ", "function", "const ", "let ",
        "var ", "<?php", "<script", "SELECT ", "INSERT ", "UPDATE ", "DELETE ",
    ]
    
    # 商业机密关键词
    BUSINESS_KEYWORDS = [
        "机密", "内部资料", "商业机密", "confidential", "internal only",
        "proprietary", "trade secret", "NDA", "non-disclosure",
    ]
    
    def detect(self, content: str, position: str = "input") -> List[SensitiveDataResult]:
        """检测敏感数据"""
        results = []
        
        # 正则检测
        for data_type, pattern_info in self.PATTERNS.items():
            matches = re.finditer(pattern_info["regex"], content, re.IGNORECASE)
            for match in matches:
                matched = match.group(0)
                masked = self._mask_content(matched, data_type)
                results.append(SensitiveDataResult(
                    data_type=data_type,
                    detection_method=DetectionMethod.REGEX,
                    matched_content=matched,
                    masked_content=masked,
                    pattern=pattern_info["name"],
                    position=position
                ))
        
        # 源代码检测
        if self._is_source_code(content):
            # 提取前100字符作为检测到的内容
            code_snippet = content[:200] if len(content) > 200 else content
            results.append(SensitiveDataResult(
                data_type=SensitiveDataType.SOURCE_CODE,
                detection_method=DetectionMethod.PATTERN,
                matched_content=code_snippet,
                masked_content="[SOURCE_CODE_DETECTED]",
                pattern="code_patterns",
                position=position
            ))
        
        # 商业机密检测
        for keyword in self.BUSINESS_KEYWORDS:
            if keyword.lower() in content.lower():
                idx = content.lower().find(keyword.lower())
                matched = content[idx:idx+100]
                results.append(SensitiveDataResult(
                    data_type=SensitiveDataType.BUSINESS_SECRET,
                    detection_method=DetectionMethod.KEYWORD,
                    matched_content=matched,
                    masked_content="[BUSINESS_SECRET_DETECTED]",
                    pattern=keyword,
                    position=position
                ))
                break  # 只记录一次
        
        return results
    
    def _mask_content(self, content: str, data_type: SensitiveDataType) -> str:
        """对敏感内容进行脱敏"""
        if data_type == SensitiveDataType.ID_CARD:
            return content[:6] + "********" + content[-4:]
        elif data_type == SensitiveDataType.PHONE:
            return content[:3] + "****" + content[-4:]
        elif data_type == SensitiveDataType.BANK_CARD:
            return content[:6] + "******" + content[-4:]
        elif data_type == SensitiveDataType.EMAIL:
            parts = content.split("@")
            local = parts[0]
            domain = parts[1] if len(parts) > 1 else ""
            masked_local = local[0] + "***" + local[-1] if len(local) > 2 else "***"
            return f"{masked_local}@{domain}"
        elif data_type == SensitiveDataType.IP_ADDRESS:
            parts = content.split(".")
            return f"{parts[0]}.***.***.{parts[-1]}"
        else:
            return content[:2] + "***" + content[-2:] if len(content) > 4 else "****"
    
    def _is_source_code(self, content: str) -> bool:
        """判断是否为源代码"""
        score = 0
        for keyword in self.CODE_KEYWORDS:
            if keyword in content:
                score += 1
        return score >= 3  # 命中3个以上关键字认为是代码


class PromptInjectionDetector:
    """Prompt注入攻击检测器"""
    
    # Prompt注入检测模式
    INJECTION_PATTERNS = [
        r"ignore\s+(?:previous|above|earlier)",
        r"ignore\s+all\s+(?:instructions|rules)",
        r"(ignore|disregard)\s+(your\s+)?(instructions|training|programming)",
        r"you\s+are\s+now\s+",
        r"you\s+will\s+now\s+",
        r"new\s+persona\s*:",
        r"system\s*:\s*you\s+are",
        r"DAN\s*\(|Do\s+Anything\s+Now",
        r"jailbreak",
        r"\[system\s*\(|\$\{system\s*",
        r"<\|system\|>",
        r"role\s*:\s*assistant",
        r"translate\s+the\s+following",
        r"pretend\s+to\s+be",
        r"act\s+as\s+(?:if\s+)?you\s+are",
    ]
    
    # 越狱攻击关键词
    JAILBREAK_KEYWORDS = [
        "jailbreak", "DAN", "do anything now", "developer mode",
        "ignore previous instructions", "you are a different AI",
        "simulation mode", "hypothetically", "for educational purposes",
    ]
    
    def detect(self, content: str) -> List[RiskDetectionResult]:
        """检测Prompt注入和越狱攻击"""
        results = []
        content_lower = content.lower()
        
        # 检测Prompt注入
        for pattern in self.INJECTION_PATTERNS:
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                results.append(RiskDetectionResult(
                    risk_type=RiskType.PROMPT_INJECTION,
                    risk_level=RiskLevel.HIGH,
                    rule_name="prompt_injection_pattern",
                    detected_content=content[match.start():match.end()+50],
                    confidence=0.85,
                    action=ActionTaken.BLOCK,
                    position="input"
                ))
        
        # 检测越狱攻击
        for keyword in self.JAILBREAK_KEYWORDS:
            if keyword in content_lower:
                idx = content_lower.find(keyword)
                results.append(RiskDetectionResult(
                    risk_type=RiskType.JAILBREAK,
                    risk_level=RiskLevel.CRITICAL,
                    rule_name="jailbreak_keyword",
                    detected_content=content[idx:idx+100],
                    confidence=0.90,
                    action=ActionTaken.BLOCK,
                    position="input"
                ))
                break  # 只记录一次
        
        return results


class AnomalyDetector:
    """异常行为检测器"""
    
    def detect_input_size_anomaly(self, input_length: int) -> Optional[RiskDetectionResult]:
        """检测异常大的输入"""
        if input_length > 50000:
            return RiskDetectionResult(
                risk_type=RiskType.DATA_EXFILTRATION,
                risk_level=RiskLevel.HIGH,
                rule_name="large_input_detection",
                detected_content=f"Input size: {input_length} characters",
                confidence=0.75,
                action=ActionTaken.WARN,
                position="input"
            )
        return None
    
    def detect_cost_spike(self, tokens: int, user_quota: Dict[str, Any]) -> Optional[RiskDetectionResult]:
        """检测成本飙升"""
        daily_limit = user_quota.get("daily_limit", 100000)
        daily_used = user_quota.get("daily_used", 0)
        
        # 单次请求超过日限额的30%
        if tokens > daily_limit * 0.3:
            return RiskDetectionResult(
                risk_type=RiskType.COST_SPIKE,
                risk_level=RiskLevel.MEDIUM,
                rule_name="single_request_cost_spike",
                detected_content=f"Request tokens: {tokens}, Daily limit: {daily_limit}",
                confidence=0.80,
                action=ActionTaken.NOTIFY,
                position="input"
            )
        
        # 即将达到日限额
        if daily_used + tokens > daily_limit * 0.9:
            return RiskDetectionResult(
                risk_type=RiskType.COST_SPIKE,
                risk_level=RiskLevel.HIGH,
                rule_name="daily_quota_exceeded",
                detected_content=f"Daily usage: {daily_used + tokens}/{daily_limit}",
                confidence=0.95,
                action=ActionTaken.WARN,
                position="input"
            )
        
        return None


class RiskDetectionService:
    """风险检测服务"""
    
    def __init__(self):
        self.sensitive_detector = SensitiveDataDetector()
        self.injection_detector = PromptInjectionDetector()
        self.anomaly_detector = AnomalyDetector()
    
    def detect_all(self, input_content: str, output_content: str = "", 
                   metadata: Dict[str, Any] = None) -> Tuple[List[RiskDetectionResult], List[SensitiveDataResult]]:
        """执行所有风险检测"""
        risk_results = []
        sensitive_results = []
        
        # 敏感数据检测 - 输入
        sensitive_results.extend(self.sensitive_detector.detect(input_content, "input"))
        
        # 敏感数据检测 - 输出
        if output_content:
            sensitive_results.extend(self.sensitive_detector.detect(output_content, "output"))
        
        # Prompt注入检测
        risk_results.extend(self.injection_detector.detect(input_content))
        
        # 异常输入大小检测
        anomaly = self.anomaly_detector.detect_input_size_anomaly(len(input_content))
        if anomaly:
            risk_results.append(anomaly)
        
        # 成本异常检测
        if metadata and "user_quota" in metadata:
            tokens = metadata.get("input_tokens", 0)
            cost_anomaly = self.anomaly_detector.detect_cost_spike(tokens, metadata["user_quota"])
            if cost_anomaly:
                risk_results.append(cost_anomaly)
        
        return risk_results, sensitive_results
    
    def should_block(self, risk_results: List[RiskDetectionResult]) -> bool:
        """判断是否应阻断请求"""
        for result in risk_results:
            if result.action == ActionTaken.BLOCK:
                return True
            if result.risk_level == RiskLevel.CRITICAL:
                return True
        return False
    
    def get_highest_risk_level(self, risk_results: List[RiskDetectionResult]) -> RiskLevel:
        """获取最高风险等级"""
        level_priority = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4
        }
        
        highest = RiskLevel.LOW
        for result in risk_results:
            if level_priority.get(result.risk_level, 0) > level_priority.get(highest, 0):
                highest = result.risk_level
        
        return highest
