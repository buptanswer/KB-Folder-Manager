# 文档整合说明

## v3.0 文档重组

为了减少冗余和提高可维护性，项目文档已重新整合。

### 新的文档结构

```
KB-Folder-Manager/
├── README.md                       # 项目概览和快速开始
├── CHANGELOG.md                    # 版本更新记录
├── docs/
│   ├── user-guide.md               # 完整用户指南（整合）
│   ├── developer-guide.md          # 开发者指南
│   └── release-notes/
│       └── v3.0.md                 # 版本发布说明
└── KB-Folder-Manager项目文档/      # 历史文档（保留）
    └── ...
```

### 文档整合映射

#### 已整合文件

以下文件的内容已整合到新文档中：

| 旧文件 | 整合到 | 说明 |
|--------|--------|------|
| `GUI使用指南.md` | `docs/user-guide.md` | GUI 使用章节 |
| `用户手册.md` | `docs/user-guide.md` | 各操作说明章节 |
| `QUICKSTART.md` | `docs/user-guide.md` | 快速开始章节 |
| `DEPENDENCIES.md` | `docs/user-guide.md` | 依赖说明章节 |
| `v3.0_RELEASE_NOTES.md` | `docs/release-notes/v3.0.md` | 直接移动 |
| `.github/copilot-instructions.md` | `docs/developer-guide.md` | 开发者指南基础 |

#### 保留文件

- `README.md` - 精简版项目说明（仅包含核心信息）
- `CHANGELOG.md` - 版本更新日志（保持独立）
- `KB-Folder-Manager项目文档/` - 历史设计文档（v2.8 及之前）

### 文档查找指南

**我想了解如何...**

- **安装和快速开始** → `README.md`
- **使用 GUI 界面** → `docs/user-guide.md` (GUI 使用章节)
- **使用命令行** → `docs/user-guide.md` (命令行使用章节)
- **配置项目** → `docs/user-guide.md` (配置文件章节)
- **解决问题** → `docs/user-guide.md` (常见问题章节)
- **了解依赖** → `docs/user-guide.md` (依赖说明章节)
- **参与开发** → `docs/developer-guide.md`
- **了解项目架构** → `docs/developer-guide.md` (项目架构章节)
- **运行测试** → `docs/developer-guide.md` (测试指南章节)
- **查看版本更新** → `CHANGELOG.md` 或 `docs/release-notes/`
- **了解 v2.8 设计** → `KB-Folder-Manager项目文档/`

### 整合收益

✅ **减少冗余** - 移除了大量重复内容  
✅ **便于维护** - 单一信息源，更新更简单  
✅ **结构清晰** - 按用户/开发者角色分类  
✅ **易于查找** - 统一的文档入口  
✅ **版本控制** - 更好的历史追踪

### 迁移日期

2026-01-30

---

**如有疑问，请查看 README.md 中的文档导航部分。**
