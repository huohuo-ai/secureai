from fastapi import APIRouter, Header, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.models import AuditLog
from app.services.audit_writer import audit_writer
from app.config import settings
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/v1/log")
async def receive_audit_log(
    log: AuditLog,
    x_audit_source: str = Header(None),
    x_request_id: str = Header(None),
    x_edge_node: str = Header(None)
):
    """
    接收网宿边缘节点发送的审计日志
    要求：高性能、低延迟，立即返回
    """
    # 验证来源（可选）
    # if x_audit_source != 'wangsu-edge':
    #     raise HTTPException(status_code=403, detail="Invalid source")
    
    # 转换为 dict 并添加 HTTP Header 信息
    log_dict = log.model_dump()
    log_dict['http_headers'] = {
        'x_audit_source': x_audit_source,
        'x_edge_node': x_edge_node
    }
    
    # 异步写入，不阻塞响应
    await audit_writer.add(log_dict)
    
    # 立即返回，边缘节点不等待
    return {
        "status": "received",
        "request_id": log.request_id,
        "server_time": time.time()
    }


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "audit-gateway"}
