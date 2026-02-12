# 更新日志

所有显著的项目变化都将记录在本文件中。

完整的发布说明请查看：[docs/release-notes/](./docs/release-notes/)

## [3.2.0] - 2026-02-12

### 新增
- **Compare 批量修复闭环工作流** 🎯
  - GUI 新增 `Repair` 标签页，支持在 `Validate -> Compare` 后直接跳转修复
  - 支持按问题类型筛选、批量多选路径、选择策略后一键修复
  - 支持的核心修复策略：
    - `mtime differs but hash same`：old->new / new->old 对齐 mtime
    - `content mismatch`（统一 size/hash）：old 覆盖 new / new 覆盖 old
    - `missing file in new`、`extra file in new`：复制补齐或按基准删除
    - `missing/extra dir`、`missing/extra placeholder`：创建对应目录或删除空目录
  - 扩展到 `Validate(mutual/class2)` 与 `Split/Merge` 失败场景：可自动生成修复建议并跳转 Repair

### 改进
- **Compare 结构化问题模型** 🧩
  - 新增结构化 Compare issue 收集逻辑，统一日志输出与 GUI 修复入口
  - Compare 问题新增目录与占位符差异的逐项记录
- **Repair 交互细节打磨**
  - 修复列表增加两侧 `size / mtime / hash` 摘要列
  - 新增单条问题详情区与策略建议，减少手动切到资源管理器比对
  - 修复完成后即时移除当前已修复项（不强制重跑 Compare）
  - Compare 的 mtime 判断增加 1 秒容差，降低亚秒级误报
  - Compare 阶段补充进行中动画和开始日志，避免“点击后无反馈”
  - 新增 `doc/res` 修复策略：错侧文件搬移、缺失占位符补齐、孤立占位符删除
  - 新增 `complete` 修复策略：占位符后缀命名清理、符号链接删除
  - `doc/res` 根目录名不一致改为“提示并确认后可继续”，并统一为 Doc 侧名称作为合并输出目录名
- **GUI 线程结果能力增强**
  - 后台任务结果支持携带结构化返回值，便于执行后续自动流程（如跳转修复页）

### 测试
- 新增 `tests/test_compare_repair.py`
  - 覆盖 Compare 问题识别
  - 覆盖批量修复（mtime 对齐、覆盖修复、缺失/多余修复）

## [3.1.0] - 2026-02-11

### 改进
- **核心性能并行化优化** 🚀
  - `build_index` 引入多线程并行哈希计算，自动按 CPU 核心数分配 worker
  - `split` / `merge` 文件复制改为并行执行，提升大文件夹处理效率
  - `doc/res`、`old/new` 等双目录索引改为并行构建，缩短等待时间
  - 索引输出改为按路径排序，保证并行执行下结果稳定可复现
- **并行度可配置**
  - 新增环境变量 `KBFM_MAX_WORKERS`，支持手动限制或放大 worker 数
- **版本一致性**
  - 新增包级版本常量 `kb_folder_manager.__version__`
  - GUI 标题和测试输出改为统一读取版本常量

### 修复
- 修复索引完成日志不可达的问题（`build_index` 返回前日志丢失）

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
