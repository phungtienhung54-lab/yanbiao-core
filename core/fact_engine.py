"""
Layer 1: 事实引擎 — 客观事实公理系统
=====================================
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .pif_guard import PIFGuard
from .audit_log import AuditLog  # +++


@dataclass
class Fact:
    id: str
    statement: str
    category: str
    scope: str
    verified: bool
    sources: List[str]
    user_id: Optional[str]
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def citation(self) -> str:
        return f"[FACT-{self.id[:8]}_{self.scope}]"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "category": self.category,
            "scope": self.scope,
            "verified": self.verified,
            "sources": self.sources,
            "user_id": self.user_id,
            "citation": self.citation(),
            "tags": self.tags,
        }


class FactEngine:
    """事实引擎 — 管理客观事实的存储、验证、检索。"""

    def __init__(self, storage_path: str,
                 audit_log: Optional[AuditLog] = None):  # +++
        self.storage = os.path.join(storage_path, "facts")
        os.makedirs(self.storage, exist_ok=True)
        os.makedirs(os.path.join(self.storage, "universal"), exist_ok=True)
        os.makedirs(os.path.join(self.storage, "session"), exist_ok=True)
        self.pif = PIFGuard()
        self._facts: Dict[str, Fact] = {}
        self.audit = audit_log  # +++
        self._load_all()

    def _load_all(self):
        for scope in ["universal", "session"]:
            path = os.path.join(self.storage, scope)
            for fname in os.listdir(path):
                if fname.endswith(".json"):
                    with open(os.path.join(path, fname)) as f:
                        data = json.load(f)
                        fact = Fact(**{k: v for k, v in data.items()
                                       if k in Fact.__dataclass_fields__})
                        self._facts[fact.id] = fact

    def _save(self, fact: Fact):
        scope_dir = os.path.join(self.storage, fact.scope)
        os.makedirs(scope_dir, exist_ok=True)
        path = os.path.join(scope_dir, f"{fact.id}.json")
        with open(path, "w") as f:
            json.dump(fact.to_dict(), f, ensure_ascii=False, indent=2)

    def _gen_id(self, statement: str) -> str:
        return hashlib.md5(statement.encode()).hexdigest()[:8].upper()

    def register_fact(self, statement: str, user_id: Optional[str] = None,
                      sources: Optional[List[str]] = None,
                      tags: Optional[List[str]] = None) -> Tuple[Fact, Dict]:
        # PIF 检查
        pif_alert = self.pif.check(statement, target_individual=user_id)
        if pif_alert.triggered:
            return None, {
                "rejected": True,
                "reason": "PIF: 群体频率不能直接套用于个体",
                "alert": pif_alert.__dict__,
            }

        classification = self.pif.fact_vs_opinion(statement)

        if classification["type"] == "opinion":
            fact = Fact(
                id=self._gen_id(statement + (user_id or "")),
                statement=statement,
                category="user_verified",
                scope="session",
                verified=True,
                sources=sources or ["用户自述"],
                user_id=user_id,
                tags=tags or [],
            )
            self._facts[fact.id] = fact
            self._save(fact)
            if self.audit:  # +++
                self.audit.record(
                    user_id=user_id or "anonymous",
                    module="fact",
                    action="register_opinion",
                    target_id=fact.id,
                    target_type="fact",
                    after=fact.to_dict(),
                    reason="主观观点降级为 session 事实",
                )
            return fact, {
                "rejected": False,
                "classification": classification,
                "note": "主观观点，仅在用户会话内有效，不公开输出",
            }

        fact = Fact(
            id=self._gen_id(statement),
            statement=statement,
            category="objective",
            scope="universal",
            verified=False,
            sources=sources or [],
            user_id=None,
            tags=tags or [],
        )
        self._facts[fact.id] = fact
        self._save(fact)
        if self.audit:  # +++
            self.audit.record(
                user_id=user_id or "anonymous",
                module="fact",
                action="register_objective",
                target_id=fact.id,
                target_type="fact",
                after=fact.to_dict(),
                reason="客观事实待交叉验证",
            )
        return fact, {
            "rejected": False,
            "classification": classification,
            "note": "客观事实，需交叉验证后可公开",
            "needs_verification": True,
        }

    def cross_validate(self, fact_id: str, source: str) -> Dict:
        fact = self._facts.get(fact_id)
        if not fact:
            return {"error": "事实不存在"}

        before = fact.to_dict() if self.audit else None  # +++

        if source not in fact.sources:
            fact.sources.append(source)

        if len(fact.sources) >= 2:
            fact.verified = True

        self._save(fact)

        if self.audit:  # +++
            self.audit.record(
                user_id="system",
                module="fact",
                action="cross_validate",
                target_id=fact.id,
                target_type="fact",
                before=before,
                after=fact.to_dict(),
                reason=f"新增来源: {source}",
            )

        return {
            "fact_id": fact.id,
            "sources": fact.sources,
            "verified": fact.verified,
            "source_count": len(fact.sources),
        }

    def query(self, keyword: str, user_id: Optional[str] = None) -> List[Fact]:
        results = []
        for fact in self._facts.values():
            if keyword in fact.statement or any(keyword in t for t in fact.tags):
                if fact.scope == "universal":
                    if fact.verified:
                        results.append(fact)
                elif fact.scope == "session" and fact.user_id == user_id:
                    results.append(fact)
        return results

    def get_all(self, user_id: Optional[str] = None) -> List[Fact]:
        results = []
        for fact in self._facts.values():
            if fact.scope == "universal" and fact.verified:
                results.append(fact)
            elif fact.scope == "session" and fact.user_id == user_id:
                results.append(fact)
        return results

    def stats(self) -> Dict:
        universal = [f for f in self._facts.values() if f.scope == "universal"]
        session = [f for f in self._facts.values() if f.scope == "session"]
        return {
            "universal_total": len(universal),
            "universal_verified": len([f for f in universal if f.verified]),
            "session_total": len(session),
            "total": len(self._facts),
        }