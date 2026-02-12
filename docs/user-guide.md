# KB Folder Manager - 用户指南

> 完整的用户使用手册，涵盖安装、配置、GUI 和 CLI 使用

**版本**: 3.2.0 | **更新日期**: 2026-02-12

---

## 目录

- [简介](#简介)
- [安装](#安装)
- [快速开始](#快速开始)
- [配置文件](#配置文件)
- [GUI 使用](#gui-使用)
- [命令行使用](#命令行使用)
- [依赖说明](#依赖说明)
- [常见问题](#常见问题)

---

## 简介

KB Folder Manager 是一个专为个人知识库整理设计的工具，提供以下核心功能：

- **Split（拆分）** - 将 Complete 目录拆分成 Doc（文档）和 Res（资源）
- **Merge（合并）** - 将 Doc 和 Res 目录合并回 Complete
- **Validate（校验）** - 验证文件夹结构是否符合规范
- **Repair（修复）** - 对 Compare、Validate、Split/Merge 前置校验发现的问题进行批量修复
- **Index（索引）** - 生成带哈希值和元数据的索引文件

### 核心设计原则

- **默认保护原目录** - 仅在用户显式选择修复策略并确认后才修改文件
- **占位符机制** - 使用空文件夹标记被移走的文件
- **闭环操作流程** - 预检 → 用户确认 → 执行 → 后检
- **哈希校验** - 支持多种哈希算法（默认 SHA256）

---

## 安装

### 系统要求

- Python 3.10 或更高版本
- Windows 操作系统（主要支持），Linux/Mac（基本支持）
- 7-Zip（可选，当前核心流程不依赖）

### 安装步骤

1. **获取项目**
   ```bash
   git clone https://github.com/buptanswer/KB-Folder-Manager.git
   cd KB-Folder-Manager
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **验证安装**
   ```bash
   # GUI 方式
   python kb_folder_manager_gui.py
   
   # CLI 方式
   python kb_folder_manager.py --help
   ```

---

## 快速开始

### 使用 GUI（推荐新手）

```powershell
# 在项目根目录运行
python kb_folder_manager_gui.py
```

### 使用命令行

```powershell
# Split 操作
python kb_folder_manager.py split --source "D:\MyKB" --output-root "D:\Output"

# Merge 操作
python kb_folder_manager.py merge --doc "D:\doc\MyKB" --res "D:\res\MyKB" --output-root "D:\Output"
```

### 测试功能

```powershell
# 创建测试数据
python tests\create_test_data_for_gui.py

# 启动 GUI 进行测试
python kb_folder_manager_gui.py
```

---

## 配置文件

项目使用 `config.yaml` 进行配置：

```yaml
# 文档侧保留的文件类型（按最后一个后缀识别）
specified_types: [
  '.pdf', '.doc', '.docx', '.txt', '.md',
  '.jpg', '.jpeg', '.png', '.gif',
  '.mp4', '.mp3', '.wav',
  # ... 更多类型
]

# 占位符后缀标记
placeholder_suffix: "(在百度网盘)"

# 哈希算法
hash_algorithm: "sha256"

# 是否启用 7-Zip 相关扩展（当前核心流程未使用）
use_7zip: true
```

### 重要说明

- `specified_types` 必须为小写并包含点号前缀
- `placeholder_suffix` 是保留标记，真实目录名严禁以该后缀结尾
- CLI 场景修改配置后需重启；GUI 可在 `Settings` 页面重载配置

---

## GUI 使用

### 启动 GUI

**方法 1：脚本启动（推荐）**
```powershell
cd KB-Folder-Manager
python kb_folder_manager_gui.py
```

**方法 2：模块方式**
```powershell
# 需要设置 PYTHONPATH
$env:PYTHONPATH = "$PWD"  # Windows
python -m kb_folder_manager.gui
```

### 界面说明

GUI 采用多标签页设计：

#### 1. Split（拆分）标签页

将 Complete 目录拆分为 Doc 和 Res。

**输入字段**：
- **Source (Complete Folder)** - 源文件夹路径
- **Output Root** - 输出根目录

**选项**：
- **Force** - 允许输出目录非空（谨慎使用）
- **Auto-confirm** - 跳过确认提示

**操作步骤**：
1. 点击 Browse 选择源文件夹
2. 选择输出目录
3. 根据需要勾选选项
4. 点击 "Execute Split Operation"
5. 观察底部全局日志 + Split 页内联日志（`Split Log (Current Tab)`）

**预期结果**：
```
OutputRoot/
├── doc/FolderName/     # 文档文件
├── res/FolderName/     # 资源文件
├── index/              # 索引文件
└── logs/               # 操作日志
```

#### 2. Merge（合并）标签页

将 Doc 和 Res 合并回 Complete。

**输入字段**：
- **Doc Folder** - Doc 文件夹路径
- **Res Folder** - Res 文件夹路径
- **Output Root** - 输出根目录

**重要**：Doc 和 Res 文件夹名称不一致时，程序会给出风险提示并要求确认；确认后可继续执行（用于同一知识库但命名不同的场景）。

**操作步骤**：
1. 分别选择 Doc 和 Res 文件夹
2. 选择输出目录
3. 点击 "Execute Merge Operation"
4. 查看底部全局日志 + Merge 页内联日志（`Merge Log (Current Tab)`）
5. 若出现确认弹窗，可选择继续或取消（无需开启 Auto-confirm）

**输出命名规则**：
- 当 Doc 与 Res 同名时：输出为该名称
- 当 Doc 与 Res 不同名且确认继续时：输出目录名称默认使用 Doc 侧名称

#### 3. Validate（校验）标签页

验证文件夹结构合规性。

**验证模式**：

- **Class1** - 基础环境检查
  - 路径合法性
  - 无符号链接
  - 无大小写冲突
  - 无 UNC 路径

- **Class2** - 类型纯净度检查
  - Doc 中只有文档类型
  - Res 中只有资源类型

- **Mutual** - Doc/Res 相互一致性
  - 结构互为镜像
  - 占位符与文件互补
  - 当 Doc/Res 根目录名不一致时会提示风险
  - CLI 默认会询问是否继续；GUI 当前版本会记录 warning 后继续执行

- **Compare** - 新旧对比
  - 哈希值和大小一致
  - mtime 差异为警告

**操作步骤**：
1. 选择验证模式
2. 填写相应输入字段
3. 指定日志目录
4. 点击 "Execute Validation"
5. 查看底部全局日志 + Validate 页内联日志（`Validation Log (Current Tab)`）

#### 4. Repair（修复）标签页

对 Compare 与其他校验失败结果执行批量修复。

**工作流**：
1. 在 Validate 或 Split/Merge 中执行检查/前置校验
2. 若发现可修复问题，程序会自动跳转到 Repair 标签页
3. 选择问题类型（如 `mtime_diff_hash_same`、`content_mismatch`）
4. 在列表中直接查看两侧文件的 `size / mtime / hash` 与提示
5. 多选要处理的路径（支持批量）
6. 选择修复策略并点击 `Apply to Selected`

**可视化决策支持**：
- 列表列包含：路径、文件夹1/2大小、文件夹1/2修改时间、文件夹1/2哈希、提示信息
- 选中单条时，底部详情区显示完整 hash 与推荐策略（仅作建议，最终由用户决定）
- 修复执行后会在当前结果集中即时移除已修复项（不强制重跑 Compare）
- mtime 比对带 1 秒容差（避免仅亚秒级抖动造成误报）
- Repair 页内联日志（`Repair Log (Current Tab)`）会同步显示修复执行细节
- 若阶段耗时较长且暂无新日志，界面会输出轻量 `running...` 心跳，避免“无响应”误解

**支持策略（按问题类型）**：
- `mtime differs but hash same`：old->new / new->old 时间对齐
- `content mismatch`（统一覆盖原 size/hash 双报错）：old 覆盖 new / new 覆盖 old
- `missing/extra`：复制补齐或按基准侧删除
- `missing/extra dir`、`missing/extra placeholder`：按侧创建目录或删除空目录
- `doc/res` 结构修复：错侧文件搬移；缺失占位符可“补占位符”或“删除对应文件”；孤立占位符可批量删除（目录需为空）；目录结构差异可按侧批量创建或删除空目录
- `complete` 预检修复：去除占位符后缀命名、删除符号链接

#### 5. Index（索引）标签页

生成文件夹索引。

**输入字段**：
- **Target Folder** - 目标文件夹
- **Output Index File** - 输出文件路径（.json）
- **Log Directory** - 日志目录

**操作步骤**：
1. 选择目标文件夹
2. 指定索引文件保存位置
3. 选择日志目录
4. 点击 "Generate Index"
5. 查看底部全局日志 + Index 页内联日志（`Index Log (Current Tab)`）

**索引文件内容**：
```json
{
  "files": {
    "path/file.txt": {
      "kind": "file",
      "size": 1234,
      "hash": "abc...",
      "hash_alg": "sha256",
      "mtime": 1769784000.123
    }
  },
  "dirs": {...},
  "placeholders": {...},
  "metadata": {...}
}
```

#### 6. Settings（设置）标签页

配置管理。

**功能**：
- 查看当前配置
- 重载配置文件
- 打开配置文件编辑

### GUI 使用技巧

1. **批处理**：勾选 Auto-confirm 可跳过确认，适合自动化
2. **错误排查**：查看日志输出区域的详细信息
3. **日志保存**：所有操作在 `logs/` 目录保存详细日志
4. **修复闭环**：Compare/Mutual/Class2/Split/Merge 前置校验失败后可直接进入 Repair 批量处理
5. **配置修改**：使用 Settings 标签页重载配置，无需重启

### GUI 故障排除

**问题 1：GUI 无法启动**

错误：`ModuleNotFoundError` 或 `AttributeError`

解决：
```powershell
pip install -r requirements.txt --upgrade
```

**问题 2：操作执行中 "Another operation is running"**

原因：上一个操作未完成

解决：等待完成或重启 GUI

**问题 3：文件夹选择后无法执行**

检查：
- 所有必填字段已填写
- 路径存在且有效
- 查看日志输出是否有错误

---

## 命令行使用

### 全局参数位置说明

- `--yes`、`--config` 是全局参数，需要写在子命令前。
- 示例：
  ```powershell
  python kb_folder_manager.py --yes split --source "D:\Data\MyKB" --output-root "D:\Output\SplitRun"
  ```

### Split（拆分）

```powershell
python kb_folder_manager.py split \
  --source "D:\Data\MyKB" \
  --output-root "D:\Output\SplitRun"
```

**可选参数**：
- `--force` - 输出目录非空时继续
- `--yes` - 全局参数，跳过确认提示（需写在子命令前）

**输出结构**：
```
OutputRoot/
├── doc/FolderName/
├── res/FolderName/
├── index/
│   ├── complete/.kb_index.json
│   ├── doc/.kb_index.json
│   └── res/.kb_index.json
└── logs/timestamp/
```

### Merge（合并）

```powershell
python kb_folder_manager.py merge \
  --doc "D:\Output\doc\MyKB" \
  --res "D:\Output\res\MyKB" \
  --output-root "D:\Output\MergeRun"
```

**说明**：
- Doc 和 Res 的文件夹名建议一致；若不一致，程序会先提示风险并要求确认，确认后可继续
- 名称不一致时，输出目录名称默认使用 Doc 侧文件夹名
- 命令行确认输入支持 `y` / `yes`；可加全局参数 `--yes` 跳过确认提示

### Validate（校验）

```powershell
# Class1 验证
python kb_folder_manager.py validate \
  --mode class1 \
  --target "D:\Data\MyKB" \
  --role complete \
  --log-dir "D:\Output\logs"

# Class2 验证
python kb_folder_manager.py validate \
  --mode class2 \
  --target "D:\Output\doc\MyKB" \
  --role doc \
  --log-dir "D:\Output\logs"

# Mutual 验证
python kb_folder_manager.py validate \
  --mode mutual \
  --doc "D:\Output\doc\MyKB" \
  --res "D:\Output\res\MyKB" \
  --log-dir "D:\Output\logs"

# Compare 验证
python kb_folder_manager.py validate \
  --mode compare \
  --old "D:\Data\MyKB" \
  --new "D:\Output\complete\MyKB" \
  --log-dir "D:\Output\logs"
```

**Mutual 名称不一致处理**：
- CLI 默认会提示你确认是否继续
- 如需无交互运行，可使用全局参数 `--yes`（放在子命令前）

### Index（索引）

```powershell
python kb_folder_manager.py index \
  --target "D:\Data\MyKB" \
  --output "D:\Output\index.json" \
  --log-dir "D:\Output\logs"
```

### 模块方式运行

如果设置了 PYTHONPATH：

```powershell
# Windows
$env:PYTHONPATH = "$PWD"
python -m kb_folder_manager.cli split --source "..." --output-root "..."

# Linux/Mac
export PYTHONPATH=$(pwd)
python -m kb_folder_manager.cli split --source "..." --output-root "..."
```

---

## 依赖说明

### 第三方库

#### PyYAML (>= 6.0)
- **用途**：读取和解析 config.yaml 配置文件
- **安装**：`pip install PyYAML`

#### ttkbootstrap (>= 1.20.0)
- **用途**：提供现代化的 GUI 组件和主题
- **安装**：`pip install ttkbootstrap`

#### pillow (>= 10.0.0)
- **用途**：GUI 的图像支持
- **安装**：`pip install pillow`

### 标准库

以下库随 Python 安装自动提供，无需额外安装：

- `pathlib`, `sys`, `os`, `time`, `datetime`
- `json`, `hashlib`, `shutil`, `tempfile`
- `threading`, `queue`, `unittest`
- `argparse`, `re`, `dataclasses`, `typing`
- `tkinter` 及其子模块

### 一键安装

```bash
pip install -r requirements.txt
```

### 验证依赖

```python
# 运行此脚本验证
import sys

dependencies = {
    'yaml': 'PyYAML',
    'ttkbootstrap': 'ttkbootstrap',
    'PIL': 'pillow',
}

for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"✓ {package} 已安装")
    except ImportError:
        print(f"✗ {package} 未安装")
```

### 虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

---

## 常见问题

### 安装问题

**Q: pip 安装失败？**

A: 尝试使用镜像源：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: tkinter 报错？**

A: Linux 需要单独安装：
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

### 使用问题

**Q: 如何处理大量文件？**

A: 可以分批处理，或使用 `--force` 参数在输出目录非空时继续

**Q: 占位符的作用？**

A: 标记原始位置，避免合并时出现问题，保留占位符可完整还原结构

**Q: 如何验证操作正确性？**

A: 每个操作生成索引文件（`.kb_index.json`），包含哈希值用于验证

**Q: Compare / Mutual / Class2 / Split-Merge 前置校验发现大量共性问题，如何快速处理？**

A: 失败后可自动进入 `Repair` 标签页，按问题类型筛选后批量多选路径，再选择统一修复策略执行。

**Q: 可以在其他操作系统使用吗？**

A: 主要针对 Windows 优化，Linux/Mac 可以尝试但某些功能可能需要调整

### 性能问题

**Q: GUI 卡顿？**

A: 大文件操作时，GUI 使用后台线程保持响应，查看进度条确认状态

**Q: 操作很慢？**

A: v3.1.0 已引入并行加速。可先确认使用最新版；如需手动调优，可设置环境变量 `KBFM_MAX_WORKERS`（例如 PowerShell：`$env:KBFM_MAX_WORKERS=16`）

---

## 附录

### 关键规则

1. **禁止使用 UNC 网络路径**，必须使用本地路径
2. **Complete 默认不改动**，仅在 Repair 中用户显式确认后执行修改
3. **占位符后缀是保留标记**，真实文件夹不能以此结尾
4. **文件类型识别基于最后一个后缀**（如 `.tar.gz` 识别为 `.gz`）

### 使用场景对比

| 特性 | GUI | CLI |
|------|-----|-----|
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 自动化 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 脚本集成 | ❌ | ✅ |
| 实时反馈 | ✅ | 部分 |
| 适用场景 | 临时操作、新手 | 批量处理、自动化 |

### 获取帮助

- **GitHub Issues**: 报告问题
- **用户手册**: 本文档
- **开发者指南**: docs/developer-guide.md
- **更新日志**: CHANGELOG.md

---

**最后更新**: 2026-02-12 | **版本**: 3.2.0
