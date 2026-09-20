import pytest
from core.pif_guard import PIFGuard, PIFAlert


class TestPIFGuard:

    # ====== 补测 1：覆盖 66->68（关键词不匹配时的循环跳过） ======
    def test_check_no_pif(self, pif_guard):
        """测试：不包含任何群体关键词的陈述，不应触发 PIF 警报"""
        alert = pif_guard.check("今天天气不错，适合出门散步")
        assert isinstance(alert, PIFAlert)
        assert alert.triggered is False
        assert alert.group_data == ""

    # ====== 补测 2：覆盖 69-79 和 88-92（触发 PIF 警报 + 自我推断） ======
    def test_check_pif_triggered_with_target(self, pif_guard):
        """测试：显式传入目标个体，触发 PIF 警报"""
        # 包含群体关键词 "男性"，并显式指定针对个体 "张三"
        alert = pif_guard.check("男性的成功率普遍比较高", target_individual="张三")
        
        assert isinstance(alert, PIFAlert)
        assert alert.triggered is True
        assert "男性" in alert.group_data
        assert alert.individual_target == "张三"
        assert "群体频率不能直接等于个体真值" in alert.correction

    def test_check_pif_triggered_implicit_target(self, pif_guard):
        """测试：不传入 target_individual，但文本中隐含了个体推断（覆盖 _targets_individual 方法）"""
        # 【修正】把 "一定" 改为 "你一定"（"你一定" 是个体标记，会触发 _targets_individual）
        alert = pif_guard.check("90后你一定都是月光族")
        
        assert alert.triggered is True
        assert alert.individual_target == "未具名个体"  # 因为没传 target_individual
        assert "年龄群体统计" in alert.reason

    # ====== 补测 3：覆盖 110->114 和 117->120（有来源且声明全貌的正向分支） ======
    def test_validate_source_complete(self, pif_guard):
        """测试：来源完整且声明为全貌时，不产生 issues"""
        result = pif_guard.validate_source("根据国家统计局的数据来源，这是一份完整的全貌统计报告")
        
        assert result["has_source"] is True
        assert result["is_complete"] is True
        assert len(result["issues"]) == 0  # 没有 issues，覆盖了 False 分支

    def test_validate_source_incomplete(self, pif_guard):
        """测试：有来源但未声明完整（触发 issues），补充原有测试"""
        result = pif_guard.validate_source("根据某个研究显示")
        
        assert result["has_source"] is True
        assert result["is_complete"] is False
        assert "未声明是否为全貌" in result["issues"][0]

    def test_validate_source_no_source(self, pif_guard):
        """测试：无来源无完整性（验证原有分支）"""
        result = pif_guard.validate_source("苹果很好吃")
        
        assert result["has_source"] is False
        assert result["is_complete"] is False
        assert len(result["issues"]) == 2

    # ====== 补测 4：覆盖 134-140（观点分支的完整返回） ======
    def test_fact_vs_opinion_opinion(self, pif_guard):
        """测试：包含主观评价词时，返回观点类型"""
        # "最好" 是 opinion_markers 里的词
        result = pif_guard.fact_vs_opinion("苹果是世界上最好吃的水果")
        
        assert result["type"] == "opinion"
        assert result["can_be_axiom"] is False
        assert "包含主观评价词" in result["reason"]
        assert result["scope"] == "session_only"

    def test_fact_vs_opinion_fact(self, pif_guard):
        """测试：客观陈述，返回事实类型（补全原有测试的断言）"""
        result = pif_guard.fact_vs_opinion("苹果是一种水果")
        
        assert result["type"] == "fact"
        assert result["can_be_axiom"] is True
        assert "需交叉验证" in result["reason"]
        assert result["scope"] == "universal"

        # ====== 补测 5：覆盖 68->65（命中群体关键词但无个体指向，继续循环） ======
    def test_check_pif_keyword_without_individual(self, pif_guard):
        """测试：命中群体关键词，但无个体标记且未传入 target_individual，循环继续"""
        # "男性" 在 gender 类别的关键词中，但句子没有个体标记（无"你/他/她"等）
        alert = pif_guard.check("男性的平均寿命是75岁")
        
        # 因为没有针对个体，所以不应触发 PIF
        assert alert.triggered is False
        assert alert.group_data == ""
        assert alert.individual_target == ""