# KB Folder Manager

一个为个人知识库整理和管理而设计的 Windows/Python 工具，提供文件夹分割、合并、校验和索引功能。**v3.1.0 引入并行加速，显著提升大目录处理速度。**

📖 **文档导航**: [用户指南](./docs/user-guide.md) | [开发者指南](./docs/developer-guide.md) | [发布说明](./docs/release-notes/v3.1.0.md) | [更新日志](./CHANGELOG.md)

## 功能特性

- **Split（拆分）** - 将 Complete 目录拆分成 Doc（文档）和 Res（资源）两个独立目录
- **Merge（合并）** - 将 Doc 和 Res 目录合并回 Complete 目录
- **Validate（校验）** - 验证文件夹结构是否符合规范
- **Index（索引）** - 生成带哈希值和元数据的索引文件

## 核心设计原则

- **Complete 目录严格只读** - 保护原始数据完整性
- **占位符机制** - 使用空文件夹作为占位符，标记被移走的文件
- **闭环操作流程** - 预检 → 用户确认 → 执行 → 后检
- **哈希校验** - 支持多种哈希算法（默认 SHA256）

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 操作系统
- 7-Zip（可选，用于压缩功能）

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

#### 拆分（Split）
将知识库拆分为文档和资源：
```powershell
python kb_folder_manager.py split --source "D:\Data\MyKB" --output-root "D:\Output\SplitRun"
```

**可选参数：**
- `--force` - 输出目录非空时继续执行（需谨慎）
- `--yes` - 跳过确认提示，直接执行

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
python kb_folder_manager.py merge --doc-root "D:\Output\doc" --res-root "D:\Output\res" --output-root "D:\Output\MergeRun"
```

#### 校验（Validate）
检查文件夹结构是否合规：
```powershell
python kb_folder_manager.py validate --path "D:\Data\MyKB"
```

#### 索引（Index）
为指定目录生成索引：
```powershell
python kb_folder_manager.py index --path "D:\Data\MyKB" --output "index.json"
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

# 是否使用 7-Zip 进行压缩操作
use_7zip: true
```

**重要提示：**
- `specified_types` 必须为小写并包含点号前缀（如 `.pdf`）
- `placeholder_suffix` 是保留标记，真实目录名严禁以该后缀结尾
- 修改配置后重启程序生效

## 项目结构

```
KB-Folder-Manager/
├── kb_folder_manager/
│   ├── __init__.py
│   ├── cli.py                 # 命令行接口
│   ├── config.py              # 配置管理
│   ├── indexer.py             # 索引生成
│   ├── operations.py          # 核心操作（split/merge/validate）
│   ├── utils.py               # 工具函数
│   └── validator.py           # 校验逻辑
├── tests/
│   └── test_basic.py          # 基础测试
├── kb_folder_manager.py       # 入口文件
├── requirements.txt           # 依赖列表
├── config.yaml                # 配置文件
├── README.md                  # 本文件
└── 用户手册.md                # 详细用户手册
```

## 文档

### 主要文档
- **[用户指南](./docs/user-guide.md)** - 完整的用户使用手册（含安装、配置、GUI、CLI）
- **[开发者指南](./docs/developer-guide.md)** - 开发文档（含架构、测试、贡献指南）
- **[发布说明 v3.1.0](./docs/release-notes/v3.1.0.md)** - v3.1.0 版本更新详情
- **[更新日志](./CHANGELOG.md)** - 完整的版本更新记录

### 历史文档
- [项目设计文档](./KB-Folder-Manager项目文档/KB%20Folder%20Manager%20项目需求与设计文档%20(v2.8).md) - 完整的技术设计和需求分析
- [KB-Folder-Manager项目文档/](./KB-Folder-Manager项目文档/) - 历史版本文档

## 常见问题

详细问题解答请参考 [用户指南 - 常见问题章节](./docs/user-guide.md#常见问题)。

**快速答案**：
- **如何处理大量文件？** - v3.1.0 已支持并行加速；可通过 `KBFM_MAX_WORKERS` 调整并发度
- **占位符的作用？** - 标记原始位置，避免合并时出现问题
- **如何验证正确性？** - 查看生成的 `.kb_index.json` 索引文件
- **其他操作系统？** - 主要针对 Windows，Linux/Mac 可尝试但需调整

## 开发

### 运行测试
```bash
python -m unittest discover tests
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

**最后更新：** 2026年2月11日 | **版本：** v3.1.0
