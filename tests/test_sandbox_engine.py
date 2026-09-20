import os
import pytest
import time
import json
from core.sandbox_engine import SandboxEngine, SANDBOX_DISCLAIMER


class TestSandboxEngine:

    # ====== 补测 1：基础会话功能 ======
    def test_create_sandbox(self, sandbox_engine):
        session = sandbox_engine.create_sandbox(
            user_id='user1',
            scenario='假设明天会下雨',
            rules_to_override=[]
        )
        assert session is not None
        assert hasattr(session, 'id')
        assert session.user_id == 'user1'

    def test_get_session(self, sandbox_engine):
        session = sandbox_engine.create_sandbox(
            user_id='user1',
            scenario='假设系统崩溃',
            rules_to_override=[]
        )
        retrieved = sandbox_engine.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id
        
        # 补测：获取不存在的会话
        assert sandbox_engine.get_session("INVALID_ID") is None

    # ====== 补测 2：推演与无效会话 ======
    def test_add_deduction(self, sandbox_engine):
        session = sandbox_engine.create_sandbox(
            user_id='user1',
            scenario='假设明天会下雨',
            rules_to_override=[]
        )
        result = sandbox_engine.add_deduction(
            session_id=session.id,
            deduction='需要带伞'
        )
        assert result is not None
        assert SANDBOX_DISCLAIMER in result  # 确保包含免责声明
        assert len(session.deductions) == 1

    def test_add_deduction_invalid_session(self, sandbox_engine):
        """补测：向不存在的沙盒会话添加推演（覆盖 202->203）"""
        result = sandbox_engine.add_deduction("INVALID_ID", "测试推演")
        assert result == "沙盒会话不存在"

    # ====== 补测 3：会话列表过滤（覆盖 215->216） ======
    def test_list_sessions(self, sandbox_engine):
        sandbox_engine.create_sandbox('user1', '场景1')
        sandbox_engine.create_sandbox('user2', '场景2')
        
        # 无过滤，列出全部
        all_sessions = sandbox_engine.list_sessions()
        assert len(all_sessions) == 2
        
        # 按 user_id 过滤
        user1_sessions = sandbox_engine.list_sessions(user_id='user1')
        assert len(user1_sessions) == 1
        assert user1_sessions[0].user_id == 'user1'

    # ====== 补测 4：归档列表与压缩解压 ======
    def test_list_archives(self, sandbox_engine):
        assert len(sandbox_engine.list_archives()) == 0
        sandbox_engine.compress_definition("量子计算", "旧定义", "新定义", "更新")
        assert len(sandbox_engine.list_archives()) == 1

    def test_compress_definition(self, sandbox_engine):
        arch = sandbox_engine.compress_definition(
            term="量子计算",
            original_def="一种计算范式",
            new_def="一种基于量子力学的新计算方式",
            reason="更新定义"
        )
        assert arch.term == "量子计算"
        assert arch.original_definition == "一种计算范式"
        assert arch.restored is False

    def test_decompress_definition(self, sandbox_engine):
        sandbox_engine.compress_definition(
            term="量子计算", original_def="旧", new_def="新", reason="更新"
        )
        # 成功解压
        arch = sandbox_engine.decompress_definition(term="量子计算")
        assert arch is not None
        assert arch.restored is True
        
        # 补测：解压不存在的 term（覆盖 154->159 和 155->154）
        not_found = sandbox_engine.decompress_definition(term="不存在Term")
        assert not_found is None

    # ====== 补测 5：概念替换防护（覆盖 170->171 全分支） ======
    def test_detect_concept_swap(self, sandbox_engine):
        # 场景1：概念不同且无显式声明 -> 检测出偷换
        result1 = sandbox_engine.detect_concept_swap("苹果", "香蕉", "它们都是水果")
        assert result1["detected"] is True
        assert result1["severity"] == "high"

        # 场景2：概念不同但有显式声明 -> 检测通过
        result2 = sandbox_engine.detect_concept_swap("苹果", "香蕉", "重新定义一下，在此上下文中苹果指香蕉")
        assert result2["detected"] is False

        # 场景3：概念完全相同 -> 检测通过
        result3 = sandbox_engine.detect_concept_swap("苹果", "苹果", "随便写点上下文")
        assert result3["detected"] is False

    # ====== 补测 6：持久化加载（覆盖 100->108 和 109->exit 空循环退出分支） ======
    def test_load_all_and_persistence(self, tmp_path):
        """测试：保存数据后，重新实例化引擎能否正确加载"""
        # 1. 创建一个空引擎（覆盖空目录退出分支）
        engine1 = SandboxEngine(str(tmp_path))
        assert len(engine1.list_archives()) == 0
        assert len(engine1.list_sessions()) == 0

        # 2. 写入数据
        engine1.compress_definition("测试Term", "旧", "新", "测试")
        engine1.create_sandbox("user1", "测试场景")
        
        # 3. 新建引擎，触发 _load_all 从磁盘读取
        engine2 = SandboxEngine(str(tmp_path))
        assert len(engine2.list_archives()) == 1
        assert len(engine2.list_sessions()) == 1
        
        # 补测：制造非 JSON 文件，确保跳过逻辑生效
        bad_file = os.path.join(str(tmp_path), "sandbox", "archives", "ignore.txt")
        with open(bad_file, "w") as f:
            f.write("not json")
            
        engine3 = SandboxEngine(str(tmp_path))
        assert len(engine3.list_archives()) == 1  # 依然只有1个

    # ====== 补测 7：精确断言统计数据 ======
    def test_stats(self, sandbox_engine):
        # 初始统计
        stats = sandbox_engine.stats()
        assert stats["total_sessions"] == 0
        assert stats["total_archives"] == 0
        assert stats["active_sandboxes"] == 0

        # 创建数据
        s1 = sandbox_engine.create_sandbox("user1", "场景1")
        s2 = sandbox_engine.create_sandbox("user1", "场景2")
        sandbox_engine.add_deduction(s1.id, "推演1")  # s1 变为 active
        sandbox_engine.compress_definition("T1", "旧", "新", "原因")

        stats2 = sandbox_engine.stats()
        assert stats2["total_sessions"] == 2
        assert stats2["total_archives"] == 1
        assert stats2["active_sandboxes"] == 1  # 只有 s1 有 deductions

            # ====== 补测 8：覆盖 100->108 和 109->exit (目录不存在) ======
    def test_load_all_missing_directories(self, sandbox_engine, monkeypatch):
        """覆盖 100->108 和 109->exit：模拟 archives 和 sessions 目录都不存在的情况"""
        import os
        # 强制让 os.path.exists 对这两个目录返回 False
        original_exists = os.path.exists
        def mock_exists(path):
            if "archives" in str(path) or "sessions" in str(path):
                return False
            return original_exists(path)
        
        monkeypatch.setattr(os.path, "exists", mock_exists)
        # 手动触发 _load_all，此时两个目录都不存在，直接跳过循环
        sandbox_engine._load_all()
        
        assert len(sandbox_engine.list_archives()) == 0
        assert len(sandbox_engine.list_sessions()) == 0

    # ====== 补测 9：覆盖 111->110 (sessions 目录下非 JSON 文件) ======
    def test_load_all_non_json_session_file(self, tmp_path):
        """覆盖 111->110：sessions 目录下存在非 .json 文件时应跳过"""
        import os
        sess_dir = os.path.join(str(tmp_path), "sandbox", "sessions")
        os.makedirs(sess_dir, exist_ok=True)
        
        # 关键点：在 sessions 目录下创建一个非 .json 文件
        with open(os.path.join(sess_dir, "ignore.txt"), "w") as f:
            f.write("not a json file")
        
        # 重新实例化引擎，触发 _load_all
        engine = SandboxEngine(str(tmp_path))
        assert len(engine.list_sessions()) == 0