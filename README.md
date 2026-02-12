# KB Folder Manager

一个为个人知识库整理和管理而设计的 Windows/Python 工具，提供文件夹分割、合并、校验、索引与批量修复功能。**v3.2.0 新增“校验后批量修复”闭环工作流。**

📖 **文档导航**: [用户指南](./docs/user-guide.md) | [开发者指南](./docs/developer-guide.md) | [发布说明](./docs/release-notes/v3.2.0.md) | [更新日志](./CHANGELOG.md)

## 功能特性

- **Split（拆分）** - 将 Complete 目录拆分成 Doc（文档）和 Res（资源）两个独立目录
- **Merge（合并）** - 将 Doc 和 Res 目录合并回 Complete 目录
- **Validate（校验）** - 验证文件夹结构是否符合规范
- **Repair（修复）** - 对 Compare、Validate、Split/Merge 前置校验发现的共性问题进行批量修复
- **Index（索引）** - 生成带哈希值和元数据的索引文件

## 核心设计原则

- **默认保护原目录** - 所有修复都要求用户显式选择策略并确认后执行
- **占位符机制** - 使用空文件夹作为占位符，标记被移走的文件
- **闭环操作流程** - 预检 → 用户确认 → 执行 → 后检
- **哈希校验** - 支持多种哈希算法（默认 SHA256）

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 操作系统
- 7-Zip（可选，当前核心流程不依赖）

### 安装

1. 克隆或下载项目：
```bash
git clone https://github.com/buptanswer/KB-Folder-Manager.git
cd KB-Folder-Manager
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

**注意**：项目使用相对导入，所有命令需要在项目根目录下运行。如果需要从其他目录调用，可以：

**方法 1**：将项目目录添加到 PYTHONPATH
```powershell
# Windows PowerShell
$env:PYTHONPATH = "C:\path\to\KB-Folder-Manager"
python -m kb_folder_manager.gui

# 或在当前会话临时设置
$env:PYTHONPATH = "$PWD"
python -m kb_folder_manager.gui
```

```bash
# Linux/Mac
export PYTHONPATH=/path/to/KB-Folder-Manager
python -m kb_folder_manager.gui
```

**方法 2**（推荐）：在项目根目录直接运行
```powershell
cd KB-Folder-Manager
python kb_folder_manager_gui.py
```

### 使用方式

#### 🎨 GUI 图形界面（推荐新手使用）

启动图形界面：
```powershell
python kb_folder_manager_gui.py
```

GUI 提供：
- 直观的可视化操作界面
- 实时进度显示和日志输出
- 友好的错误提示
- 无需记忆命令参数

**快速测试 GUI**：
```powershell
# 创建测试数据并按照屏幕提示操作
python tests\create_test_data_for_gui.py
python kb_folder_manager_gui.py
```

详细使用说明请参考：[用户指南 - GUI 使用章节](./docs/user-guide.md#gui-使用)

#### ⌨️ 命令行界面（适合自动化）

命令行适合脚本自动化和批量处理。

全局参数（如 `--yes`、`--config`）需要放在子命令前，例如：
```powershell
python kb_folder_manager.py --yes split --source "D:\Data\MyKB" --output-root "D:\Output\SplitRun"
```

#### 拆分（Split）
将知识库拆分为文档和资源：
```powershell
python kb_folder_manager.py split --source "D:\Data\MyKB" --output-root "D:\Output\SplitRun"
```

**可选参数：**
- `--force` - 输出目录非空时继续执行（需谨慎）
- `--yes` - 全局参数，跳过确认提示（需写在子命令前）

**输出结构：**
```
OutputRoot/
├── doc/<FolderName>/          # 文档文件
├── res/<FolderName>/          # 资源文件
└── index/
    ├── complete/.kb_index.json
    ├── doc/.kb_index.json
    └── res/.kb_index.json
