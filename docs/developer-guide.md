# KB Folder Manager - 开发者指南

> 完整的开发文档，涵盖架构、测试、贡献指南

**版本**: 3.2.0 | **更新日期**: 2026-02-12

---

## 目录

- [项目概述](#项目概述)
- [开发环境设置](#开发环境设置)
- [项目架构](#项目架构)
- [核心模块详解](#核心模块详解)
- [测试指南](#测试指南)
- [代码规范](#代码规范)
- [贡献指南](#贡献指南)

---

## 项目概述

KB Folder Manager 是一个用于个人知识库管理的 Windows/Python 工具。

### 核心功能

- **Split** - 将 Complete 目录拆分成 Doc（文档）和 Res（资源）
- **Merge** - 将 Doc 和 Res 目录合并回 Complete
- **Validate** - 验证文件夹结构是否符合规范
- **Repair** - 对 Compare、Validate 与 Split/Merge 前置校验问题执行批量修复
- **Index** - 生成带哈希值和元数据的索引文件

### 技术栈

- **语言**: Python 3.10+
- **GUI 框架**: tkinter + ttkbootstrap
- **配置**: YAML
- **测试**: unittest
- **依赖管理**: pip + requirements.txt

---

## 开发环境设置

### 前置要求

- Python 3.10 或更高版本
- Windows 操作系统（主要支持）
- Git

### 克隆项目

```bash
git clone https://github.com/buptanswer/KB-Folder-Manager.git
cd KB-Folder-Manager
```

### 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows CMD
.venv\Scripts\activate.bat
# Linux/Mac
source .venv/bin/activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

**requirements.txt 内容**:
```
PyYAML>=6.0
ttkbootstrap>=1.20.0
pillow>=10.0.0
```

### 验证安装

```bash
# 测试 CLI
python kb_folder_manager.py --help

# 测试 GUI
python kb_folder_manager_gui.py

# 运行测试
python -m unittest discover tests
```

---

## 项目架构

### 目录结构

```
KB-Folder-Manager/
├── kb_folder_manager/          # 核心包
│   ├── __init__.py             # 包初始化
│   ├── cli.py                  # 命令行入口参数解析
│   ├── config.py               # 配置读取与校验
│   ├── gui.py                  # GUI（Split/Merge/Validate/Repair/Index）
│   ├── indexer.py              # 索引构建与写出
│   ├── operations.py           # 业务编排层（含 Compare/Repair API）
│   ├── utils.py                # 通用工具与日志封装
│   └── validator.py            # Class1/Class2/Mutual/Compare 校验
├── kb_folder_manager.py        # CLI 入口
├── kb_folder_manager_gui.py    # GUI 入口
├── config.yaml                 # 配置文件
├── requirements.txt            # 依赖清单
├── tests/                      # 测试目录
│   ├── test_basic.py
│   ├── test_compare_repair.py
│   ├── test_gui.py
│   ├── test_gui_batch_repair_flow.py
│   ├── test_gui_launch.py
│   └── test_progress_feedback.py
├── docs/                       # 文档
│   ├── user-guide.md           # 用户指南
│   ├── developer-guide.md      # 开发者指南（本文档）
│   └── release-notes/          # 发布说明
│       ├── v3.0.md
│       ├── v3.1.0.md
│       └── v3.2.0.md
├── CHANGELOG.md                # 更新日志
└── README.md                   # 项目说明
```

### 架构设计原则

1. **接口与业务分离**：`cli.py/gui.py` 只做输入输出与调度，规则在 `validator.py` 和 `operations.py`。
2. **统一 Repair 模型**：Compare/Validate/Pre-check 问题统一为结构化 issue，GUI 与后端共享同一套策略调度。
3. **闭环流程**：操作遵循“预检/分析 → 用户确认 → 执行 → 结果反馈”。
4. **响应优先**：GUI 后台线程执行任务，主线程只做渲染与状态更新。

### 模块依赖关系

```
kb_folder_manager_gui.py ─→ gui.py ─┬─→ operations.py ─┬─→ validator.py
kb_folder_manager.py ─────→ cli.py ─┘                  ├─→ indexer.py
                                                        └─→ utils.py/config.py
```

---

## 核心模块详解

### operations.py（核心业务逻辑）

**职责**：封装可复用操作 API（CLI 与 GUI 共用）。

**主要入口函数**：
- `split_operation(...)`
- `merge_operation(...)`
- `validate_operation(...)`
- `validate_mutual_operation(...)`
- `analyze_compare_operation(...)`
- `apply_compare_fixes(...)`
- `index_operation(...)`

**行为约定（与当前实现一致）**：
- `merge_operation(...)` 在 `doc/res` 根目录名不一致时不再直接阻断，而是先告警并要求确认
- 若用户确认继续，合并输出目录名称默认采用 `doc_path.name`
- `validate_mutual_operation(...)` 在名称不一致时会触发同类确认逻辑（`auto_yes=False` 时）
- CLI 可通过全局参数 `--yes`（需位于子命令前）跳过确认；GUI 通过弹窗回调确认
- 当前 GUI 的 Mutual 校验调用使用 `auto_yes=True`，即记录 warning 后继续（不弹确认框）

**关键数据结构**：
- `CompareAnalysisResult`：Compare 输出（问题列表、路径、日志路径）
- `CompareFixResult`：Repair 输出（applied/skipped/failed/applied_paths）

### validator.py（规则与问题分类）

**职责**：定义校验规则与 Compare 问题类型。

**核心能力**：
- `validate_class1` / `validate_class2` / `validate_mutual`
- `collect_compare_issues` / `group_compare_issues_by_type`
- `emit_compare_issue_logs`

**当前 Compare 分类要点**：
- 内容差异统一为 `content_mismatch`（不再拆 `size/hash` 双错误）
- `mtime_diff_hash_same` 使用 1 秒容差，避免亚秒抖动误报
- 目录/占位符差异独立建模，可直接进入批量修复

### utils.py（工具函数）

**职责**：提供日志、文件系统与路径相关基础能力（如 `Logger`、哈希计算、拷贝、路径工具）。

### indexer.py（索引构建）

**职责**：扫描目录并生成结构化索引（`files/dirs/placeholders/metadata`）。

### cli.py（命令行接口）

**职责**：解析命令并调用 `operations.py`。

**子命令**：
- `split` - 拆分操作
- `merge` - 合并操作
- `validate` - 验证操作
- `index` - 索引操作

### gui.py（图形界面）

**职责**：提供交互层与可视化反馈。

**关键组件**：
1. `OperationThread`：后台执行任务并通过队列回传结果。
2. `LogCapture` / `MultiLogCapture`：将 stdout/stderr 转为 GUI 日志、进度与状态。
3. `KBFolderManagerGUI`：管理 6 个标签页与跨流程 Repair 闭环。

**当前交互特性**：
- 共享进度条 + 状态动画 + `Activity` 动态指示
- Validate 页内联日志框
- Compare 结束自动切 Repair；Mutual/Class2/Split/Merge 失败时也可自动切 Repair
- Repair 支持按问题类型多选批量修复，并即时移除已修复项（不强制重跑分析）

---

## 测试指南

### 运行测试

```bash
# 1) 运行单元测试（含 CLI 烟雾）
python -m unittest discover tests

# 2) GUI 启动烟雾
python tests/test_gui_launch.py

# 3) GUI 功能模拟（Split/Merge/Validate/Index）
python tests/test_gui.py

# 4) GUI 批量修复全流程（模拟用户事件）
python tests/test_gui_batch_repair_flow.py

# 5) GUI 进度与状态反馈验证
python tests/test_progress_feedback.py
```

### 测试文件说明

#### test_basic.py
- 基础功能测试
- Split/Merge 核心回归

#### test_cli_smoke.py
- CLI 入口烟雾测试
- 覆盖 `--help`、`validate compare` 错误码、`index` 成功路径

#### test_gui.py
- GUI 相关后端流程模拟测试（Split/Merge/Validate/Index）

#### test_compare_repair.py
- Compare + 非 Compare（doc/res、complete）问题识别与批量修复单元测试
- 覆盖 `content_mismatch`、`mtime_diff_hash_same`、missing/extra/placeholder、doc/res 与 complete 场景

#### test_gui_batch_repair_flow.py
- 模拟 GUI 批量修复闭环：Compare、Mutual、Split 前置校验失败后进入 Repair
- 验证策略下拉是否完整、修复后列表是否即时移除

#### test_gui_launch.py
- 启动 GUI 窗口
- 3 秒后自动关闭
- 验证没有启动错误

#### test_gui_log_capture.py
- 验证日志捕获器在状态回调写日志时不发生递归
- 保障“进行中动画/状态文本”稳定更新

#### create_test_data_for_gui.py
- 创建测试数据
- 生成 11 个测试文件
- 多级目录结构

**运行**:
```bash
python tests/create_test_data_for_gui.py
```

### 手动测试清单

位于 `tests/MANUAL_GUI_TEST_CHECKLIST.txt`，包含：
- GUI 启动验证
- 每个标签页功能测试
- 错误处理测试
- 边界条件测试

### 本次回归基线（2026-02-12）

以下命令已完整执行并通过（版本号保持 `3.2.0`）：
- `python -m py_compile kb_folder_manager\*.py tests\*.py`（按文件逐个展开执行）
- `python -m unittest discover tests -v`
- `python tests/test_gui_launch.py`
- `python tests/test_gui.py`
- `python tests/test_gui_batch_repair_flow.py`
- `python tests/test_progress_feedback.py`

---

## 代码规范

### Python 风格

遵循 PEP 8 标准：

- 缩进：4 个空格
- 行宽：最大 88 字符（Black 默认）
- 命名：
  - 类名：PascalCase（如 `KBFolderManagerGUI`）
  - 函数/变量：snake_case（如 `collect_compare_issues`）
  - 常量：UPPER_SNAKE_CASE（如 `DEFAULT_CONFIG`）

### 注释规范

```python
def function_name(param1, param2):
    """
    简短描述函数功能。
    
    Args:
        param1: 参数1描述
        param2: 参数2描述
    
    Returns:
        返回值描述
    
    Raises:
        异常描述
    """
    pass
```

### 类型注解

推荐使用类型注解：

```python
from typing import List, Dict, Optional

def process_files(files: List[str]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    return result
```

### 错误处理

```python
try:
    # 操作代码
    result = operation()
except SpecificException as e:
    # 具体异常处理
    log.error(f"操作失败: {e}")
    raise
finally:
    # 清理代码
    cleanup()
```

---

## 贡献指南

### 提交代码

1. **Fork 项目**
2. **创建特性分支**
   ```bash
   git checkout -b feature/your-feature
   ```

3. **编写代码**
   - 遵循代码规范
   - 添加测试用例
   - 更新文档

4. **运行测试**
   ```bash
   python -m unittest discover tests
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "Add: 新功能描述"
   ```

6. **推送到 Fork**
   ```bash
   git push origin feature/your-feature
   ```

7. **创建 Pull Request**

### 提交信息规范

格式：`<类型>: <描述>`

类型：
- `Add`: 新功能
- `Fix`: Bug 修复
- `Update`: 更新现有功能
- `Refactor`: 代码重构
- `Docs`: 文档更新
- `Test`: 测试相关
- `Style`: 代码格式

示例：
```
Add: 新增 Export 功能
Fix: 修复 Merge 时的路径错误
Update: 优化 GUI 响应速度
Docs: 更新安装文档
```

### 报告问题

使用 GitHub Issues 报告问题时，请包含：

1. **问题描述**: 清楚描述遇到的问题
2. **复现步骤**: 详细步骤
3. **期望行为**: 应该发生什么
4. **实际行为**: 实际发生了什么
5. **环境信息**:
   - 操作系统及版本
   - Python 版本
   - 项目版本

### 功能请求

提交功能请求时，请说明：

1. **功能描述**: 想要什么功能
2. **使用场景**: 为什么需要这个功能
3. **建议实现**: 如何实现（可选）

---

## 附录

### 重要设计决策

1. **不使用 setup.py/pyproject.toml**
   - 原因：项目为独立脚本，不需要安装为包
   - 影响：需要从项目根目录运行或设置 PYTHONPATH

2. **GUI 框架选择 ttkbootstrap**
   - 原因：轻量级（<5MB），内置现代主题
   - 替代方案：PyQt（>50MB）、wxPython（>50MB）

3. **线程模型**
   - GUI 使用 `threading.Thread` 而非 `multiprocessing`
   - 原因：简单，适合 I/O 密集型操作

4. **配置文件使用 YAML**
   - 原因：可读性强，易于手动编辑
   - 替代方案：JSON（不支持注释）、TOML（需额外依赖）

### 关键约束

1. **Complete 默认不改动；仅在 Repair 中用户确认后执行改动**
2. **占位符后缀是保留标记**
3. **文件类型识别基于最后一个后缀**
4. **禁止使用 UNC 网络路径**

### 性能考虑

- 大文件哈希计算：使用流式读取（1MB 块）+ 多线程并行哈希
- GUI 线程模型：后台线程避免界面冻结
- Split/Merge 复制：使用线程池并行复制
- 双目录索引：支持并行构建（doc/res、old/new）
- 并行度控制：支持环境变量 `KBFM_MAX_WORKERS`

### 已知限制

1. **平台支持**: 主要针对 Windows 优化
2. **大文件**: 超大文件（>10GB）哈希计算较慢
3. **I/O 设备限制**: 机械硬盘或网络盘可能成为性能瓶颈

---

**最后更新**: 2026-02-12 | **版本**: 3.2.0
