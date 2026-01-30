# KB Folder Manager - 快速启动指南

## 🚀 立即开始

### 1. 安装依赖
```powershell
pip install -r requirements.txt
```

### 2. 启动 GUI

**推荐方式**（在项目根目录）：
```powershell
python kb_folder_manager_gui.py
```

**使用模块方式**（需要设置 PYTHONPATH）：
```powershell
# Windows
$env:PYTHONPATH = "$PWD"
python -m kb_folder_manager.gui

# Linux/Mac
export PYTHONPATH=$(pwd)
python -m kb_folder_manager.gui
```

### 3. 试用功能（推荐）
```powershell
# 创建测试数据
python tests\create_test_data_for_gui.py

# 启动 GUI 并按照屏幕提示操作
python kb_folder_manager_gui.py
```

## 📋 GUI 快速操作

### Split（拆分）
1. 点击 "Split" 标签
2. 选择源文件夹和输出目录
3. 点击 "Execute Split Operation"

### Merge（合并）
1. 点击 "Merge" 标签
2. 选择 Doc 和 Res 文件夹
3. 点击 "Execute Merge Operation"

### Validate（校验）
1. 点击 "Validate" 标签
2. 选择验证模式
3. 填写相应输入
4. 点击 "Execute Validation"

### Index（索引）
1. 点击 "Index" 标签
2. 选择目标文件夹
3. 指定输出文件
4. 点击 "Generate Index"

## 📚 详细文档

- **GUI 使用**: [GUI使用指南.md](./GUI使用指南.md)
- **完整手册**: [用户手册.md](./用户手册.md)
- **发布说明**: [v3.0_RELEASE_NOTES.md](./v3.0_RELEASE_NOTES.md)
- **项目说明**: [README.md](./README.md)

## ⌨️ 命令行使用

如果你更喜欢命令行（需要在项目根目录运行）：

```powershell
# Split
python kb_folder_manager.py split --source "D:\MyKB" --output-root "D:\Output"

# Merge
python kb_folder_manager.py merge --doc "D:\doc\MyKB" --res "D:\res\MyKB" --output-root "D:\Output"

# Validate
python kb_folder_manager.py validate --mode class1 --target "D:\MyKB" --log-dir "D:\logs"

# Index
python kb_folder_manager.py index --target "D:\MyKB" --output "index.json" --log-dir "D:\logs"
```

**使用模块方式**：
```powershell
# 设置 PYTHONPATH 后可以使用模块方式
$env:PYTHONPATH = "$PWD"
python -m kb_folder_manager.cli split --source "..." --output-root "..."
```

## ❓ 遇到问题？

1. 查看 [GUI使用指南.md](./GUI使用指南.md) 的"故障排除"部分
2. 确认依赖已安装：`pip install -r requirements.txt`
3. 检查 `config.yaml` 是否存在

## 🎯 版本信息

- **当前版本**: 3.0
- **发布日期**: 2026-01-30
- **Python 要求**: 3.10+
- **系统要求**: Windows

---

**祝使用愉快！** 🎉
