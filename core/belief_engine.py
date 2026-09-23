"""
Layer 2: 信念系统 — 用户数据基底 + 会话隔离
=============================================
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .audit_log import AuditLog  # +++


@dataclass
class Belief:
    id: str
    user_id: str
    statement: str
    weight: float
    category: str
    verified: bool
    scope: str
    source: str
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}


class BeliefEngine:
    """信念引擎 — 管理用户个人数据，会话隔离。"""

    WORLDVIEW_WEIGHT = 0.9
    PREFERENCE_WEIGHT = 0.6
    VERIFIED_WEIGHT = 0.8

    def __init__(self, storage_path: str,
                 audit_log: Optional[AuditLog] = None):  # +++
        self.storage = os.path.join(storage_path, "beliefs")
        os.makedirs(self.storage, exist_ok=True)
        self._beliefs: Dict[str, Belief] = {}
        self.audit = audit_log  # +++
        self._load_all()

    def _load_all(self):
        if not os.path.exists(self.storage):
            return
        for fname in os.listdir(self.storage):
            if fname.endswith(".json"):
                with open(os.path.join(self.storage, fname)) as f:
                    data = json.load(f)
                    belief = Belief(**{k: v for k, v in data.items()
                                       if k in Belief.__dataclass_fields__})
                    self._beliefs[belief.id] = belief

    def _save(self, belief: Belief):
        path = os.path.join(self.storage, f"{belief.id}.json")
        with open(path, "w") as f:
            json.dump(belief.to_dict(), f, ensure_ascii=False, indent=2)

    def _gen_id(self, user_id: str, statement: str) -> str:
        return hashlib.md5(f"{user_id}:{statement}".encode()).hexdigest()[:8].upper()

    def register_belief(self, user_id: str, statement: str,
                        category: str = "preference",
                        source: str = "用户自述",
                        tags: Optional[List[str]] = None) -> Belief:
        weight_map = {
            "worldview": self.WORLDVIEW_WEIGHT,
            "preference": self.PREFERENCE_WEIGHT,
            "verified": self.VERIFIED_WEIGHT,
        }
        belief = Belief(
            id=self._gen_id(user_id, statement),
            user_id=user_id,
            statement=statement,
            weight=weight_map.get(category, 0.5),
            category=category,
            verified=True,
            scope="persistent" if category == "worldview" else "session",
            source=source,
            tags=tags or [],
        )
        self._beliefs[belief.id] = belief
        self._save(belief)
        if self.audit:  # +++
            self.audit.record(
                user_id=user_id,
                module="belief",
                action="register",
                target_id=belief.id,
                target_type="belief",
                after=belief.to_dict(),
                reason=f"用户注册信念 (category={category})",
            )
        return belief

    def get_user_beliefs(self, user_id: str) -> List[Belief]:
        return [b for b in self._beliefs.values() if b.user_id == user_id]

    def adjust_weight(self, belief_id: str, new_weight: float):
        belief = self._beliefs.get(belief_id)
        if belief:
            before = belief.to_dict() if self.audit else None  # +++
            old_weight = belief.weight
            belief.weight = max(0.0, min(1.0, new_weight))
            self._save(belief)
            if self.audit:  # +++
                self.audit.record(
                    user_id=belief.user_id,
                    module="belief",
                    action="adjust_weight",
                    target_id=belief.id,
                    target_type="belief",
                    before=before,
                    after=belief.to_dict(),
                    reason=f"权重从 {old_weight} 调整为 {belief.weight}",
                )
            return belief
        return None

    def query(self, keyword: str, user_id: str) -> List[Belief]:
        results = []
        for b in self._beliefs.values():
            if b.user_id != user_id:
                continue
            if keyword in b.statement or any(keyword in t for t in b.tags):
                results.append(b)
        return results

    def check_session_isolation(self, user_id: str, query_user_id: str) -> bool:
        return user_id == query_user_id

    def stats(self, user_id: Optional[str] = None) -> Dict:
        beliefs = self.get_user_beliefs(user_id) if user_id \
            else list(self._beliefs.values())
        return {
            "total": len(beliefs),
            "worldview": len([b for b in beliefs if b.category == "worldview"]),
            "preference": len([b for b in beliefs if b.category == "preference"]),
            "verified": len([b for b in beliefs if b.category == "verified"]),
            "avg_weight": sum(b.weight for b in beliefs) / max(len(beliefs), 1),
        }