# 文档索引

欢迎查阅 KB Folder Manager 的完整文档。

---

## 📁 文档结构

```
KB-Folder-Manager/
├── README.md                       # 项目概览和快速开始
├── AGENTS.md                       # AI 助手指令
├── CHANGELOG.md                    # 版本更新记录
├── docs/
│   ├── README.md                   # 本文件（文档索引）
│   ├── user-guide.md               # 用户指南（完整）
│   ├── developer-guide.md          # 开发者指南
│   ├── MUTUAL_VALIDATION_TREEVIEW_FIX.md  # Bug 修复案例
│   └── release-notes/
│       ├── v3.0.md                 # v3.0 发布说明
│       ├── v3.1.0.md               # v3.1.0 发布说明
│       ├── v3.2.0.md               # v3.2.0 发布说明
│       └── v3.2.1.md               # v3.2.1 发布说明（最新）
└── tests/                          # 测试文件
```

---

## 📖 快速导航

### 👤 普通用户

| 需求 | 文档位置 |
|------|---------|
| **快速开始** | [README.md](../README.md) |
| **完整使用指南** | [user-guide.md](user-guide.md) |
| **GUI 使用说明** | [user-guide.md - GUI 章节](user-guide.md#gui-界面使用) |
| **命令行使用** | [user-guide.md - CLI 章节](user-guide.md#命令行使用) |
| **版本更新内容** | [CHANGELOG.md](../CHANGELOG.md) |
| **详细发布说明** | [release-notes/](release-notes/) |

### 👨‍💻 开发者

| 需求 | 文档位置 |
|------|---------|
| **项目结构** | [developer-guide.md](developer-guide.md) |
| **开发指南** | [developer-guide.md](developer-guide.md) |
| **AI 协作指令** | [AGENTS.md](../AGENTS.md) |
| **测试说明** | [developer-guide.md - 测试章节](developer-guide.md) |
| **Bug 修复案例** | [MUTUAL_VALIDATION_TREEVIEW_FIX.md](MUTUAL_VALIDATION_TREEVIEW_FIX.md) |

---

## 🔍 文档说明

### 核心文档

- **README.md** - 项目简介、特性、快速开始、安装说明
- **CHANGELOG.md** - 所有版本的变更记录（精简格式）
- **user-guide.md** - 完整的用户使用手册（GUI + CLI + 所有操作说明）
- **developer-guide.md** - 开发者文档（架构、测试、贡献指南）

### 发布说明

每个版本都有详细的发布说明文档：
- **v3.0.md** - GUI 重构版本
- **v3.1.0.md** - 性能并行化优化
- **v3.2.0.md** - 批量修复闭环工作流
- **v3.2.1.md** - Bug 修复版本（Mutual 验证树形视图）

### 技术案例

- **MUTUAL_VALIDATION_TREEVIEW_FIX.md** - 详细记录了一次复杂 GUI bug 的完整调试过程

---

## ✏️ 文档维护

### 更新指南

| 变更类型 | 需要更新的文档 |
|---------|---------------|
| **新增功能** | `user-guide.md` + `CHANGELOG.md` |
| **版本发布** | `CHANGELOG.md` + 创建新的 `release-notes/vX.X.X.md` |
| **架构变更** | `developer-guide.md` |
| **项目信息** | `README.md` |
| **AI 协作规范** | `AGENTS.md` |

### 编写原则

- ✅ 一个功能只在一处详细说明，其他地方用链接引用
- ✅ 保持文档同步更新，避免过时信息
- ✅ 使用清晰的标题和目录结构
- ✅ 提供代码示例和实际用例
- ❌ 避免内容重复
- ❌ 避免创建过多临时文档

---

**当前版本**: v3.2.1  
**最后更新**: 2026-02-14
