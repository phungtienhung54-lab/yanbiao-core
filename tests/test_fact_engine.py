import os
import pytest
import time
import json
from core.fact_engine import FactEngine


class TestFactEngine:

    # ====== 通用 Fixture：智能模拟 PIFGuard ======
    @pytest.fixture
    def mock_pif(self, fact_engine, monkeypatch):
        """智能模拟 PIFGuard，让包含'我觉得'的句子降级为观点"""
        class MockAlert:
            triggered = False
            def __init__(self):
                self.__dict__ = {"triggered": False}
        
        # 强制不触发 PIF 拦截
        monkeypatch.setattr(fact_engine.pif, "check", lambda *args, **kwargs: MockAlert())
        
        # 【修正】根据内容智能判断事实/观点
        def mock_fact_vs_opinion(stmt):
            if "我觉得" in stmt or "我认为" in stmt:
                return {"type": "opinion"}
            return {"type": "fact"}
            
        monkeypatch.setattr(fact_engine.pif, "fact_vs_opinion", mock_fact_vs_opinion)
        return fact_engine

    # ====== 补测 1：PIF 拦截分支 (覆盖 102->103) ======
    def test_register_fact_pif_rejected(self, fact_engine, monkeypatch):
        class MockPIFAlert:
            triggered = True
            def __init__(self):
                self.__dict__ = {"triggered": True, "reason": "群体频率套用个体"}
        
        monkeypatch.setattr(fact_engine.pif, "check", lambda *args, **kwargs: MockPIFAlert())
        
        fact, info = fact_engine.register_fact("测试群体归因", user_id="user1")
        assert fact is None
        assert info["rejected"] is True
        assert "PIF" in info["reason"]

    # ====== 补测 2：主观观点降级 (覆盖 112->114) ======
    def test_register_fact_opinion(self, fact_engine, monkeypatch):
        monkeypatch.setattr(fact_engine.pif, "check", lambda *args, **kwargs: type('Alert', (), {'triggered': False})())
        monkeypatch.setattr(fact_engine.pif, "fact_vs_opinion", lambda stmt: {"type": "opinion"})
        
        fact, info = fact_engine.register_fact("我觉得苹果最好吃", user_id="user1")
        
        assert fact is not None
        assert fact.scope == "session"
        assert fact.category == "user_verified"
        assert fact.user_id == "user1"
        assert fact.verified is True
        assert "主观观点" in info["note"]

    # ====== 补测 3：客观事实注册 (覆盖 137->141) ======
    def test_register_fact_objective(self, mock_pif):
        fact, info = mock_pif.register_fact("苹果是一种水果")
        
        assert fact is not None
        assert fact.scope == "universal"
        assert fact.category == "objective"
        assert fact.verified is False
        assert info["needs_verification"] is True

    # ====== 补测 4：交叉验证逻辑 (覆盖 158->161 和 161->162) ======
    def test_cross_validate_logic(self, mock_pif):
        fact, _ = mock_pif.register_fact("水在标准大气压下100°C沸腾")
        fact_id = fact.id
        
        res1 = mock_pif.cross_validate(fact_id, "来源A")
        assert res1["source_count"] == 1
        assert res1["verified"] is False
        
        # 重复添加同一个来源
        res2 = mock_pif.cross_validate(fact_id, "来源A")
        assert res2["source_count"] == 1
        assert res2["verified"] is False
        
        # 添加第二个不同来源
        res3 = mock_pif.cross_validate(fact_id, "来源B")
        assert res3["source_count"] == 2
        assert res3["verified"] is True
        
        res4 = mock_pif.cross_validate("INVALID_ID", "来源C")
        assert "error" in res4

    # ====== 补测 5：查询逻辑 (覆盖 181->184 和 182->183) ======
    def test_query_logic(self, mock_pif):
        # 未验证的 universal
        mock_pif.register_fact("未经证实的消息")
        
        # 已验证的 universal
        fact_verified, _ = mock_pif.register_fact("地球是圆的")
        mock_pif.cross_validate(fact_verified.id, "来源A")
        mock_pif.cross_validate(fact_verified.id, "来源B")
        
        # session 事实（包含'我觉得'，会被智能 mock 降级）
        mock_pif.register_fact("我觉得今天很冷", user_id="user1")
        
        # 未验证的 universal 查不到
        res_unverified = mock_pif.query("未经证实")
        assert len(res_unverified) == 0
        
        # 已验证的 universal 能查到
        res_verified = mock_pif.query("地球")
        assert len(res_verified) == 1
        assert res_verified[0].verified is True
        
        # session 事实能查到 (覆盖 182->183)
        res_session = mock_pif.query("今天很冷", user_id="user1")
        assert len(res_session) == 1
        assert res_session[0].scope == "session"
        
        # 用户不匹配查不到
        res_wrong_user = mock_pif.query("今天很冷", user_id="user2")
        assert len(res_wrong_user) == 0

    # ====== 补测 6：get_all 过滤 (覆盖 192->193 和 194->195) ======
    def test_get_all_logic(self, mock_pif):
        mock_pif.register_fact("客观事实A")
        mock_pif.register_fact("我觉得主观观点B", user_id="user1")
        
        # 用户1 应看到自己的 session 事实 (覆盖 192->193, 194->195)
        all_user1 = mock_pif.get_all(user_id="user1")
        assert len(all_user1) == 1
        assert all_user1[0].statement == "我觉得主观观点B"
        
        # 用户2 看不到
        all_user2 = mock_pif.get_all(user_id="user2")
        assert len(all_user2) == 0

    # ====== 补测 7：持久化加载 (覆盖 74->75) ======
    def test_load_all_persistence(self, tmp_path, monkeypatch):
        engine1 = FactEngine(str(tmp_path))
        # 临时 mock 分类逻辑
        monkeypatch.setattr(engine1.pif, "check", lambda *args, **kwargs: type('Alert', (), {'triggered': False})())
        monkeypatch.setattr(engine1.pif, "fact_vs_opinion", lambda stmt: {"type": "opinion"})
        
        engine1.register_fact("测试持久化事实", user_id="user1")
        
        engine2 = FactEngine(str(tmp_path))
        facts = engine2.get_all(user_id="user1")
        assert len(facts) == 1
        assert facts[0].statement == "测试持久化事实"
        
        # 触发非 JSON 文件的跳过逻辑 (覆盖 74->75)
        with open(os.path.join(str(tmp_path), "facts", "session", "ignore.txt"), "w") as f:
            f.write("not json")
            
        engine3 = FactEngine(str(tmp_path))
        assert len(engine3.get_all(user_id="user1")) == 1

    # ====== 补测 8：精确断言统计数据 ======
    def test_stats_full(self, mock_pif):
        mock_pif.register_fact("事实1")
        # 【修正】使用包含'我觉得'的句子，确保被识别为 session 事实
        mock_pif.register_fact("我觉得事实2", user_id="user1")
        
        fact_verified = [f for f in mock_pif._facts.values() if f.statement == "事实1"][0]
        mock_pif.cross_validate(fact_verified.id, "来源A")
        mock_pif.cross_validate(fact_verified.id, "来源B")
        
        stats = mock_pif.stats()
        assert stats["total"] == 2
        assert stats["universal_total"] == 1
        assert stats["universal_verified"] == 1
        assert stats["session_total"] == 1

        # ====== 补测 6：get_all 过滤（修正版，覆盖 192->193 和 194->195） ======
    def test_get_all_logic(self, mock_pif):
        # 1. 注册一个 universal 事实，并交叉验证使其 verified = True（覆盖 192->193）
        fact_universal, _ = mock_pif.register_fact("客观事实A")
        mock_pif.cross_validate(fact_universal.id, "来源A")
        mock_pif.cross_validate(fact_universal.id, "来源B")
        
        # 2. 注册一个 session 事实（覆盖 194->195）
        mock_pif.register_fact("我觉得主观观点B", user_id="user1")
        
        # 3. 用户1 应看到 1 条已验证 universal + 1 条自己的 session
        all_user1 = mock_pif.get_all(user_id="user1")
        assert len(all_user1) == 2
        statements = [f.statement for f in all_user1]
        assert "客观事实A" in statements
        assert "我觉得主观观点B" in statements
        
        # 4. 用户2 应只看到 1 条已验证 universal，看不到别人的 session
        all_user2 = mock_pif.get_all(user_id="user2")
        assert len(all_user2) == 1
        assert all_user2[0].statement == "客观事实A"