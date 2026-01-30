### Tag version（标签版本）
```
v2.8
```

### Release title（发布标题）
```
KB Folder Manager v2.8 - Initial Public Release
```

或中文版本：
```
KB Folder Manager v2.8 - 首次公开发布
```

### Release description（发布描述）

```markdown
# KB Folder Manager v2.8

**首次公开发布版本**

## ✨ 主要功能

- **Split（拆分）** - 将知识库拆分为文档和资源
- **Merge（合并）** - 将拆分的内容合并回原目录
- **Validate（校验）** - 验证文件夹结构是否合规
- **Index（索引）** - 生成带哈希值的索引文件

## 🎯 核心特性

- ✅ Complete 目录严格只读保护
- ✅ 占位符机制保留原始结构
- ✅ 闭环操作流程（预检 → 确认 → 执行 → 后检）
- ✅ SHA256 哈希校验
- ✅ 支持 7-Zip 压缩
- ✅ YAML 灵活配置
- ✅ 详细的中文文档

## 🚀 快速开始

### 安装
```bash
git clone https://github.com/buptanswer/KB-Folder-Manager.git
cd KB-Folder-Manager
pip install -r requirements.txt
```

### 基本使用
```powershell
# 拆分知识库
python kb_folder_manager.py split --source "D:\MyKB" --output-root "D:\Output"

# 合并回原位置
python kb_folder_manager.py merge --doc-root "D:\Output\doc" --res-root "D:\Output\res" --output-root "D:\FinalOutput"

# 校验文件夹结构
python kb_folder_manager.py validate --path "D:\MyKB"

# 生成索引
python kb_folder_manager.py index --path "D:\MyKB" --output "index.json"
```

## 📚 文档

- 📖 [README](./README.md) - 项目概览和使用指南
- 📘 [用户手册](./用户手册.md) - 详细的功能说明
- 📗 [项目设计文档](./KB-Folder-Manager项目文档/KB%20Folder%20Manager%20项目需求与设计文档%20(v2.8).md) - 技术设计细节

## 💻 系统要求

- Python 3.10 或更高版本
- Windows 操作系统
- 7-Zip（可选，用于压缩功能）

## 📝 版本说明

这是首个公开发布的稳定版本，包含完整的核心功能和详细文档。

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**发布日期**：2026-01-30
```
