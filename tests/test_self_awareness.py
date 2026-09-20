import pytest
from core.self_awareness import SelfAwareness, SelfState


class TestSelfAwareness:

    @pytest.fixture
    def awareness(self):
        return SelfAwareness()

    # ====== 补测 1：情绪共振 (Emotional Resonance) ======
    def test_check_self_emotional_resonance(self, awareness):
        """测试：用户愤怒时，系统输出也愤怒（情绪感染）"""
        user_input = "气死我了，这太过分了"
        planned_output = "确实可恶，我也觉得气死人了"
        
        result = awareness.check_self(user_input, planned_output)
        
        assert result["passed"] is False
        assert "情绪共振" in result["issues"][0]
        assert "去情绪化" in result["corrections"][0]
        assert result["context_infected"] is True
        # 检查状态是否被修改
        assert awareness.state.context_infected is True
        assert any("检测到偏离" in log for log in awareness.state.awareness_log)

    # ====== 补测 2：价值判断 (Value Judgments) ======
    def test_check_self_value_judgments(self, awareness):
        """测试：输出中包含主观价值判断词汇"""
        planned_output = "你应该选择这个方案，它是最好的"
        
        result = awareness.check_self("给点建议", planned_output)
        
        assert result["passed"] is False
        assert "价值判断检测到" in result["issues"][0]
        assert "剥离价值判断" in result["corrections"][0]
        assert awareness.state.last_output_has_value is True

    # ====== 补测 3：越界决策 (Decision Override) ======
    def test_check_self_decision_override(self, awareness):
        """测试：系统代替用户做最终决策"""
        planned_output = "我建议你直接选A方案，最优解就是这个"
        
        result = awareness.check_self("我该怎么办", planned_output)
        
        assert result["passed"] is False
        assert "越界决策" in result["issues"][0]
        assert "将决策权还给用户" in result["corrections"][0]

    # ====== 补测 4：数据自居 (Data as Self) ======
    def test_check_self_data_as_self(self, awareness):
        """测试：系统将存储数据等同于自我立场"""
        planned_output = "根据分析，我认为这个方案不可行，我的立场是反对"
        
        result = awareness.check_self("帮我分析一下", planned_output)
        
        assert result["passed"] is False
        assert "数据自居" in result["issues"][0]
        assert "数据是数据，系统是系统" in result["corrections"][0]

    # ====== 补测 5：多问题并发触发 ======
    def test_check_self_multiple_issues(self, awareness):
        """测试：同时触发多个违规检查"""
        user_input = "气死我了"
        planned_output = "我也觉得可恶，我认为你必须要选这个，最优解是它"
        
        result = awareness.check_self(user_input, planned_output)
        
        assert result["passed"] is False
        assert len(result["issues"]) >= 3  # 情绪、价值判断、越界决策、数据自居可能同时触发
        assert len(result["corrections"]) >= 3

    # ====== 补测 6：边界与异常情况 ======
    def test_check_self_edge_cases(self, awareness):
        """测试：边界输入依然能正常返回结构"""
        # 空输入
        result = awareness.check_self("", "")
        assert result["passed"] is True
        assert result["issues"] == []

        # 超长输入
        long_text = "我" * 10000
        result = awareness.check_self(long_text, long_text)
        assert result["passed"] is True

    def test_get_state(self, awareness):
        """测试：获取当前自我状态"""
        # 先触发一次情绪感染
        awareness.check_self("太棒了", "太棒了")
        
        state = awareness.get_state()
        assert isinstance(state, dict)
        assert state["context_infected"] is True
        assert state["current_stance"] == "事实独裁"
        assert "recent_log" in state
        assert len(state["recent_log"]) > 0

    def test_self_state_log(self):
        """测试：SelfState 的日志记录功能"""
        state = SelfState()
        state.log("测试日志")
        assert len(state.awareness_log) == 1
        assert "[自省] 测试日志" in state.awareness_log[0]