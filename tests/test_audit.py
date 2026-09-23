"""
审计日志测试 — 覆盖 AuditLog 所有分支，并验证引擎集成
"""
import os
import json
import time
import pytest

from core.audit_log import AuditLog, AuditEntry
from core.fact_engine import FactEngine
from core.belief_engine import BeliefEngine


class TestAuditLog:

    @pytest.fixture
    def audit_log(self, tmp_path):
        return AuditLog(str(tmp_path))

    # ========== 基础记录 ==========
    def test_record_and_retrieve(self, audit_log):
        entry = audit_log.record(
            user_id="user1",
            module="fact",
            action="register",
            target_id="FACT001",
            target_type="fact",
            after={"statement": "苹果可食用"},
            reason="初始注册",
        )
        assert entry.id is not None
        assert entry.user_id == "user1"
        assert entry.module == "fact"

        history = audit_log.get_history(user_id="user1")
        assert len(history) == 1
        assert history[0].target_id == "FACT001"

    def test_record_with_before_after(self, audit_log):
        audit_log.record(
            user_id="u1", module="belief", action="adjust_weight",
            target_id="B001", target_type="belief",
            before={"weight": 0.6}, after={"weight": 0.9},
            reason="用户要求提高权重",
        )
        entry = audit_log.get_history()[0]
        assert entry.before["weight"] == 0.6
        assert entry.after["weight"] == 0.9
        assert "提高权重" in entry.reason

    def test_record_with_metadata(self, audit_log):
        audit_log.record(
            user_id="u1", module="sandbox", action="deduce",
            target_id="S001", target_type="session",
            session_id="S001", extra_info="test",
        )
        entry = audit_log.get_history()[0]
        assert entry.metadata.get("session_id") == "S001"
        assert entry.metadata.get("extra_info") == "test"

    # ========== get_history 过滤分支 ==========
    def test_get_history_filters(self, audit_log):
        # 造多条不同用户、不同模块、不同 action 的记录
        audit_log.record("u1", "fact", "register", "F1", "fact")
        audit_log.record("u1", "belief", "register", "B1", "belief")
        audit_log.record("u2", "fact", "cross_validate", "F2", "fact")
        audit_log.record("u2", "belief", "adjust_weight", "B2", "belief")

        # 按用户过滤
        u1_history = audit_log.get_history(user_id="u1")
        assert len(u1_history) == 2
        assert all(e.user_id == "u1" for e in u1_history)

        # 按模块过滤
        fact_history = audit_log.get_history(module="fact")
        assert len(fact_history) == 2
        assert all(e.module == "fact" for e in fact_history)

        # 按 action 过滤
        reg_history = audit_log.get_history(action="register")
        assert len(reg_history) == 2
        assert all(e.action == "register" for e in reg_history)

        # 组合过滤
        u1_fact = audit_log.get_history(user_id="u1", module="fact")
        assert len(u1_fact) == 1
        assert u1_fact[0].target_id == "F1"

    def test_get_history_limit(self, audit_log):
        for i in range(10):
            audit_log.record("u1", "fact", "register", f"F{i}", "fact")
        history = audit_log.get_history(limit=3)
        assert len(history) == 3

    def test_get_history_empty(self, audit_log):
        assert audit_log.get_history() == []

    # ========== get_target_history ==========
    def test_get_target_history(self, audit_log):
        # 对同一目标记录两次
        audit_log.record("u1", "belief", "register", "B001", "belief")
        time.sleep(0.01)
        audit_log.record("u1", "belief", "adjust_weight", "B001", "belief",
                         before={"weight": 0.6}, after={"weight": 0.9})

        history = audit_log.get_target_history("B001")
        assert len(history) == 2
        # 应该按时间正序
        assert history[0].action == "register"
        assert history[1].action == "adjust_weight"

    def test_get_target_history_not_found(self, audit_log):
        audit_log.record("u1", "fact", "register", "F1", "fact")
        assert audit_log.get_target_history("NOT_EXIST") == []

    # ========== stats ==========
    def test_stats(self, audit_log):
        audit_log.record("u1", "fact", "register", "F1", "fact")
        audit_log.record("u1", "fact", "cross_validate", "F1", "fact")
        audit_log.record("u1", "belief", "register", "B1", "belief")

        stats = audit_log.stats()
        assert stats["total"] == 3
        assert stats["by_module"]["fact"] == 2
        assert stats["by_module"]["belief"] == 1
        assert stats["by_action"]["register"] == 2

    def test_stats_empty(self, audit_log):
        stats = audit_log.stats()
        assert stats["total"] == 0
        assert stats["by_module"] == {}

    # ========== 持久化加载 ==========
    def test_load_all_persistence(self, tmp_path):
        # 1. 创建并写入
        log1 = AuditLog(str(tmp_path))
        log1.record("u1", "fact", "register", "F1", "fact",
                    after={"statement": "苹果"})
        log1.record("u1", "belief", "register", "B1", "belief")

        # 2. 重新加载
        log2 = AuditLog(str(tmp_path))
        assert len(log2.get_history()) == 2

        # 3. 验证内容一致
        history = log2.get_history()
        target_ids = {e.target_id for e in history}
        assert "F1" in target_ids
        assert "B1" in target_ids

    def test_load_all_empty_dir(self, tmp_path):
        log = AuditLog(str(tmp_path))
        assert log.get_history() == []

    def test_load_all_corrupted_line(self, tmp_path):
        # 手动写入一条正常记录和一条损坏记录
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        log_file = audit_dir / "audit.jsonl"

        valid_entry = {
            "id": "TEST001", "timestamp": time.time(),
            "user_id": "u1", "module": "fact", "action": "register",
            "target_id": "F1", "target_type": "fact",
            "before": None, "after": None, "reason": "", "metadata": {},
        }
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_entry) + "\n")
            f.write("this is not json\n")  # 损坏行
            f.write("\n")  # 空行

        log = AuditLog(str(tmp_path))
        history = log.get_history()
        # 只加载了 1 条正常的
        assert len(history) == 1
        assert history[0].id == "TEST001"

    # ========== AuditEntry.to_dict ==========
    def test_audit_entry_to_dict(self):
        entry = AuditEntry(
            id="X1", timestamp=time.time(),
            user_id="u1", module="fact", action="register",
            target_id="F1", target_type="fact",
        )
        d = entry.to_dict()
        assert d["id"] == "X1"
        assert d["user_id"] == "u1"
        assert d["module"] == "fact"


