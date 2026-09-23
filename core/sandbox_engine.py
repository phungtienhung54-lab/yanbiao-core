"""
Layer 3: 沙盒引擎 — 架空现实推演
===================================
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .audit_log import AuditLog  # +++


SANDBOX_DISCLAIMER = "为沙盒推演，已架空现实，不可现实使用"


@dataclass
class ArchivedDefinition:
    id: str
    term: str
    original_definition: str
    new_definition: str
    compressed_at: float
    reason: str
    restored: bool = False


@dataclass
class SandboxSession:
    id: str
    user_id: str
    scenario: str
    rules_overridden: List[str]
    deductions: List[str]
    created_at: float = field(default_factory=time.time)
    disclaimer_added: bool = True


class SandboxEngine:
    """沙盒引擎。"""

    def __init__(self, storage_path: str,
                 audit_log: Optional[AuditLog] = None):  # +++
        self.storage = os.path.join(storage_path, "sandbox")
        os.makedirs(self.storage, exist_ok=True)
        os.makedirs(os.path.join(self.storage, "archives"), exist_ok=True)
        os.makedirs(os.path.join(self.storage, "sessions"), exist_ok=True)
        self._archives: Dict[str, ArchivedDefinition] = {}
        self._sessions: Dict[str, SandboxSession] = {}
        self.audit = audit_log  # +++
        self._load_all()

    def _load_all(self):
        arch_dir = os.path.join(self.storage, "archives")
        if os.path.exists(arch_dir):
            for fname in os.listdir(arch_dir):
                if fname.endswith(".json"):
                    with open(os.path.join(arch_dir, fname), encoding='utf-8') as f:
                        data = json.load(f)
                        a = ArchivedDefinition(**{k: v for k, v in data.items()
                                                if k in ArchivedDefinition.__dataclass_fields__})
                        self._archives[a.id] = a
        sess_dir = os.path.join(self.storage, "sessions")
        if os.path.exists(sess_dir):
            for fname in os.listdir(sess_dir):
                if fname.endswith(".json"):
                    with open(os.path.join(sess_dir, fname), encoding='utf-8') as f:
                        data = json.load(f)
                        s = SandboxSession(**{k: v for k, v in data.items()
                                            if k in SandboxSession.__dataclass_fields__})
                        self._sessions[s.id] = s

    def _save_archive(self, arch: ArchivedDefinition):
        path = os.path.join(self.storage, "archives", f"{arch.id}.json")
        with open(path, "w", encoding='utf-8') as f:
            json.dump(arch.__dict__, f, ensure_ascii=False, indent=2)

    def _save_session(self, sess: SandboxSession):
        path = os.path.join(self.storage, "sessions", f"{sess.id}.json")
        with open(path, "w", encoding='utf-8') as f:
            json.dump(sess.__dict__, f, ensure_ascii=False, indent=2)

    def compress_definition(self, term: str, original_def: str,
                            new_def: str, reason: str = "") -> ArchivedDefinition:
        arch = ArchivedDefinition(
            id=hashlib.md5(f"{term}:{time.time()}".encode()).hexdigest()[:8].upper(),
            term=term,
            original_definition=original_def,
            new_definition=new_def,
            compressed_at=time.time(),
            reason=reason,
        )
        self._archives[arch.id] = arch
        self._save_archive(arch)

        if self.audit:  # +++
            self.audit.record(
                user_id="system",
                module="sandbox",
                action="compress_definition",
                target_id=arch.id,
                target_type="archived_definition",
                after={
                    "term": term,
                    "original": original_def,
                    "new": new_def,
                },
                reason=reason or "定义压缩归档",
            )
        return arch

    def decompress_definition(self, term: str) -> Optional[ArchivedDefinition]:
        for arch in self._archives.values():
            if arch.term == term and not arch.restored:
                arch.restored = True
                self._save_archive(arch)

                if self.audit:  # +++
                    self.audit.record(
                        user_id="system",
                        module="sandbox",
                        action="decompress_definition",
                        target_id=arch.id,
                        target_type="archived_definition",
                        after=arch.__dict__,
                        reason=f"解压定义: {term}",
                    )
                return arch
        return None

    def detect_concept_swap(self, original_term: str, new_term: str,
                            context: str) -> Dict:
        if original_term != new_term:
            has_explicit_swap = any(m in context for m in [
                "重新定义", "概念替换", "换一个说法", "在此上下文中",
                "这里指的是",
            ])
            if not has_explicit_swap:
                return {
                    "detected": True,
                    "original": original_term,
                    "swapped_to": new_term,
                    "severity": "high",
                    "action": "阻断：检测到概念可能被偷换。需显式声明概念替换，或进入沙盒推演。",
                }
        return {"detected": False}

    def create_sandbox(self, user_id: str, scenario: str,
                       rules_to_override: Optional[List[str]] = None) -> SandboxSession:
        sess = SandboxSession(
            id=hashlib.md5(f"{user_id}:{scenario}:{time.time()}".encode()).hexdigest()[:8].upper(),
            user_id=user_id,
            scenario=scenario,
            rules_overridden=rules_to_override or [],
            deductions=[],
        )
        self._sessions[sess.id] = sess
        self._save_session(sess)

        if self.audit:  # +++
            self.audit.record(
                user_id=user_id,
                module="sandbox",
                action="create_sandbox",
                target_id=sess.id,
                target_type="sandbox_session",
                after={
                    "scenario": scenario,
                    "rules_overridden": sess.rules_overridden,
                },
                reason="创建沙盒推演会话",
            )
        return sess

    def add_deduction(self, session_id: str, deduction: str) -> str:
        sess = self._sessions.get(session_id)
        if not sess:
            return "沙盒会话不存在"

        marked = f"{deduction}\n⚠ {SANDBOX_DISCLAIMER}"
        sess.deductions.append(marked)
        self._save_session(sess)

        if self.audit:  # +++
            self.audit.record(
                user_id=sess.user_id,
                module="sandbox",
                action="add_deduction",
                target_id=session_id,
                target_type="sandbox_session",
                after={"deduction_preview": deduction[:100]},
                reason=f"沙盒推演 #{len(sess.deductions)}",
            )
        return marked

    def get_session(self, session_id: str) -> Optional[SandboxSession]:
        return self._sessions.get(session_id)

    def list_sessions(self, user_id: Optional[str] = None) -> List[SandboxSession]:
        if user_id:
            return [s for s in self._sessions.values() if s.user_id == user_id]
        return list(self._sessions.values())

    def list_archives(self) -> List[ArchivedDefinition]:
        return list(self._archives.values())

    def stats(self) -> Dict:
        return {
            "total_sessions": len(self._sessions),
            "total_archives": len(self._archives),
            "active_sandboxes": len([s for s in self._sessions.values() if s.deductions]),
        }