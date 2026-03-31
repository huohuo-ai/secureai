"""
Token 行为标签器
"""
from typing import List, Dict
from datetime import datetime, timedelta


class BehaviorTagger:
    """用户行为标签生成器"""
    
    def __init__(self):
        # 用户调用历史（内存缓存，用于检测高频）
        self.user_history: Dict[str, List[datetime]] = {}
    
    def tag(
        self,
        user_id: str,
        prompt: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        timestamp: str,
        model: str,
        session_id: str
    ) -> List[str]:
        """
        为用户调用打标签
        返回: 标签列表
        """
        tags = []
        
        try:
            current_time = datetime.fromisoformat(timestamp)
        except:
            current_time = datetime.now()
        
        # 1. 高频用户：1小时内 > 20 次
        if self._is_high_frequency(user_id, current_time):
            tags.append("高频用户")
        
        # 2. 异常消耗：单次 Token > 8K 或成本 > $0.5
        total_tokens = tokens_input + tokens_output
        if total_tokens > 8000 or cost_usd > 0.5:
            tags.append("异常消耗")
        
        # 3. 测试行为：输入包含测试关键词且调用间隔短
        if self._is_testing_behavior(prompt, user_id, current_time):
            tags.append("测试行为")
        
        # 4. 批量操作：1分钟内 > 5 次相似调用
        if self._is_batch_operation(user_id, prompt, current_time):
            tags.append("批量操作")
        
        # 5. 深夜使用：22:00 - 06:00
        if self._is_night_usage(current_time):
            tags.append("深夜使用")
        
        # 6. 敏感操作：包含敏感关键词
        if self._is_sensitive_operation(prompt):
            tags.append("敏感操作")
        
        # 7. 多模型切换：1小时内使用 > 3 个不同模型
        # 注：这个需要在更上层统计，这里标记为可疑
        if "对比" in prompt or "比较" in prompt or "vs" in prompt.lower():
            tags.append("模型对比")
        
        # 8. 长对话：单会话提示词包含多轮上下文
        if self._is_long_conversation(prompt):
            tags.append("长对话")
        
        # 记录调用历史
        self._record_call(user_id, current_time)
        
        return tags
    
    def _is_high_frequency(self, user_id: str, current_time: datetime) -> bool:
        """检查是否高频调用（1小时内 > 20 次）"""
        if user_id not in self.user_history:
            return False
        
        recent_calls = [
            t for t in self.user_history[user_id]
            if (current_time - t).total_seconds() < 3600
        ]
        return len(recent_calls) > 20
    
    def _is_testing_behavior(self, prompt: str, user_id: str, current_time: datetime) -> bool:
        """检查是否测试行为"""
        test_keywords = ['test', '测试', 'debug', '调试', 'example', '示例']
        has_test_keyword = any(kw in prompt.lower() for kw in test_keywords)
        
        if not has_test_keyword:
            return False
        
        # 检查调用间隔（如果历史上有调用，且间隔 < 10 秒）
        if user_id in self.user_history and self.user_history[user_id]:
            last_call = max(self.user_history[user_id])
            if (current_time - last_call).total_seconds() < 10:
                return True
        
        return False
    
    def _is_batch_operation(self, user_id: str, prompt: str, current_time: datetime) -> bool:
        """检查是否批量操作（简化版：短时间内多次调用）"""
        if user_id not in self.user_history:
            return False
        
        # 1分钟内 > 5 次
        recent_calls = [
            t for t in self.user_history[user_id]
            if (current_time - t).total_seconds() < 60
        ]
        return len(recent_calls) > 5
    
    def _is_night_usage(self, current_time: datetime) -> bool:
        """检查是否深夜使用（22:00 - 06:00）"""
        hour = current_time.hour
        return hour >= 22 or hour < 6
    
    def _is_sensitive_operation(self, prompt: str) -> bool:
        """检查是否敏感操作"""
        sensitive_keywords = ['导出', '下载', 'download', 'export', '复制', 'copy', '备份', 'backup']
        data_keywords = ['数据库', 'db', '用户数据', '订单', '客户', '财务']
        
        has_sensitive = any(kw in prompt.lower() for kw in sensitive_keywords)
        has_data = any(kw in prompt.lower() for kw in data_keywords)
        
        return has_sensitive and has_data
    
    def _is_long_conversation(self, prompt: str) -> bool:
        """检查是否长对话（简化：prompt 长度 > 3000）"""
        return len(prompt) > 3000
    
    def _record_call(self, user_id: str, timestamp: datetime):
        """记录用户调用时间"""
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        
        self.user_history[user_id].append(timestamp)
        
        # 清理 24 小时前的记录
        cutoff = timestamp - timedelta(hours=24)
        self.user_history[user_id] = [
            t for t in self.user_history[user_id]
            if t > cutoff
        ]


def get_tag_color(tag: str) -> str:
    """获取标签颜色"""
    colors = {
        '高频用户': '#722ed1',
        '异常消耗': '#f5222d',
        '测试行为': '#13c2c2',
        '批量操作': '#eb2f96',
        '深夜使用': '#1890ff',
        '敏感操作': '#cf1322',
        '模型对比': '#fa8c16',
        '长对话': '#52c41a'
    }
    return colors.get(tag, '#999')
