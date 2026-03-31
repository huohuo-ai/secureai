import asyncio
from typing import List, Dict
from datetime import datetime
from app.database import ch_client
from app.config import settings
from app.services.sensitive_check import sensitive_checker
import logging
import orjson

logger = logging.getLogger(__name__)


class AuditWriter:
    """审计日志批量写入服务"""
    
    def __init__(self):
        self.buffer: List[Dict] = []
        self.lock = asyncio.Lock()
        self.last_flush = datetime.now()
        
        # 启动定时刷新任务
        asyncio.create_task(self._scheduled_flush())
    
    async def add(self, log: Dict):
        """添加日志到缓冲区"""
        # 补充接收时间
        log['received_at'] = datetime.utcnow().isoformat()
        
        # 敏感词检测
        if settings.ENABLE_SENSITIVE_CHECK:
            try:
                risk_level, words, score = sensitive_checker.check(
                    log.get('request', {}).get('contents', [])
                )
                log['risk_level'] = risk_level
                log['sensitive_words'] = words
                
                # 高风险记录告警
                if risk_level == 'high':
                    asyncio.create_task(self._alert_high_risk(log, words))
                    
            except Exception as e:
                logger.error(f"Sensitive check failed: {e}")
                log['risk_level'] = 'unknown'
        
        async with self.lock:
            self.buffer.append(log)
            
            # 达到批次大小立即刷新
            if len(self.buffer) >= settings.AUDIT_BATCH_SIZE:
                await self._flush()
    
    async def _scheduled_flush(self):
        """定时刷新缓冲区"""
        while True:
            await asyncio.sleep(settings.AUDIT_FLUSH_INTERVAL)
            async with self.lock:
                if self.buffer:
                    await self._flush()
    
    async def _flush(self):
        """将缓冲区写入 ClickHouse"""
        if not self.buffer:
            return
        
        logs_to_write = self.buffer.copy()
        self.buffer = []
        
        try:
            # 使用线程池执行同步的 ClickHouse 写入
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, ch_client.insert_audit_logs, logs_to_write)
            
            logger.debug(f"Flushed {len(logs_to_write)} audit logs to ClickHouse")
            
        except Exception as e:
            logger.error(f"Failed to write audit logs: {e}")
            # 失败时放回缓冲区（限制大小防止内存爆炸）
            remaining_space = 10000 - len(self.buffer)
            if remaining_space > 0:
                self.buffer = logs_to_write[:remaining_space] + self.buffer
                if len(logs_to_write) > remaining_space:
                    logger.error(f"Dropped {len(logs_to_write) - remaining_space} logs due to buffer overflow")
    
    async def _alert_high_risk(self, log: Dict, words: List[str]):
        """高风险告警"""
        logger.warning(f"HIGH RISK detected: user={log['user']['user_id']}, words={words}")
        
        if settings.ALERT_WEBHOOK_URL:
            pass


# 全局实例
audit_writer = AuditWriter()
