# KB Folder Manager

一个为个人知识库整理和管理而设计的 Windows/Python 工具，提供文件夹分割、合并、校验和索引功能。

[用户手册完整版](#文档) | [项目需求与设计](./KB-Folder-Manager项目文档/KB%20Folder%20Manager%20项目需求与设计文档%20(v2.8).md)

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

### 基本用法

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

- [用户手册](./用户手册.md) - 详细的功能说明和使用指南
- [项目设计文档](./KB-Folder-Manager项目文档/KB%20Folder%20Manager%20项目需求与设计文档%20(v2.8).md) - 完整的技术设计和需求分析
- 更多历史文档见 [KB-Folder-Manager项目文档/](./KB-Folder-Manager项目文档/)

## 常见问题

### Q: 如何处理大量文件？
A: 可以分批处理，或使用 `--force` 参数在输出目录非空的情况下继续执行。

### Q: 占位符的作用是什么？
A: 占位符（空文件夹）用来标记原始位置，避免合并时出现问题。保留占位符可以完整还原目录结构。

### Q: 如何验证操作的正确性？
A: 每个操作都会生成索引文件（`.kb_index.json`），包含哈希值，可用于验证文件完整性。

### Q: 可以使用其他操作系统吗？
A: 当前主要针对 Windows 优化。Linux/Mac 用户可以尝试，但某些功能（如 7-Zip）可能需要调整。

## 开发

### 运行测试
```bash
python -m pytest tests/
```

### 代码结构说明

- **cli.py** - 命令行参数解析和主流程控制
- **operations.py** - Split、Merge、Validate 的核心算法实现
- **indexer.py** - 文件索引生成和校验
- **validator.py** - 文件夹结构合规性检查
- **config.py** - YAML 配置加载和管理
- **utils.py** - 通用工具函数（路径处理、日志等）

## 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

## 作者

Created by buptanswer

## 更新日志

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

**最后更新：** 2026年1月30日
