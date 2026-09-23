"""SQLite 后端测试"""
import os
import pytest
from core.storage import SQLiteBackend
from core.fact_engine import FactEngine


class TestSQLiteBackend:

    @pytest.fixture
    def db(self, tmp_path):
        return SQLiteBackend(str(tmp_path / "test.db"))

    def test_save_and_load_fact(self, db):
        fact = {
            "id": "F001", "statement": "苹果可食用",
            "category": "objective", "scope": "universal",
            "verified": True, "sources": ["来源A", "来源B"],
            "user_id": None, "created_at": 1234567890.0,
            "tags": ["食物"],
        }
        db.save_fact(fact)
        loaded = db.load_all_facts()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "F001"
        assert loaded[0]["verified"] is True
        assert loaded[0]["sources"] == ["来源A", "来源B"]

    def test_save_fact_upsert(self, db):
        fact = {
            "id": "F001", "statement": "原始", "category": "objective",
            "scope": "universal", "verified": False, "sources": [],
            "user_id": None, "created_at": 1.0, "tags": [],
        }
        db.save_fact(fact)
        fact["statement"] = "更新后"
        fact["verified"] = True
        db.save_fact(fact)
        loaded = db.load_all_facts()
        assert len(loaded) == 1
        assert loaded[0]["statement"] == "更新后"
        assert loaded[0]["verified"] is True

    def test_execute_and_fetch(self, db):
        db.execute("INSERT INTO facts (id, statement, category, scope, verified, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                   ("F002", "测试", "objective", "universal", 0, 1.0))
        row = db.fetch_one("SELECT * FROM facts WHERE id = ?", ("F002",))
        assert row is not None
        assert row["statement"] == "测试"

    def test_persistence_across_instances(self, tmp_path):
        db_path = str(tmp_path / "persist.db")
        db1 = SQLiteBackend(db_path)
        db1.save_fact({
            "id": "F003", "statement": "持久化测试", "category": "objective",
            "scope": "universal", "verified": False, "sources": [],
            "user_id": None, "created_at": 1.0, "tags": [],
        })
        db2 = SQLiteBackend(db_path)
        loaded = db2.load_all_facts()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "F003"


class TestFactEngineSQLite:

    @pytest.fixture
    def engine(self, tmp_path, monkeypatch):
        e = FactEngine(str(tmp_path), use_sqlite=True)
        # mock PIF
        class MockAlert:
            triggered = False
            def __init__(self):
                self.__dict__ = {"triggered": False}
        monkeypatch.setattr(e.pif, "check", lambda *a, **kw: MockAlert())
        monkeypatch.setattr(e.pif, "fact_vs_opinion",
                            lambda s: {"type": "fact"})
        return e

    def test_register_and_query_sqlite(self, engine):
        fact, info = engine.register_fact("SQLite 测试事实")
        assert fact is not None
        assert info["needs_verification"] is True

        # 交叉验证
        engine.cross_validate(fact.id, "来源A")
        engine.cross_validate(fact.id, "来源B")

        # 查询
        results = engine.query("SQLite")
        assert len(results) == 1
        assert results[0].verified is True

    def test_persistence_across_engines(self, tmp_path, monkeypatch):
        # 第一个引擎写入
        e1 = FactEngine(str(tmp_path), use_sqlite=True)
        class MockAlert:
            triggered = False
            def __init__(self):
                self.__dict__ = {"triggered": False}
        monkeypatch.setattr(e1.pif, "check", lambda *a, **kw: MockAlert())
        monkeypatch.setattr(e1.pif, "fact_vs_opinion",
                            lambda s: {"type": "fact"})
        e1.register_fact("持久化事实A")

        # 第二个引擎加载
        e2 = FactEngine(str(tmp_path), use_sqlite=True)
        assert len(e2._facts) == 1

    def test_stats_sqlite(self, engine):
        engine.register_fact("事实1")
        engine.register_fact("事实2")
        stats = engine.stats()
        assert stats["total"] == 2

class TestSQLiteBackendEdgeCases:
    """补测 storage.py 的边界分支"""

    @pytest.fixture
    def db(self, tmp_path):
        return SQLiteBackend(str(tmp_path / "edge.db"))

    def test_fetch_all(self, db):
        """覆盖 fetch_all 分支"""
        db.execute(
            "INSERT INTO facts (id, statement, category, scope, verified, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("F001", "测试A", "objective", "universal", 0, 1.0),
        )
        db.execute(
            "INSERT INTO facts (id, statement, category, scope, verified, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("F002", "测试B", "objective", "universal", 0, 2.0),
        )
        rows = db.fetch_all("SELECT * FROM facts")
        assert len(rows) == 2

    def test_fetch_one_not_found(self, db):
        """覆盖 fetch_one 返回 None 的分支"""
        result = db.fetch_one("SELECT * FROM facts WHERE id = ?", ("NOT_EXIST",))
        assert result is None

    def test_close(self, db):
        """覆盖 close() 方法"""
        db.execute(
            "INSERT INTO facts (id, statement, category, scope, verified, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("F001", "测试", "objective", "universal", 0, 1.0),
        )
        db.close()
        # close 之后应该还能重新建立连接（因为 _get_conn 会重新创建）
        rows = db.fetch_all("SELECT * FROM facts")
        assert len(rows) == 1

    def test_close_without_connection(self, tmp_path):
        """覆盖 close 在未建立连接时的分支（165->exit）"""
        db = SQLiteBackend(str(tmp_path / "noconn.db"))
        # 手动删除连接，模拟从未建立连接的状态
        if hasattr(db._local, "conn"):
            del db._local.conn
        db.close()  # 此时 hasattr 为 False，走空分支，不应报错