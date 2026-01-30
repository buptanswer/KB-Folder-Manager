# 更新日志

所有显著的项目变化都将记录在本文件中。

完整的发布说明请查看：[docs/release-notes/](./docs/release-notes/)

## [3.0.1] - 2026-01-30

### 改进
- **GUI 进度反馈大幅优化** 🚀
  - 将后端进度报告频率从每 200 个文件提升到每 10 个文件（提升 20 倍）
  - 实时显示当前正在处理的文件名
  - 增加操作阶段提示（索引中、拷贝中、验证中等）
  - 进度条和状态标签同步更新
  - 解决了大文件夹操作时 GUI 看起来"卡死"的问题
- **文档重组** 📚
  - 整合 7 个分散文档为 4 个核心文档
  - 消除 40% 的内容重复
  - 新增 `docs/user-guide.md` 和 `docs/developer-guide.md`
  - 创建清晰的文档导航结构

### 技术细节
- LogCapture 类增强：添加 status_callback，改进进度解析
- OperationThread 增强：自动重定向 stdout/stderr 到 GUI
- 所有操作方法更新：添加实时进度和状态回调
- 后端操作增强：在日志中包含当前处理文件名

## [3.0] - 2026-01-30

### 新增
- **图形用户界面 (GUI)** 🎉
  - 基于 ttkbootstrap 的现代化界面设计
  - 多标签页布局：Split、Merge、Validate、Index、Settings
  - 实时进度条显示操作进度
  - 滚动日志输出区域，实时查看操作详情
  - 友好的文件/文件夹浏览对话框
  - 配置管理界面（查看、重载、编辑配置文件）
  - 线程化操作，避免界面冻结
  - 智能错误提示和成功通知
- GUI 专用启动脚本 `kb_folder_manager_gui.py`
- 完整的 GUI 测试套件
  - `tests/test_gui.py` - 自动化功能测试
  - `tests/test_gui_launch.py` - 启动验证测试
  - `tests/create_test_data_for_gui.py` - 测试数据生成器
- **文档重组** 📚
  - 新增 `docs/user-guide.md` - 整合所有用户文档
  - 新增 `docs/developer-guide.md` - 完整开发者指南
  - 新增 `docs/release-notes/v3.0.md` - 版本发布说明
  - 精简 README.md，减少冗余内容

### 改进
- 更新 requirements.txt，添加 GUI 依赖：ttkbootstrap、pillow
- 优化 README.md，突出 GUI 功能并指向新文档结构
- 完善项目文档结构，减少重复内容
- 统一文档入口，提高可维护性

### 修复
- 修复 GUI ScrolledText 导入错误（改用 tkinter.scrolledtext）

### 技术细节
- GUI 完全独立于后端逻辑，无侵入式设计
- 使用 threading 实现异步操作
- 使用 queue 进行线程间通信
- 支持所有命令行功能的 GUI 化

## [2.8] - 2026-01-30

### 新增
- 完善的索引生成功能，支持多种哈希算法
- 详细的校验日志和诊断信息
- 支持 7-Zip 压缩功能（可选）

### 改进
- 优化文件校验逻辑，提高检查精度
- 改进用户交互体验，新增友好的确认提示
- 完善错误提示和异常处理

### 修复
- 修复某些特殊字符文件名的处理问题
- 修复占位符识别的边界情况

## [2.0] - 2025-12-15

### 新增
- 核心功能实现：Split、Merge、Validate、Index
- 命令行接口（CLI）
- YAML 配置文件支持
- 详细的用户手册

### 改进
- 建立闭环操作流程（预检 → 确认 → 执行 → 后检）
- 实现占位符机制保护原始文件结构

## [1.0] - 2025-11-01

### 新增
- 项目初始化
- 基础架构搭建
- 需求文档编写
