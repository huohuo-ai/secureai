import logging
from typing import List
import asyncio
import aiohttp
from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """告警服务"""
    
    def __init__(self):
        self.webhook_url = settings.ALERT_WEBHOOK_URL
    
    async def send_alert(self, title: str, content: str, level: str = "warning"):
        """发送告警通知"""
        if not self.webhook_url:
            logger.info(f"[ALERT-{level}] {title}: {content}")
            return
        
        try:
            # 钉钉/企微格式
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"**{title}**\n\n{content}"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Alert sent: {title}")
                    else:
                        logger.error(f"Failed to send alert: {resp.status}")
        except Exception as e:
            logger.error(f"Alert send error: {e}")
    
    async def alert_high_risk_content(self, user_id: str, department: str, 
                                       matched_words: List[str], preview: str):
        """高风险内容告警"""
        title = "🚨 AI网关高风险内容告警"
        content = f"""
**用户信息**
- 用户ID: {user_id}
- 部门: {department}

**命中敏感词**
{', '.join(matched_words)}

**内容预览**
{preview[:500]}

**处理建议**
请尽快联系相关人员进行核查。
"""
        await self.send_alert(title, content, level="high")


# 全局实例
alert_service = AlertService()
