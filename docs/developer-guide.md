# KB Folder Manager - 开发者指南

> 完整的开发文档，涵盖架构、测试、贡献指南

**版本**: 3.0 | **更新日期**: 2026-01-30

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
│   ├── operations.py           # 核心业务逻辑（288 行）
│   ├── utils.py                # 工具函数（122 行）
│   ├── cli.py                  # 命令行接口（93 行）
│   └── gui.py                  # 图形界面（873 行）
├── kb_folder_manager.py        # CLI 入口
├── kb_folder_manager_gui.py    # GUI 入口
├── config.yaml                 # 配置文件
├── requirements.txt            # 依赖清单
├── tests/                      # 测试目录
│   ├── test_basic.py
│   ├── test_gui.py
│   ├── test_gui_launch.py
│   └── create_test_data_for_gui.py
├── docs/                       # 文档
│   ├── user-guide.md           # 用户指南
│   ├── developer-guide.md      # 开发者指南（本文档）
│   └── release-notes/          # 发布说明
│       └── v3.0.md
├── CHANGELOG.md                # 更新日志
└── README.md                   # 项目说明
```

### 架构设计原则

1. **模块分离**: 核心业务逻辑与接口（CLI/GUI）完全分离
2. **非侵入性**: GUI 作为包装层，不修改任何后端代码
3. **闭环流程**: 所有操作遵循"预检 → 确认 → 执行 → 后检"流程
4. **线程安全**: GUI 操作使用独立线程，避免界面冻结

### 模块依赖关系

```
kb_folder_manager_gui.py ─→ gui.py ─┐
kb_folder_manager.py ─────→ cli.py ─┼─→ operations.py ─→ utils.py
                                     └─→ utils.py
```

---

## 核心模块详解

### operations.py（核心业务逻辑）

**职责**: 实现所有核心操作（Split、Merge、Validate、Index）

**主要类**:

- `OperationContext`: 操作上下文数据类
- `KBFolderOperations`: 核心操作类

**关键方法**:

```python
class KBFolderOperations:
    def split(self, source, output_root, force=False, auto_confirm=False):
        """拆分 Complete 目录为 Doc 和 Res"""
    
    def merge(self, doc_path, res_path, output_root, force=False, auto_confirm=False):
        """合并 Doc 和 Res 为 Complete"""
    
    def validate(self, mode, **kwargs):
        """验证文件夹结构"""
    
    def index(self, target_folder, output_index_file, log_dir=None):
        """生成索引文件"""
```

**设计模式**: 策略模式（Validate 有 4 种验证模式）

### utils.py（工具函数）

**职责**: 提供通用工具函数

**主要函数**:

```python
def compute_hash(file_path, algorithm="sha256"):
    """计算文件哈希值"""

def is_specified_type(filename, specified_types):
    """判断文件是否为指定类型"""

def is_placeholder(name, suffix):
    """判断是否为占位符文件夹"""

def normalize_path(path):
    """路径规范化"""
```

### cli.py（命令行接口）

**职责**: 解析命令行参数，调用 operations 模块

**实现**: 使用 `argparse` 构建子命令系统

**子命令**:
- `split` - 拆分操作
- `merge` - 合并操作
- `validate` - 验证操作
- `index` - 索引操作

**示例**:
```python
def run_split(args):
    ops = KBFolderOperations(args.config)
    ops.split(args.source, args.output_root, args.force, args.yes)
```

### gui.py（图形界面）

**职责**: 提供现代化的图形用户界面

**架构设计**:

1. **OperationThread**: 独立线程运行后端操作
   ```python
   class OperationThread(threading.Thread):
       def run(self):
           result = self.func(*self.args, **self.kwargs)
           self.result_queue.put(result)
   ```

2. **LogCapture**: 捕获日志输出到 GUI
   ```python
   class LogCapture:
       def write(self, text):
           self.log_widget.insert(tk.END, text)
   ```

3. **KBFolderManagerGUI**: 主窗口类
   - 5 个标签页：Split, Merge, Validate, Index, Settings
   - 实时日志输出
   - 进度条显示

**关键代码**:
```python
class KBFolderManagerGUI:
    def __init__(self, master):
        self.notebook = ttk.Notebook(master)
        self.create_split_tab()
        self.create_merge_tab()
        # ... 其他标签页
    
    def execute_operation(self, operation_func, *args):
        thread = OperationThread(operation_func, *args)
        thread.start()
        self.check_operation_status(thread)
```

---

## 测试指南

### 运行测试

```bash
# 运行所有测试
python -m unittest discover tests

# 运行单个测试文件
python tests/test_basic.py
python tests/test_gui.py

# GUI 启动测试
python tests/test_gui_launch.py
```

### 测试文件说明

#### test_basic.py
- 基础功能测试
- 文件系统操作测试
- 配置加载测试

#### test_gui.py
- GUI 后端集成测试
- 模拟用户点击操作
- 验证所有操作正确性
- **不启动真实 GUI 窗口**

**测试用例**:
```python
def test_01_load_config(self):
    """测试配置加载"""

def test_02_split_operation(self):
    """测试 Split 操作"""

def test_03_merge_operation(self):
    """测试 Merge 操作"""

def test_04_validate_operation(self):
    """测试 Validate 操作"""

def test_05_index_operation(self):
    """测试 Index 操作"""
```

#### test_gui_launch.py
- 启动 GUI 窗口
- 3 秒后自动关闭
- 验证没有启动错误

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

---

## 代码规范

### Python 风格

遵循 PEP 8 标准：

- 缩进：4 个空格
- 行宽：最大 88 字符（Black 默认）
- 命名：
  - 类名：PascalCase（如 `KBFolderOperations`）
  - 函数/变量：snake_case（如 `compute_hash`）
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

1. **Complete 目录严格只读**
2. **占位符后缀是保留标记**
3. **文件类型识别基于最后一个后缀**
4. **禁止使用 UNC 网络路径**

### 性能考虑

- 大文件哈希计算：使用流式读取（8KB 块）
- GUI 线程模型：后台线程避免界面冻结
- 日志输出：使用队列缓冲，避免频繁刷新

### 已知限制

1. **平台支持**: 主要针对 Windows 优化
2. **大文件**: 超大文件（>10GB）哈希计算较慢
3. **并发**: 不支持并行处理多个文件夹

---

**最后更新**: 2026-01-30 | **版本**: 3.0
