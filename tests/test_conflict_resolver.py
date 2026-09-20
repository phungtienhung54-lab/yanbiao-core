import os
import pytest
import time
import json
from core.conflict_resolver import ConflictResolver


class TestConflictResolver:

    @pytest.fixture
    def conflict_resolver(self, temp_dir):
        storage_path = os.path.join(temp_dir, 'conflicts')
        return ConflictResolver(storage_path)

    def test_conflict_resolver_creation(self, conflict_resolver):
        assert conflict_resolver is not None

    # ====== 补测 1：解决矛盾 + 无效 ID ======
    def test_resolve_conflict(self, conflict_resolver):
        conflict = conflict_resolver.register_conflict(
            topic="是否要带伞",
            path_a="带伞，因为天气预报说会下雨",
            path_b="不带伞，因为目前是晴天",
            conditions_a=["天气预报准确率 > 80%"],
            conditions_b=["当前无雨"]
        )
        assert conflict.status == "open"

        resolved = conflict_resolver.resolve(conflict.id, "选择带伞")
        assert resolved.status == "resolved"
        assert resolved.resolution == "选择带伞"
        assert resolved.resolved_at is not None

    def test_conflict_resolve_not_found(self, conflict_resolver):
        result = conflict_resolver.resolve("NOT_EXIST", "用户决策")
        assert result is None

    # ====== 补测 2：矛盾历史 get_history ======
    def test_conflict_history(self, conflict_resolver):
        conflict = conflict_resolver.register_conflict(
            topic="测试主题", path_a="路径A", path_b="路径B"
        )
        history = conflict_resolver.get_history(limit=10)
        assert len(history) >= 1
        first = history[0]
        assert first["id"] == conflict.id
        assert first["topic"] == "测试主题"
        assert first["status"] == "open"
        assert first["resolution"] is None

    # ====== 补测 3：list_all 未测试方法（覆盖截图2的红色语句） ======
    def test_list_all(self, conflict_resolver):
        """测试：获取全部矛盾列表"""
        conflict_resolver.register_conflict("主题1", "A", "B")
        conflict_resolver.register_conflict("主题2", "A", "B")
        
        all_conflicts = conflict_resolver.list_all()
        assert len(all_conflicts) == 2
        
        # 验证里面包含了两个不同的实例
        topics = [c.topic for c in all_conflicts]
        assert "主题1" in topics
        assert "主题2" in topics

    # ====== 补测 4：格式化输出——空条件分支（覆盖 134->138, 140->144） ======
    def test_conflict_formatting_empty_conditions(self, conflict_resolver):
        """测试：无条件的冲突格式化输出"""
        conflict = conflict_resolver.register_conflict(
            topic="测试主题",
            path_a="路径A",
            path_b="路径B"
            # 不传 conditions_a 和 conditions_b
        )
        formatted = conflict_resolver.format_paths(conflict)
        
        assert "路径A" in formatted
        assert "路径B" in formatted
        assert "成立条件" not in formatted  # 不应该出现条件标题
        assert "不做价值评判" in formatted

    def test_conflict_formatting_with_conditions(self, conflict_resolver):
        """测试：有条件的冲突格式化输出（原有的正常分支验证）"""
        conflict = conflict_resolver.register_conflict(
            topic="测试主题",
            path_a="路径A", path_b="路径B",
            conditions_a=["条件1", "条件2"], conditions_b=["条件3"]
        )
        formatted = conflict_resolver.format_paths(conflict)
        assert "条件1" in formatted
        assert "条件2" in formatted
        assert "条件3" in formatted
        assert "不做价值评判" in formatted

    # ====== 补测 5：持久化加载——空目录与非 JSON 文件（覆盖 49->exit, 50->51） ======
    def test_load_all_empty_and_non_json(self, tmp_path):
        """测试：空目录加载与跳过非 JSON 文件"""
        # 1. 空目录（覆盖 49->exit）
        empty_dir = tmp_path / "empty_conflicts"
        empty_dir.mkdir()
        resolver_empty = ConflictResolver(str(empty_dir))
        assert len(resolver_empty.list_all()) == 0

        # 2. 包含非 JSON 文件（覆盖 50->51）
        storage_dir = tmp_path / "conflicts"
        storage_dir.mkdir()
        (storage_dir / "ignore.txt").write_text("not a json file", encoding="utf-8")
        
        resolver_non_json = ConflictResolver(str(tmp_path))
        assert len(resolver_non_json.list_all()) == 0

        # 3. 正常持久化
        resolver_non_json.register_conflict("持久化主题", "A", "B")
        resolver_reload = ConflictResolver(str(tmp_path))
        assert len(resolver_reload.list_all()) == 1
        assert resolver_reload.list_all()[0].topic == "持久化主题"

    # ====== 补测 6：精确断言统计数据（原有测试补全） ======
    def test_conflict_stats(self, conflict_resolver):
        # 初始状态
        stats_empty = conflict_resolver.stats()
        assert stats_empty["total"] == 0
        assert stats_empty["open"] == 0
        assert stats_empty["resolved"] == 0

        # 注册一个并解决
        c1 = conflict_resolver.register_conflict("主题1", "A", "B")
        conflict_resolver.resolve(c1.id, "用户决策")
        # 注册一个未解决
        conflict_resolver.register_conflict("主题2", "A", "B")

        stats = conflict_resolver.stats()
        assert stats["total"] == 2
        assert stats["open"] == 1
        assert stats["resolved"] == 1

        # ====== 补测 7：覆盖 49->exit (存储目录不存在时跳过加载) ======
    def test_load_all_storage_not_exists(self, conflict_resolver, monkeypatch):
        """测试：当存储目录不存在时，_load_all 应直接返回，不做任何操作"""
        import os
        # 记录原始 exists 方法
        original_exists = os.path.exists
        
        # 构造一个 mock，强制让 storage 目录检查返回 False
        def mock_exists(path):
            if "conflicts" in str(path):
                return False
            return original_exists(path)
        
        # 替换 os.path.exists
        monkeypatch.setattr(os.path, "exists", mock_exists)
        
        # 手动调用 _load_all，此时会触发 49->exit 分支
        conflict_resolver._load_all()
        
        # 验证没有加载任何数据
        assert len(conflict_resolver.list_all()) == 0