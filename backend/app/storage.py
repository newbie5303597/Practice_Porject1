"""工单存储模块：封装对 Issue 相关的数据库操作。"""
from typing import Optional, List, Dict, Any


def _ensure_history_list(history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """避免 history 为 None，统一转换为列表。"""
    return list(history or [])