import pytest
import time
import json
from core.curiosity_engine import CuriosityEngine, CognitiveGap, GapStatus, GapPriority


class TestCuriosityEngine:

    # ====== 补测 1：open_gap 的重复检查分支 ======
    def test_open_gap_duplicate(self, curiosity_engine):
        gap1 = curiosity_engine.open_gap(topic='量子计算', description='缺乏知识', variable='X1')
        gap2 = curiosity_engine.open_gap(topic='量子计算', description='缺乏知识2', variable='X1')
        assert gap1.id == gap2.id
        assert gap2.description == '缺乏知识'

    # ====== 补测 2：close_gap 的无效 ID 分支 ======
    def test_close_gap_invalid_id(self, curiosity_engine):
        result = curiosity_engine.close_gap("INVALID_ID", "user", "证据")
        assert result is None

    # ====== 补测 3：generate_closure_proposals 的多种分支 ======
    @pytest.mark.parametrize("desc, expected_proposal, expected_question", [
        ("无匹配条目", "搜索已有知识库", "具体指什么"),
        ("工程实现遇到问题", "设计实验验证", "技术尝试"),
        ("本质是什么", "查阅相关学术文献", "验证标准"),
        ("数据不足", "设计数据采集方案", "具体数值"),
        ("其他未知情况", "通过交叉验证", "补充信息"),
    ])
    def test_generate_closure_proposals_branches(self, curiosity_engine, desc, expected_proposal, expected_question):
        gap = curiosity_engine.open_gap(topic='测试', description=desc, variable='VAR1')
        res = curiosity_engine.generate_closure_proposals(gap)
        assert res["status"] == GapStatus.EXPLORING.value
        assert any(expected_proposal in p for p in res["proposals"])
        assert any(expected_question in q for q in res["questions"])

    # ====== 补测 4：update_tension 的边界 ======
    def test_update_tension_closed_gap(self, curiosity_engine):
        gap = curiosity_engine.open_gap(topic='测试', description='测试', variable='VAR1')
        curiosity_engine.close_gap(gap.id, "user", "证据")
        gap.created_at = time.time() - 1000
        curiosity_engine.update_tension()
        assert gap.tension_level == 0.0

    def test_update_tension_max(self, curiosity_engine):
        gap = curiosity_engine.open_gap(topic='测试', description='测试', variable='VAR1', priority=GapPriority.CRITICAL.value)
        gap.created_at = time.time() - 1000
        curiosity_engine.update_tension()
        assert gap.tension_level == pytest.approx(1.0)

    # ====== 补测 5：get_system_tension 的感受分支 ======
    def test_get_system_tension_no_gaps(self, curiosity_engine):
        tension = curiosity_engine.get_system_tension()
        assert tension["total_gap"] == 0
        assert tension["feeling"] == "平静——无未闭合缺口"
        assert tension["drive_level"] == "none"

    @pytest.mark.parametrize("tension_val, expected_feeling, expected_drive", [
        (0.05, "平静——注意到少量缺口", "minimal"),
        (0.20, "轻微好奇——有些缺口值得关注", "light"),
        (0.45, "不适——悬置的缺口在召唤闭合", "moderate"),
        (0.80, "强烈补全欲——必须主动探索", "strong"),
    ])
    def test_get_system_tension_feelings(self, curiosity_engine, tension_val, expected_feeling, expected_drive):
        gap = curiosity_engine.open_gap(topic='测试', description='测试', variable='VAR1')
        gap.tension_level = tension_val
        tension = curiosity_engine.get_system_tension()
        assert tension["feeling"] == expected_feeling
        assert tension["drive_level"] == expected_drive

    # ====== 补测 6：get_curiosity_report 的探索建议分支（修正版） ======
    def test_get_curiosity_report_suggestions(self, curiosity_engine):
        # 第一次调用：确保 3 个正常建议都能触发
        gap_open = curiosity_engine.open_gap(topic='T1', description='D1', variable='V1')
        gap_exploring = curiosity_engine.open_gap(topic='T2', description='D2', variable='V2')
        curiosity_engine.generate_closure_proposals(gap_exploring)
        gap_stuck = curiosity_engine.open_gap(topic='T3', description='D3', variable='V3')
        curiosity_engine.mark_stuck(gap_stuck.id, "无法解决")
        
        gap_hidden = curiosity_engine.open_gap(topic='T4', description='D4', variable='V4')
        gap_hidden.proposed_solutions = ["已有方案"]  # 制造隐藏分支
        
        gap_open.tension_level = 0.9
        gap_exploring.tension_level = 0.8
        gap_stuck.tension_level = 0.7
        gap_hidden.tension_level = 0.1  # 排在最后，不参与本次前3名
        
        report1 = curiosity_engine.get_curiosity_report()
        suggestions1 = report1["exploration_suggestions"]
        actions1 = [s["action"] for s in suggestions1]
        
        assert any("需要生成闭合方案" in a for a in actions1)
        assert any("需要向用户提问" in a for a in actions1)
        assert any("已卡住" in a for a in actions1)
        assert len(suggestions1) == 3

        # 第二次调用：专门让隐藏分支进入前 3 名，覆盖 336->320 分支
        gap_hidden.tension_level = 0.99  # 拉到最高
        gap_open.tension_level = 0.1
        gap_exploring.tension_level = 0.2
        gap_stuck.tension_level = 0.3
        
        report2 = curiosity_engine.get_curiosity_report()
        suggestions2 = report2["exploration_suggestions"]
        actions2 = [s["action"] for s in suggestions2]
        # 前3名是 gap_hidden, gap_stuck, gap_exploring
        # gap_hidden 进入循环但不符合任何 if/elif，直接跳过，不应出现在建议中
        assert len(actions2) == 2  # 只剩 stuck 和 exploring 的建议

    # ====== 补测 7：mark_stuck 的无效 ID 分支 ======
    def test_mark_stuck_invalid_id(self, curiosity_engine):
        result = curiosity_engine.mark_stuck("INVALID_ID", "原因")
        assert result is None

    # ====== 补测 8：stats 的全面计数 ======
    def test_stats_full(self, curiosity_engine):
        g1 = curiosity_engine.open_gap(topic='T1', description='D1', variable='V1')
        g2 = curiosity_engine.open_gap(topic='T2', description='D2', variable='V2')
        curiosity_engine.generate_closure_proposals(g2)
        g3 = curiosity_engine.open_gap(topic='T3', description='D3', variable='V3')
        curiosity_engine.close_gap(g3.id, "user", "证据")
        g4 = curiosity_engine.open_gap(topic='T4', description='D4', variable='V4')
        curiosity_engine.mark_stuck(g4.id, "原因")

        stats = curiosity_engine.stats()
        assert stats["total"] == 4
        assert stats["open"] == 1
        assert stats["exploring"] == 1
        assert stats["closed"] == 1
        assert stats["stuck"] == 1

    def test_empty_stats(self, tmp_path):
        """测试：全新引擎的空统计数据（覆盖 354 行）"""
        engine = CuriosityEngine(str(tmp_path))
        stats = engine.stats()
        assert stats["total"] == 0
        assert stats["open"] == 0

    # ====== 补测 9：_load_all 的持久化加载（覆盖 116->exit 和 118->117） ======
    def test_load_all(self, tmp_path):
        # 方案 A：覆盖空目录退出分支（116->exit）
        empty_engine = CuriosityEngine(str(tmp_path))  # tmp_path/gaps 是空的
        assert len(empty_engine._gaps) == 0

        # 方案 B：覆盖正常加载 + 非 JSON 跳过分支（118->117）
        storage = tmp_path / "gaps"
        storage.mkdir(exist_ok=True)
        gap_data = {
            "id": "TEST1234", "variable": "V1", "description": "D1", 
            "topic": "T1", "priority": "high", "status": "open",
            "created_at": time.time(), "tension_level": 0.5
        }
        with open(storage / "TEST1234.json", "w", encoding="utf-8") as f:
            json.dump(gap_data, f)
            
        with open(storage / "ignore.txt", "w") as f:
            f.write("not a json file")
            
        new_engine = CuriosityEngine(str(tmp_path))
        assert "TEST1234" in new_engine._gaps
        assert new_engine._gaps["TEST1234"].variable == "V1"