```

#### 合并（Merge）
将拆分的文档和资源合并回 Complete 目录：
```powershell
python kb_folder_manager.py merge --doc "D:\Output\doc\MyKB" --res "D:\Output\res\MyKB" --output-root "D:\Output\MergeRun"
```

**说明：**
- Doc/Res 根目录名建议一致；若不一致会先提示并要求确认，确认后仍可继续
- 名称不一致时，输出 `complete/<FolderName>` 默认使用 `doc` 侧文件夹名
- 交互确认可输入 `y` 或 `yes`；可加全局参数 `--yes` 跳过确认提示

#### 校验（Validate）
检查文件夹结构是否合规：
```powershell
python kb_folder_manager.py validate --mode class1 --target "D:\Data\MyKB" --role complete --log-dir "D:\Output\logs"
```

#### 索引（Index）
为指定目录生成索引：
```powershell
python kb_folder_manager.py index --target "D:\Data\MyKB" --output "D:\Output\index.json" --log-dir "D:\Output\logs"
```

## 配置文件

项目使用 `config.yaml` 进行配置，主要字段说明：

```yaml
# 文档侧保留的文件类型列表（基于最后一个后缀识别）
specified_types: ['.pdf', '.doc', '.docx', '.txt', '.md', ...]

# 占位符后缀标记（表示该文件已被移走）
placeholder_suffix: "(在百度网盘)"

# 哈希算法选择
hash_algorithm: "sha256"

# 是否启用 7-Zip 相关扩展（当前核心流程未使用）
use_7zip: true
```

**重要提示：**
- `specified_types` 必须为小写并包含点号前缀（如 `.pdf`）
- `placeholder_suffix` 是保留标记，真实目录名严禁以该后缀结尾
- CLI 场景修改配置后需重启；GUI 可在 `Settings` 标签页点击重载配置

## 项目结构

```
KB-Folder-Manager/
├── kb_folder_manager/
│   ├── __init__.py
│   ├── cli.py                 # 命令行接口
│   ├── config.py              # 配置管理
│   ├── indexer.py             # 索引生成
│   ├── operations.py          # 核心操作（split/merge/validate/repair）
│   ├── utils.py               # 工具函数
│   └── validator.py           # 校验逻辑
├── tests/
│   ├── test_basic.py
│   ├── test_compare_repair.py
│   ├── test_gui_batch_repair_flow.py
│   ├── test_gui.py
│   └── test_gui_launch.py
├── docs/
│   ├── user-guide.md
│   ├── developer-guide.md
│   └── release-notes/
├── kb_folder_manager.py       # 入口文件
├── kb_folder_manager_gui.py   # GUI 入口文件
├── requirements.txt           # 依赖列表
├── config.yaml                # 配置文件
├── CHANGELOG.md               # 更新日志
└── README.md                  # 本文件
```

## 文档

### 主要文档
- **[用户指南](./docs/user-guide.md)** - 完整的用户使用手册（含安装、配置、GUI、CLI）
- **[开发者指南](./docs/developer-guide.md)** - 开发文档（含架构、测试、贡献指南）
- **[发布说明 v3.2.0](./docs/release-notes/v3.2.0.md)** - v3.2.0 版本更新详情
- **[更新日志](./CHANGELOG.md)** - 完整的版本更新记录

### 历史文档
- [项目设计文档](./KB-Folder-Manager项目文档/KB%20Folder%20Manager%20项目需求与设计文档%20(v2.8).md) - 完整的技术设计和需求分析
- [KB-Folder-Manager项目文档/](./KB-Folder-Manager项目文档/) - 历史版本文档

## 常见问题

详细问题解答请参考 [用户指南 - 常见问题章节](./docs/user-guide.md#常见问题)。

**快速答案**：
- **如何处理大量文件？** - v3.1.0 已支持并行加速；可通过 `KBFM_MAX_WORKERS` 调整并发度
- **发现大量一致性问题如何快速处理？** - 无论是 Compare、Mutual/Class2 校验失败，还是 Split/Merge 前置校验失败，都可自动进入 `Repair` 批量处理
- **占位符的作用？** - 标记原始位置，避免合并时出现问题
- **如何验证正确性？** - 查看生成的 `.kb_index.json` 索引文件
- **其他操作系统？** - 主要针对 Windows，Linux/Mac 可尝试但需调整

## 开发

### 运行测试
```bash
# 单元测试（含 CLI 烟雾）
python -m unittest discover tests

