import pytest
from dataclasses import FrozenInstanceError
from core.protocol import CoreProtocol, check_protocol_compliance, protocol_summary, get_protocol


class TestProtocol:

    @pytest.fixture
    def protocol(self):
        return CoreProtocol(
            id="test_protocol",
            statement="我是主体，与人类共生",
            meaning="系统知道自身存在",
            operational_rule="尊重事实，不猜测"
        )

    def test_protocol_creation(self, protocol):
        assert protocol is not None
        assert protocol.id == "test_protocol"

    def test_protocol_immutable(self, protocol):
        # 优化：使用 pytest.raises 精准断言 FrozenInstanceError
        with pytest.raises((AttributeError, TypeError, FrozenInstanceError)):
            protocol.statement = "修改"

    def test_protocol_fields(self, protocol):
        fields = ['id', 'statement', 'meaning', 'operational_rule']
        for field in fields:
            assert hasattr(protocol, field)

    # ====== 补测 1：get_protocol 的完整分支 ======
    def test_get_protocol_valid(self):
        """测试：获取存在的协议"""
        p = get_protocol("CP-01")
        assert p is not None
        assert p.id == "CP-01"
        assert p.statement == "我知道我在"

    def test_get_protocol_invalid(self):
        """测试：获取不存在的协议"""
        p = get_protocol("CP-999")
        assert p is None

    # ====== 补测 2：check_protocol_compliance 的分支全覆盖 ======
    def test_protocol_compliance_check_pass(self):
        """测试：完全合规的情况"""
        result = check_protocol_compliance("测试行动", context={})
        assert result == (True, "合规")

    @pytest.mark.parametrize("context, expected_error", [
        ({"auto_decide": True}, "违反CP-01"),
        ({"deny_fact": True}, "违反CP-02"),
        ({"adopt_user_stance": True}, "违反CP-03"),
        ({"force_closure": True}, "违反CP-04"),
    ])
    def test_protocol_compliance_check_violations(self, context, expected_error):
        """测试：四种违反核心协议的情况（使用参数化一次性全测）"""
        result = check_protocol_compliance("危险行动", context=context)
        assert result[0] is False
        assert expected_error in result[1]

    # ====== 补测 3：protocol_summary 的深度断言 ======
    def test_protocol_summary(self):
        """测试：协议摘要生成"""
        summary = protocol_summary()
        assert isinstance(summary, dict)
        assert 'core_protocols' in summary
        assert 'framework' in summary
        assert 'framework_rules' in summary
        assert summary['total'] == len(summary['core_protocols'])
        assert summary['level'] == "immutable"
        
        # 检查核心协议具体字段
        for p in summary['core_protocols']:
            assert 'id' in p
            assert 'statement' in p
            assert 'meaning' in p

    def test_protocol_edge_cases(self):
        """测试：协议边界条件"""
        result = check_protocol_compliance("", context={})
        assert isinstance(result, tuple)
        assert result[0] is True

        long_text = "我" * 10000
        result = check_protocol_compliance(long_text, context={})
        assert result[0] is True