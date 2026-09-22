"""
性能与压力测试 — 验证大数据量、高并发下的响应时间与数据一致性
"""
import time
import concurrent.futures
import pytest
from core.belief_engine import BeliefEngine
from core.fact_engine import FactEngine
from core.sandbox_engine import SandboxEngine


class TestPerformance:

    # ========== 1. 大数据量查询性能 ==========
    def test_belief_query_performance(self, tmp_path):
        """测试：写入 1000 条信念后，单次查询耗时"""
        engine = BeliefEngine(str(tmp_path))
        
        # 写入 1000 条
        for i in range(1000):
            engine.register_belief(
                user_id="perf_user",
                statement=f"信念条目-{i}",
                category="preference"
            )
        
        # 查询耗时
        start = time.perf_counter()
        results = engine.query("信念条目-500", "perf_user")
        elapsed = time.perf_counter() - start
        
        assert len(results) == 1
        assert elapsed < 0.5, f"查询 1000 条数据耗时 {elapsed:.4f}s，超过 0.5s 阈值"
        print(f"\n[性能] 信念查询 1000 条耗时: {elapsed*1000:.2f} ms")

    def test_fact_query_performance(self, tmp_path):
        """测试：写入 1000 条事实后，单次查询耗时"""
        engine = FactEngine(str(tmp_path))
        
        for i in range(1000):
            engine.register_fact(f"事实条目-{i}")
        
        start = time.perf_counter()
        results = engine.query("事实条目-500")
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.5, f"查询 1000 条事实耗时 {elapsed:.4f}s，超过 0.5s 阈值"
        print(f"\n[性能] 事实查询 1000 条耗时: {elapsed*1000:.2f} ms")

    # ========== 2. 高并发写入 ==========
    def test_high_concurrency_belief(self, tmp_path):
        """测试：100 线程同时为 100 个不同用户注册信念"""
        engine = BeliefEngine(str(tmp_path))
        
        def register(uid: int):
            engine.register_belief(
                user_id=f"user_{uid}",
                statement=f"信念-{uid}",
                category="preference"
            )
        
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(register, i) for i in range(100)]
            for f in concurrent.futures.as_completed(futures):
                f.result()
        elapsed = time.perf_counter() - start
        
        # 验证每个用户只有自己的 1 条
        for i in range(100):
            beliefs = engine.get_user_beliefs(f"user_{i}")
            assert len(beliefs) == 1
            assert beliefs[0].user_id == f"user_{i}"
        
        print(f"\n[性能] 100 线程并发注册耗时: {elapsed*1000:.2f} ms")

    # ========== 3. 沙盒会话并发创建 ==========
    def test_concurrent_sandbox_creation(self, tmp_path):
        """测试：50 线程同时创建沙盒会话"""
        engine = SandboxEngine(str(tmp_path))
        
        def create(idx: int):
            return engine.create_sandbox(
                user_id=f"user_{idx}",
                scenario=f"推演场景-{idx}"
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(create, i) for i in range(50)]
            sessions = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(sessions) == 50
        # 验证用户隔离
        user_0_sessions = engine.list_sessions(user_id="user_0")
        assert len(user_0_sessions) == 1
        assert user_0_sessions[0].scenario == "推演场景-0"

    # ========== 4. 大批量事实交叉验证 ==========
    def test_bulk_cross_validate(self, tmp_path):
        """测试：批量交叉验证 500 条事实"""
        engine = FactEngine(str(tmp_path))
        
        facts = []
        for i in range(500):
            f, _ = engine.register_fact(f"批量事实-{i}")
            facts.append(f)
        
        start = time.perf_counter()
        for f in facts:
            engine.cross_validate(f.id, "来源A")
            engine.cross_validate(f.id, "来源B")
        elapsed = time.perf_counter() - start
        
        # 验证全部已通过验证
        verified = [f for f in engine._facts.values() if f.verified]
        assert len(verified) == 500
        print(f"\n[性能] 500 条事实交叉验证耗时: {elapsed*1000:.2f} ms")