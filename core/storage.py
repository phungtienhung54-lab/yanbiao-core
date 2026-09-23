"""
存储后端 — 支持 JSON 文件与 SQLite 两种实现
================================================

设计原则：
- SQLite 用于性能关键场景（大数据量、批量写入）
- JSON 保留用于调试和轻量场景
- 两个后端共享相同的数据结构，引擎层无需感知差异
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Dict, List, Optional


class SQLiteBackend:
    """SQLite 存储后端 — 线程安全的连接池。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """每个线程一个独立连接。"""
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        """初始化所有表结构。"""
        with self._lock:
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS facts (
                    id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    category TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    sources TEXT NOT NULL DEFAULT '[]',
                    user_id TEXT,
                    created_at REAL NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_facts_scope ON facts(scope);
                CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id);

                CREATE TABLE IF NOT EXISTS beliefs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    weight REAL NOT NULL,
                    category TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    scope TEXT NOT NULL,
                    source TEXT,
                    created_at REAL NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_beliefs_user ON beliefs(user_id);

                CREATE TABLE IF NOT EXISTS sandbox_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    rules_overridden TEXT NOT NULL DEFAULT '[]',
                    deductions TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    disclaimer_added INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS archives (
                    id TEXT PRIMARY KEY,
                    term TEXT NOT NULL,
                    original_definition TEXT,
                    new_definition TEXT,
                    compressed_at REAL NOT NULL,
                    reason TEXT,
                    restored INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS audit_entries (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    user_id TEXT NOT NULL,
                    module TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT,
                    reason TEXT,
                    metadata_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_entries(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_entries(target_id);
            """)
            conn.commit()

    # ========== Facts ==========
    def save_fact(self, fact: Dict):
        """保存单条事实（单次 commit）。"""
        conn = self._get_conn()
        with self._lock:
            conn.execute("""
                INSERT OR REPLACE INTO facts
                (id, statement, category, scope, verified, sources, user_id, created_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact["id"], fact["statement"], fact["category"], fact["scope"],
                1 if fact["verified"] else 0,
                json.dumps(fact.get("sources", []), ensure_ascii=False),
                fact.get("user_id"),
                fact.get("created_at", 0),
                json.dumps(fact.get("tags", []), ensure_ascii=False),
            ))
            conn.commit()

    def save_facts_batch(self, facts: List[Dict]):
        """批量保存事实（一次 commit）——比逐条保存快 5~10 倍。"""
        if not facts:
            return
        conn = self._get_conn()
        with self._lock:
            for fact in facts:
                conn.execute("""
                    INSERT OR REPLACE INTO facts
                    (id, statement, category, scope, verified, sources, user_id, created_at, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fact["id"], fact["statement"], fact["category"], fact["scope"],
                    1 if fact["verified"] else 0,
                    json.dumps(fact.get("sources", []), ensure_ascii=False),
                    fact.get("user_id"),
                    fact.get("created_at", 0),
                    json.dumps(fact.get("tags", []), ensure_ascii=False),
                ))
            conn.commit()

    def load_all_facts(self) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM facts").fetchall()
        return [self._row_to_fact(r) for r in rows]

    @staticmethod
    def _row_to_fact(row) -> Dict:
        return {
            "id": row["id"],
            "statement": row["statement"],
            "category": row["category"],
            "scope": row["scope"],
            "verified": bool(row["verified"]),
            "sources": json.loads(row["sources"] or "[]"),
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "tags": json.loads(row["tags"] or "[]"),
        }

    # ========== 通用 ==========
    def execute(self, sql: str, params: tuple = ()):
        conn = self._get_conn()
        with self._lock:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetch_all(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(sql, params).fetchall()

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        conn = self._get_conn()
        return conn.execute(sql, params).fetchone()

    def close(self):
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            del self._local.conn