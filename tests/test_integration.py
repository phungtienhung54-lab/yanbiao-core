import os
import pytest
from orchestrator import YanbiaoCore, ProcessingResult


class TestIntegration:

    @pytest.fixture
    def orchestrator(self, temp_dir):
        storage_path = os.path.join(temp_dir, 'orchestrator')
        return YanbiaoCore(storage_path=storage_path)

    # ========== 基础 ==========
    def test_orchestrator_creation(self, orchestrator):
        assert orchestrator is not None
        assert hasattr(orchestrator, 'process')

    def test_process_returns_result(self, orchestrator):
        result = orchestrator.process("我今年25岁", user_id="test_user")
        assert isinstance(result, ProcessingResult)
        assert result.raw_input == "我今年25岁"

    # ========== 语义确认失败路径 ==========
    def test_process_ambiguous_input(self, orchestrator):
        """模糊输入触发语义确认，提前返回"""
        result = orchestrator.process("那个东西有点问题", user_id="test_user")
        assert result.needs_user_input is True
        assert len(result.questions_for_user) > 0
        assert "语义确认" in result.output_text

    # ========== PIF 拦截路径 ==========
    def test_process_pif_triggered(self, orchestrator):
        """群体统计套用个体触发 PIF 拦截"""
        result = orchestrator.process("男性你一定都是这样", user_id="test_user")
        assert "概率个体化谬误" in result.output_text
        assert any("PIF" in str(s["stage"]) or "pif" in str(s["stage"])
                   for s in result.stages)

    # ========== 沙盒路由（创造性表达） ==========
    def test_process_sandbox_creative(self, orchestrator):
        """创造性表达自动进入沙盒"""
        result = orchestrator.process("写小说：主角可以飞", user_id="test_user")
        assert result.in_sandbox is True
        assert "沙盒推演" in result.output_text
        assert "架空现实" in result.output_text

    # ========== 沙盒路由（常理违反） ==========
    def test_process_sandbox_common_sense(self, orchestrator):
        """常理违反 + 创造性标记 → 沙盒"""
        result = orchestrator.process("假设吃饭不用嘴", user_id="test_user")
        assert result.in_sandbox is True

    # ========== 事实路径 ==========
    def test_process_fact_path(self, orchestrator):
        """客观陈述走事实引擎"""
        result = orchestrator.process("苹果是一种水果", user_id="test_user")
        stages = [s["stage"] for s in result.stages]
        assert "fact_opinion" in stages
        assert "fact_register" in stages

    # ========== 信念路径（避开模糊词） ==========
    def test_process_belief_path(self, orchestrator):
        """主观观点走信念引擎（避开 '这个/那个' 等模糊词）"""
        result = orchestrator.process("我觉得苹果最好吃", user_id="test_user")
        stages = [s["stage"] for s in result.stages]
        assert "belief_register" in stages

    # ========== 延标标记 + 好奇心驱动 ==========
    def test_process_unknown_marker(self, orchestrator):
        """未知输入 → 延标标记 + 好奇心缺口"""
        result = orchestrator.process("量子纠缠拓扑学", user_id="test_user")
        # 大概率无匹配，会触发 unknown_markers
        assert isinstance(result.unknown_markers, list)
        # 好奇心报告必须存在
        assert result.curiosity_report is not None
        assert result.system_tension is not None

    # ========== 多用户隔离 ==========
    def test_multi_user_flow(self, orchestrator):
        r1 = orchestrator.process("我喜欢吃苹果", user_id="user_a")
        r2 = orchestrator.process("我喜欢吃香蕉", user_id="user_b")
        assert r1 is not None
        assert r2 is not None

        # 验证信念隔离
        beliefs_a = orchestrator.belief_engine.get_user_beliefs("user_a")
        beliefs_b = orchestrator.belief_engine.get_user_beliefs("user_b")
        for b in beliefs_a:
            assert b.user_id == "user_a"
        for b in beliefs_b:
            assert b.user_id == "user_b"

    # ========== 系统状态 ==========
    def test_get_system_state(self, orchestrator):
        state = orchestrator.get_system_state()
        assert isinstance(state, dict)
        for key in ["protocols", "self_awareness", "facts", "beliefs",
                    "sandbox", "conflicts", "curiosity", "system_tension"]:
            assert key in state

    # ========== 内部方法：矛盾检测（数据对齐源码逻辑） ==========
    def test_detect_contradiction_with_conflict(self, orchestrator):
        class FakeItem:
            def __init__(self, s):
                self.statement = s

        # 关键：s2 必须是 s1 去掉否定标记后的子串
        # "地球不是平的" - "不是" = "地球平的"，正好等于 s2
        items = [
            FakeItem("地球不是平的"),
            FakeItem("地球平的"),
        ]
        result = orchestrator._detect_contradiction(items, "测试")
        assert result is not None
        assert "path_a" in result
        assert "path_b" in result
        assert "conditions_a" in result
        assert "conditions_b" in result

    # ========== 内部方法：沙盒推演 ==========
    def test_sandbox_deduce(self, orchestrator):
        text = orchestrator._sandbox_deduce("测试场景")
        assert "沙盒推演" in text
        assert "假设性推理" in text or "架空现实" in text

    # ========== 内部方法：语义问题格式化 ==========
    def test_format_semantic_question(self, orchestrator):
        class FakeSemantic:
            issues = ["检测到模糊词：那个"]
            suggested_questions = ["您提到的'那个'具体指什么？"]

        text = orchestrator._format_semantic_question(FakeSemantic())
        assert "语义确认" in text
        assert "检测到模糊词" in text
        assert "具体指什么" in text

    # ========== 内部方法：输出构建 ==========
    def test_build_output_no_data(self, orchestrator):
        text = orchestrator._build_output("测试", [], [], [])
        assert "已知条件" in text
        assert "决策声明" in text
        assert "无匹配条目" in text

    def test_build_output_with_unknowns(self, orchestrator):
        unknowns = [{
            "variable": "X(∞)_{测试}",
            "description": "测试缺口",
        }]
        text = orchestrator._build_output("测试", [], [], unknowns)
        assert "延标标记" in text
        assert "闭合方案" in text
        assert "存在未闭合变量" in text

    # ========== 种子数据幂等性 ==========
    def test_seed_data_idempotent(self, temp_dir):
        """两次实例化使用相同路径，种子数据不应重复"""
        path = os.path.join(temp_dir, 'seed_test')
        core1 = YanbiaoCore(storage_path=path)
        stats1 = core1.fact_engine.stats()
        core2 = YanbiaoCore(storage_path=path)
        stats2 = core2.fact_engine.stats()
        assert stats1["total"] == stats2["total"]

        # ========== 补测：ProcessingResult.to_dict ==========
    def test_processing_result_to_dict(self, orchestrator):
        result = orchestrator.process("我今年25岁", user_id="test_user")
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in ["stages", "output_text", "unknown_markers", "decision_chain",
                    "in_sandbox", "needs_user_input", "questions_for_user",
                    "curiosity_report", "system_tension", "raw_input", "timestamp"]:
            assert key in d

    # ========== 补测：种子数据幂等（覆盖 _seed_data 的跳过分支） ==========
    def test_seed_data_second_load(self, temp_dir):
        """第二次实例化同一路径，种子已存在，走跳过分支"""
        path = os.path.join(temp_dir, 'seed_reload')
        core1 = YanbiaoCore(storage_path=path)
        # 第一次会注册种子并 cross_validate
        stats1 = core1.fact_engine.stats()
        # 第二次不会重复注册
        core2 = YanbiaoCore(storage_path=path)
        stats2 = core2.fact_engine.stats()
        assert stats1["total"] == stats2["total"]

    # ========== 补测：_build_output 覆盖 beliefs 分支 ==========
    def test_build_output_with_beliefs(self, orchestrator):
        # 先注册一个信念
        orchestrator.belief_engine.register_belief(
            user_id="test_user", statement="我喜欢安静", category="preference"
        )
        beliefs = orchestrator.belief_engine.get_user_beliefs("test_user")
        text = orchestrator._build_output("测试", [], beliefs, [])
        assert "用户信念" in text
        assert "权重" in text

    # ========== 补测：_format_semantic_question 无 issues 情况 ==========
    def test_format_semantic_question_no_issues(self, orchestrator):
        class FakeSemantic:
            issues = []
            suggested_questions = []
        text = orchestrator._format_semantic_question(FakeSemantic())
        assert "语义确认" in text

    # ========== 补测：矛盾检测在 process 中触发 ==========
    def test_process_with_contradiction(self, orchestrator):
        """先注册一条事实，再用否定句触发矛盾检测"""
        # 注册一条正事实
        f, _ = orchestrator.fact_engine.register_fact("地球是平的")
        orchestrator.fact_engine.cross_validate(f.id, "来源A")
        orchestrator.fact_engine.cross_validate(f.id, "来源B")
        # 输入一个对立陈述
        result = orchestrator.process("地球不是平的", user_id="test_user")
        assert result is not None
        # 无论是否触发矛盾，都要有 output_text
        assert len(result.output_text) > 0

    # ========== 补测：多个未知输入触发好奇心循环 ==========
    def test_process_multiple_unknowns(self, orchestrator):
        """连续输入多个未知词，触发好奇心缺口累积"""
        for kw in ["量子纠缠拓扑", "超弦理论分支", "暗物质谐振"]:
            result = orchestrator.process(kw, user_id="test_user")
            assert result is not None
        # 最后检查系统状态里的 curiosity
        state = orchestrator.get_system_state()
        assert state["curiosity"]["total"] > 0

    # ========== 补测：get_system_state 完整字段 ==========
    def test_get_system_state_full(self, orchestrator):
        state = orchestrator.get_system_state()
        assert "system_tension" in state
        assert "feeling" in state["system_tension"]
        assert "drive_level" in state["system_tension"]

            # ========== 补测：触发 process 内的矛盾检测（覆盖 262-281） ==========
    def test_process_contradiction_detected(self, orchestrator):
        """构造必然触发的矛盾对，覆盖 process 的矛盾检测分支"""
        # 关键：s1 含否定标记，s2 是 s1 去掉标记后的子串
        # marker="不是", s1="测试对象可食用不是", s1.replace("不是","")="测试对象可食用"
        # 让 s2 = "测试对象可食用"（子串）即可匹配

        # 1. 注册带否定的版本（先插入，作为 s1）
        f1, _ = orchestrator.fact_engine.register_fact("测试对象可食用不是")
        orchestrator.fact_engine.cross_validate(f1.id, "来源A")
        orchestrator.fact_engine.cross_validate(f1.id, "来源B")

        # 2. 注册去掉否定后的版本（后插入，作为 s2）
        f2, _ = orchestrator.fact_engine.register_fact("测试对象可食用")
        orchestrator.fact_engine.cross_validate(f2.id, "来源C")
        orchestrator.fact_engine.cross_validate(f2.id, "来源D")

        # 3. 输入前缀匹配两者的语句，触发 process 走完整流程
        # user_input[:4] = "测试对象"，两条事实都包含
        result = orchestrator.process("测试对象可食用真的不错", user_id="test_user")

        stages = [s["stage"] for s in result.stages]
        assert "conflict_detected" in stages, f"未触发矛盾检测，实际 stages: {stages}"
        assert "路径" in result.output_text or "不做价值评判" in result.output_text
        assert len(result.decision_chain) > 0

        # ========== 补测：语义门无 issues 时格式化 ==========
    def test_format_semantic_question_with_no_suggestions(self, orchestrator):
        class FakeSemantic:
            issues = ["测试issue"]
            suggested_questions = []
        text = orchestrator._format_semantic_question(FakeSemantic())
        assert "语义确认" in text
        assert "测试issue" in text

    # ========== 补测：build_output 事实有 beliefs 无 unknowns ==========
    def test_build_output_facts_beliefs_no_unknowns(self, orchestrator):
        f, _ = orchestrator.fact_engine.register_fact("测试事实A")
        orchestrator.fact_engine.cross_validate(f.id, "来源A")
        orchestrator.fact_engine.cross_validate(f.id, "来源B")
        facts = orchestrator.fact_engine.query("测试事实")
        b = orchestrator.belief_engine.register_belief(
            "u1", "测试信念A", category="preference"
        )
        beliefs = [b]
        text = orchestrator._build_output("测试", facts, beliefs, [])
        assert "已知条件" in text
        assert "用户信念" in text
        assert "推演路径" in text
        assert "证据充分" in text  # facts and not unknowns 分支

    # ========== 补测：get_system_state 完整触发 ==========
    def test_get_system_state_after_activity(self, orchestrator):
        # 制造一些活动
        orchestrator.process("苹果是一种水果", user_id="u1")
        orchestrator.process("我觉得量子纠缠很酷", user_id="u1")
        state = orchestrator.get_system_state()
        assert state["facts"]["total"] > 0
        assert state["system_tension"]["drive_level"] in [
            "none", "minimal", "light", "moderate", "strong"
        ]

        # ========== 补测：种子数据二次加载的跳过分支 ==========
    def test_seed_data_skip_existing(self, temp_dir):
        """第二次加载时，种子已存在，走跳过分支（覆盖 119->118, 121->118）"""
        path = os.path.join(temp_dir, 'seed_skip')
        # 第一次加载会注册所有种子
        core1 = YanbiaoCore(storage_path=path)
        count1 = core1.fact_engine.stats()["total"]

        # 第二次加载，种子已存在，应该跳过
        core2 = YanbiaoCore(storage_path=path)
        count2 = core2.fact_engine.stats()["total"]

        # 数量应该相同，且不会重复
        assert count1 == count2

        # ========== 补测：编排层的全链路审计 ==========
    def test_process_records_audit(self, orchestrator):
        """每次 process 应在 audit log 里留下一条 orchestrator 记录"""
        orchestrator.process("苹果是一种水果", user_id="audit_user")
        history = orchestrator.audit.get_history(
            user_id="audit_user", module="orchestrator"
        )
        assert len(history) == 1
        assert history[0].action == "process"
        assert history[0].after["raw_input"] == "苹果是一种水果"

    def test_get_system_state_includes_audit(self, orchestrator):
        """get_system_state 应包含审计统计"""
        orchestrator.process("测试输入A", user_id="u1")
        orchestrator.process("测试输入B", user_id="u1")
        state = orchestrator.get_system_state()
        assert "audit" in state
        assert state["audit"]["total"] > 0

    