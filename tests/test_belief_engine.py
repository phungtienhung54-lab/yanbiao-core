import os
import pytest
import json
import time
from core.belief_engine import BeliefEngine


class TestBeliefEngine:
    """Layer 2: 信念引擎测试"""

    # ====== 补测 1：注册与分类权重 ======
    def test_register_belief(self, belief_engine):
        # 测试世界观（三观）类
        b_worldview = belief_engine.register_belief('user1', '我信奉人人平等', category='worldview')
        assert b_worldview.weight == 0.9
        assert b_worldview.scope == 'persistent'
        
        # 测试偏好类
        b_pref = belief_engine.register_belief('user1', '我喜欢喝咖啡', category='preference')
        assert b_pref.weight == 0.6
        assert b_pref.scope == 'session'
        
        # 测试验证事实类
        b_verified = belief_engine.register_belief('user1', '我今年25岁', category='verified')
        assert b_verified.weight == 0.8
        
        # 测试未知类别（覆盖 weight_map.get 的默认值 0.5 分支）
        b_unknown = belief_engine.register_belief('user1', '其他', category='unknown')
        assert b_unknown.weight == 0.5
        assert b_unknown.scope == 'session'

    # ====== 补测 2：获取用户信念 ======
    def test_get_user_beliefs(self, belief_engine):
        belief_engine.register_belief('user1', '25岁', category='verified')
        belief_engine.register_belief('user1', '北京', category='verified')
        beliefs = belief_engine.get_user_beliefs('user1')
        assert len(beliefs) == 2
        assert all(b.user_id == 'user1' for b in beliefs)

    # ====== 补测 3：核心用户隔离逻辑 ======
    def test_user_isolation_core(self, belief_engine):
        belief_engine.register_belief('user_a', '喜欢苹果', category='preference')
        belief_engine.register_belief('user_b', '喜欢香蕉', category='preference')
        
        a_beliefs = belief_engine.get_user_beliefs('user_a')
        b_beliefs = belief_engine.get_user_beliefs('user_b')
        
        assert len(a_beliefs) == 1
        assert a_beliefs[0].statement == '喜欢苹果'
        assert len(b_beliefs) == 1
        assert b_beliefs[0].statement == '喜欢香蕉'

    # ====== 补测 4：查询逻辑与跨用户隔离（覆盖 123->125） ======
    def test_query_isolation(self, belief_engine):
        belief_engine.register_belief('user_a', '喜欢苹果', category='preference')
        belief_engine.register_belief('user_b', '喜欢香蕉', category='preference')
        
        # 用户 A 查询 "香蕉"，因为用户隔离，应该查不到用户 B 的数据
        # 此调用会触发 if b.user_id != user_id: continue 分支（123->125）
        result = belief_engine.query('香蕉', 'user_a')
        assert len(result) == 0
        
        # 用户 A 查询自己的数据
        result_self = belief_engine.query('苹果', 'user_a')
        assert len(result_self) == 1
        assert result_self[0].statement == '喜欢苹果'

    # ====== 补测 5：调整权重（覆盖 113->114 无效 ID 分支） ======
    def test_adjust_weight(self, belief_engine):
        belief = belief_engine.register_belief('user1', '喜欢茶', category='preference')
        belief_id = belief.id
        
        # 正常调整
        result = belief_engine.adjust_weight(belief_id, 0.9)
        assert result is not None
        assert result.weight == 0.9
        
        # 边界：超过 1.0（应被 clamp 到 1.0）
        result_max = belief_engine.adjust_weight(belief_id, 1.5)
        assert result_max.weight == 1.0
        
        # 边界：小于 0.0（应被 clamp 到 0.0）
        result_min = belief_engine.adjust_weight(belief_id, -0.5)
        assert result_min.weight == 0.0
        
        # 补测：查询不存在的 belief_id（覆盖 113->114）
        result_invalid = belief_engine.adjust_weight("INVALID_ID", 0.5)
        assert result_invalid is None

    # ====== 补测 6：会话隔离检查 ======
    def test_check_session_isolation(self, belief_engine):
        assert belief_engine.check_session_isolation('user1', 'user1') is True
        assert belief_engine.check_session_isolation('user1', 'user2') is False

    # ====== 补测 7：持久化加载（覆盖 63->64 和 65->66） ======
    def test_load_all_persistence(self, tmp_path, monkeypatch):
        # 1. 覆盖 63->64：强制让 os.path.exists 返回 False
        engine_empty = BeliefEngine(str(tmp_path))
        monkeypatch.setattr(os.path, "exists", lambda path: False)
        engine_empty._load_all()
        assert len(engine_empty._beliefs) == 0
        
        # 恢复 os.path.exists 的原始行为
        monkeypatch.undo()
        
        # 2. 覆盖 65->66：在一个空目录上执行 _load_all
        empty_storage = tmp_path / "empty_beliefs"
        empty_storage.mkdir()
        engine2 = BeliefEngine(str(empty_storage))
        # 注意：BeliefEngine.__init__ 会创建 self.storage 并调用 _load_all，此时为空目录
        assert len(engine2._beliefs) == 0
        
        # 3. 正常持久化测试
        engine3 = BeliefEngine(str(tmp_path / "valid_beliefs"))
        engine3.register_belief('user1', '测试持久化', category='preference')
        
        # 重新实例化，触发从磁盘加载
        engine4 = BeliefEngine(str(tmp_path / "valid_beliefs"))
        assert len(engine4.get_user_beliefs('user1')) == 1
        assert engine4.get_user_beliefs('user1')[0].statement == '测试持久化'

    # ====== 补测 8：精确断言统计数据 ======
    def test_stats(self, belief_engine):
        belief_engine.register_belief('user1', '信念1', category='worldview')
        belief_engine.register_belief('user1', '信念2', category='preference')
        belief_engine.register_belief('user2', '信念3', category='verified')
        
        # 全局统计
        stats_all = belief_engine.stats()
        assert stats_all["total"] == 3
        assert stats_all["worldview"] == 1
        assert stats_all["preference"] == 1
        assert stats_all["verified"] == 1
        
        # 特定用户统计
        stats_user1 = belief_engine.stats(user_id='user1')
        assert stats_user1["total"] == 2
        assert stats_user1["worldview"] == 1
        assert stats_user1["preference"] == 1
        assert stats_user1["verified"] == 0

    # ====== 补测 9：空数据下的统计（避免除零错误） ======
    def test_stats_empty(self, belief_engine):
        stats = belief_engine.stats()
        assert stats["total"] == 0
        assert stats["avg_weight"] == 0.0

        # ====== 补测 10：覆盖 66->65 非 JSON 文件跳过分支 ======
    def test_load_all_non_json_file(self, tmp_path):
        """覆盖 66->65：在 beliefs 目录下存在非 .json 文件时，循环应跳过它"""
        # 1. 手动创建存储目录，并放入一个非 JSON 文件
        belief_dir = tmp_path / "beliefs"
        belief_dir.mkdir()
        (belief_dir / "ignore.txt").write_text("not a json file", encoding="utf-8")

        # 2. 实例化引擎，触发 _load_all。此时循环会进入，但 if 判断为 False，触发 66->65
        engine = BeliefEngine(str(tmp_path))
        assert len(engine._beliefs) == 0