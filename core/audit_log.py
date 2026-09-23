"""
审计日志模块 — 记录系统所有关键操作的完整轨迹
================================================

核心目标：让每一次决策、每一次数据变更都可追溯。

设计原则：
- JSONL 格式（每行一条 JSON），追加写入，性能好
- 每条记录包含 who / when / module / action / target / before / after / reason
- 通过 storage_path 持久化，重启后自动加载
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class AuditEntry:
    """单条审计记录"""
    id: str
    timestamp: float
    user_id: str
    module: str          # "fact" | "belief" | "conflict" | "orchestrator" | "sandbox"
    action: str          # "register" | "update" | "cross_validate" | "resolve" | "delete"
    target_id: str       # 被操作对象的 id
    target_type: str     # "fact" | "belief" | "conflict" | "message"
    before: Optional[Dict] = None   # 变更前的快照（可选）
    after: Optional[Dict] = None    # 变更后的快照（可选）
    reason: str = ""                # 变更原因
    metadata: Dict = field(default_factory=dict)  # 额外信息

    def to_dict(self) -> Dict:
        return asdict(self)


class AuditLog:
    """审计日志 — 追加式记录所有关键操作。"""

    def __init__(self, storage_path: str):
        self.storage = os.path.join(storage_path, "audit")
        os.makedirs(self.storage, exist_ok=True)
        self._log_file = os.path.join(self.storage, "audit.jsonl")
        self._entries: List[AuditEntry] = []
        self._load_all()

    def _load_all(self):
        """从 JSONL 文件加载所有历史记录。"""
        if not os.path.exists(self._log_file):
            return
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = AuditEntry(**{
                        k: v for k, v in data.items()
                        if k in AuditEntry.__dataclass_fields__
                    })
                    self._entries.append(entry)
                except (json.JSONDecodeError, TypeError):
                    continue  # 跳过损坏的行

    def _append(self, entry: AuditEntry):
        """追加写入 JSONL 文件。"""
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def _gen_id(self, user_id: str, action: str) -> str:
        return hashlib.md5(
            f"{user_id}:{action}:{time.time()}".encode()
        ).hexdigest()[:12].upper()

    def record(self, user_id: str, module: str, action: str,
               target_id: str, target_type: str,
               before: Optional[Dict] = None,
               after: Optional[Dict] = None,
               reason: str = "",
               **metadata) -> AuditEntry:
        """记录一条审计条目。"""
        entry = AuditEntry(
            id=self._gen_id(user_id, action),
            timestamp=time.time(),
            user_id=user_id,
            module=module,
            action=action,
            target_id=target_id,
            target_type=target_type,
            before=before,
            after=after,
            reason=reason,
            metadata=metadata,
        )
        self._entries.append(entry)
        self._append(entry)
        return entry

    def get_history(self, user_id: Optional[str] = None,
                    module: Optional[str] = None,
                    action: Optional[str] = None,
                    limit: int = 100) -> List[AuditEntry]:
        """查询审计历史，按时间倒序返回。"""
        results = self._entries

        if user_id is not None:
            results = [e for e in results if e.user_id == user_id]
        if module is not None:
            results = [e for e in results if e.module == module]
        if action is not None:
            results = [e for e in results if e.action == action]

        results = sorted(results, key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def get_target_history(self, target_id: str) -> List[AuditEntry]:
        """获取某个对象（事实/信念/矛盾）的完整变更历史，按时间正序。"""
        results = [e for e in self._entries if e.target_id == target_id]
        return sorted(results, key=lambda e: e.timestamp)

    def stats(self) -> Dict:
        """审计统计。"""
        by_module: Dict[str, int] = {}
        by_action: Dict[str, int] = {}
        for e in self._entries:
            by_module[e.module] = by_module.get(e.module, 0) + 1
            by_action[e.action] = by_action.get(e.action, 0) + 1
        return {
            "total": len(self._entries),
            "by_module": by_module,
            "by_action": by_action,
        }