class TestFactEngineAudit:
    """事实引擎 + 审计集成"""

    @pytest.fixture
    def setup(self, tmp_path, monkeypatch):
        audit = AuditLog(str(tmp_path))
        engine = FactEngine(str(tmp_path), audit_log=audit)
        # mock PIF，保证测试不受规则干扰
        class MockAlert:
            triggered = False
            def __init__(self):
                self.__dict__ = {"triggered": False}
        monkeypatch.setattr(engine.pif, "check",
                            lambda *a, **kw: MockAlert())
        monkeypatch.setattr(engine.pif, "fact_vs_opinion",
                            lambda s: {"type": "fact"})
        return engine, audit

    def test_register_objective_audited(self, setup):
        engine, audit = setup
        fact, _ = engine.register_fact("测试事实A", user_id="u1")
        history = audit.get_history(module="fact")
        assert len(history) == 1
        assert history[0].action == "register_objective"
        assert history[0].target_id == fact.id

    def test_register_opinion_audited(self, setup, monkeypatch):
        engine, audit = setup
        # 让分类返回 opinion
        monkeypatch.setattr(engine.pif, "fact_vs_opinion",
                            lambda s: {"type": "opinion"})
        fact, _ = engine.register_fact("我觉得不错", user_id="u1")
        history = audit.get_history(module="fact")
        assert len(history) == 1
        assert history[0].action == "register_opinion"

    def test_cross_validate_audited(self, setup):
        engine, audit = setup
        fact, _ = engine.register_fact("测试事实B")
        audit._entries.clear()  # 清空以便只观察 cross_validate

        engine.cross_validate(fact.id, "来源A")
        engine.cross_validate(fact.id, "来源B")

        history = audit.get_history(action="cross_validate")
        assert len(history) == 2
        # 第二次验证应记录 before/after
        second = history[0]  # 倒序，最新的在前
        assert second.after["verified"] is True
        assert "来源B" in second.reason


class TestBeliefEngineAudit:
    """信念引擎 + 审计集成"""

    @pytest.fixture
    def setup(self, tmp_path):
        audit = AuditLog(str(tmp_path))
        engine = BeliefEngine(str(tmp_path), audit_log=audit)
        return engine, audit

    def test_register_belief_audited(self, setup):
        engine, audit = setup
        belief = engine.register_belief("u1", "我喜欢安静", category="preference")
        history = audit.get_history(module="belief")
        assert len(history) == 1
        assert history[0].action == "register"
        assert history[0].target_id == belief.id
        assert "preference" in history[0].reason

    def test_adjust_weight_audited(self, setup):
        engine, audit = setup
        belief = engine.register_belief("u1", "我喜欢茶", category="preference")
        audit._entries.clear()

        engine.adjust_weight(belief.id, 0.9)
        history = audit.get_history(action="adjust_weight")
        assert len(history) == 1
        assert history[0].before["weight"] == 0.6
        assert history[0].after["weight"] == 0.9

    def test_adjust_weight_not_found_no_audit(self, setup):
        engine, audit = setup
        result = engine.adjust_weight("NOT_EXIST", 0.9)
        assert result is None
        assert len(audit.get_history()) == 0