# GUI 启动烟雾
python tests/test_gui_launch.py

# GUI 功能模拟（Split/Merge/Validate/Index）
python tests/test_gui.py

# GUI Compare->Repair 批量修复全流程模拟
python tests/test_gui_batch_repair_flow.py

# 进度与状态反馈验证
python tests/test_progress_feedback.py
```

### 更多开发信息
详见 [开发者指南](./docs/developer-guide.md)

## 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

## 作者

Created by buptanswer

## 更新日志

### v3.2.0 (2026-02-12)
- 🔧 **新增 Compare 批量修复工作流**
  - `Validate -> Compare` 后自动进入 `Repair` 标签页
  - 支持按问题类型筛选与多选路径批量修复
  - Repair 列表直接展示两侧 `size / mtime / hash` 列与提示信息，便于就地决策
  - 修复完成后即时移除当前已修复项（不强制重跑 Compare）
  - 支持 `mtime differs but hash same` 的双向 mtime 对齐
  - 将 `size/hash` 统一为单一 `content mismatch` 错误并支持双向覆盖修复
  - 支持 `missing/extra` 的补齐复制或按基准侧删除
  - 支持 `missing/extra dir` 与 `missing/extra placeholder` 的目录创建/删除修复
  - 扩展到非 Compare 流程：`Validate(mutual/class2)` 与 `Split/Merge` 失败时自动生成 Repair 方案并跳转
  - 新增 Doc/Res 纠偏修复（错侧文件搬移、缺失占位符可补齐或删除对应文件、孤立占位符删除、目录差异按侧创建/删除空目录）
  - 新增 Complete 预检修复（占位符后缀命名清理、符号链接删除）
- 🧱 **后端能力升级**
  - 新增结构化 Compare 问题模型（供 GUI 与自动化逻辑复用）
  - 新增批量修复 API 与修复日志
- 🖥️ **GUI 体验一致性优化**
  - Split / Merge / Validate / Repair / Index 全部提供当前页内联日志框
  - 比较索引阶段恢复细粒度进度输出（不再长时间无反馈）
  - 长耗时阶段在无新日志时追加轻量 `running...` 心跳提示
  - 修复日志回调递归风险，确保进度与状态动画稳定显示

### v3.1.0 (2026-02-11)
- 🚀 **并行性能优化（CPU 利用率提升）**
  - 索引阶段支持多线程并行哈希计算，自动按 CPU 核心数分配 worker
  - Split/Merge 文件复制改为并行执行，提升大批量文件吞吐
  - 双目录索引场景（Doc/Res、Compare）改为并行构建
  - 新增 `KBFM_MAX_WORKERS` 环境变量，可手动控制并行度
- 🧩 **版本管理优化**
  - 新增统一版本常量 `kb_folder_manager.__version__`
  - GUI 标题与测试输出改为引用统一版本号

### v3.0 (2026-01-30)
- 🎉 **新增图形用户界面 (GUI)**
  - 基于 ttkbootstrap 的现代化界面设计
  - 支持所有核心功能：Split、Merge、Validate、Index
  - 实时进度条和日志输出
  - 友好的文件/文件夹浏览器
  - 配置管理界面
- 完整的 GUI 测试套件
- 新增 GUI 使用指南文档

### v2.8
- 完善索引生成功能
- 优化文件校验逻辑
- 改进用户交互体验

### v2.0
- 核心功能实现
- 命令行接口

## 联系方式

如有问题或建议，欢迎通过以下方式联系：
- 提交 GitHub Issue
- 或直接邮件联系

---

**最后更新：** 2026年2月12日 | **版本：** v3.2.0
