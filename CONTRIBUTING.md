# Contributing

Please ensure that before submitting a pull request, you run:

```bash
pytest tests/ --cov=core --cov-branch

and that the coverage is not lower than 95%.

**2. 在终端执行强制添加命令**：
```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING"
git push origin main