# KB Folder Manager - GUI 用户指南

## 简介

KB Folder Manager v3.0 现在提供了图形用户界面(GUI)，让操作更加直观和便捷。

## 启动 GUI

### 方法 1: 使用启动脚本（推荐）
```powershell
# 在项目根目录下运行
cd KB-Folder-Manager
python kb_folder_manager_gui.py
```

### 方法 2: 通过 Python 模块
如果已将项目添加到 PYTHONPATH：
```powershell
python -m kb_folder_manager.gui
```

如果未设置 PYTHONPATH，需要先设置：
```powershell
# Windows PowerShell（临时）
$env:PYTHONPATH = "$PWD"
python -m kb_folder_manager.gui

# Linux/Mac（临时）
export PYTHONPATH=$(pwd)
python -m kb_folder_manager.gui
```

**建议**：对于日常使用，推荐使用方法 1（启动脚本），更简单直接。

## 界面概览

GUI 采用标签页设计，包含以下功能模块：

### 1. Split（拆分）标签页

将 Complete 目录拆分为 Doc 和 Res 两个目录。

**输入字段：**
- **Source (Complete Folder)**: 选择要拆分的源文件夹
- **Output Root**: 选择输出根目录

**选项：**
- **Force**: 允许在输出目录非空时继续执行（谨慎使用）
- **Auto-confirm**: 跳过确认提示，直接执行

**操作步骤：**
1. 点击 "Browse..." 按钮选择源文件夹
2. 点击 "Browse..." 按钮选择输出根目录
3. 根据需要勾选选项
4. 点击 "Execute Split Operation" 按钮
5. 等待操作完成，查看日志输出

### 2. Merge（合并）标签页

将 Doc 和 Res 目录合并回 Complete 目录。

**输入字段：**
- **Doc Folder**: Doc 文件夹路径
- **Res Folder**: Res 文件夹路径
- **Output Root**: 输出根目录

**选项：**
- **Force**: 允许在输出目录非空时继续执行
- **Auto-confirm**: 跳过确认提示

**操作步骤：**
1. 分别选择 Doc 和 Res 文件夹
2. 选择输出根目录
3. 点击 "Execute Merge Operation" 按钮
4. 查看合并结果

**注意：** Doc 和 Res 文件夹的名称必须完全一致！

### 3. Validate（校验）标签页

验证文件夹结构是否符合规范。

**验证模式：**
- **Class1**: 基础环境检查（路径合法性、符号链接、大小写冲突等）
- **Class2**: 类型纯净度检查（Doc 中只有文档类型，Res 中只有资源类型）
- **Mutual**: Doc/Res 相互一致性检查
- **Compare**: 新旧文件夹对比（哈希值和大小）

**操作步骤：**
1. 选择验证模式
2. 根据模式填写相应的输入字段
3. 选择日志输出目录
4. 点击 "Execute Validation" 按钮
5. 在日志输出区域查看验证结果

### 4. Index（索引）标签页

为指定文件夹生成索引文件。

**输入字段：**
- **Target Folder**: 要生成索引的目标文件夹
- **Output Index File**: 索引文件保存路径（.json 格式）
- **Log Directory**: 日志输出目录

**操作步骤：**
1. 选择目标文件夹
2. 指定索引文件保存位置
3. 选择日志目录
4. 点击 "Generate Index" 按钮

### 5. Settings（设置）标签页

查看和管理配置文件。

**功能：**
- **配置信息显示**: 查看当前配置（文件类型、占位符后缀、哈希算法等）
- **Reload Configuration**: 重新加载配置文件
- **Open Config File**: 在编辑器中打开配置文件进行修改

## 进度和日志

### 进度条
界面底部的进度条显示当前操作的进度，包括：
- 进度百分比
- 已处理/总数
- 当前状态

### 日志输出
日志输出区域实时显示操作详情，包括：
- `[INFO]` 信息日志
- `[WARNING]` 警告信息
- `[ERROR]` 错误信息
- `[FATAL]` 致命错误
- `[SUCCESS]` 成功消息

## 常见使用场景

### 场景 1: 首次拆分知识库
1. 切换到 "Split" 标签页
2. 选择 Complete 文件夹作为 Source
3. 选择输出目录
4. 取消勾选 "Force"（确保输出目录为空）
5. 勾选 "Auto-confirm" 以跳过确认
6. 点击执行按钮
7. 等待完成，检查日志确认无错误

### 场景 2: 合并修改后的文件
1. 编辑 Doc 或 Res 文件夹中的文件
2. 切换到 "Merge" 标签页
3. 分别选择 Doc 和 Res 文件夹
4. 选择输出目录
5. 点击执行按钮
6. 合并完成后在 complete 子目录中查看结果

### 场景 3: 验证文件夹合规性
1. 切换到 "Validate" 标签页
2. 选择验证模式（通常先用 Class1 进行基础检查）
3. 选择要验证的文件夹
4. 指定日志目录
5. 点击执行按钮
6. 查看日志输出，确认无 FATAL 或 ERROR

## 提示和技巧

### 1. 批处理操作
- 勾选 "Auto-confirm" 可以跳过确认提示，适合自动化场景
- 使用 "Force" 选项时要格外小心，确保不会覆盖重要数据

### 2. 错误排查
- 如果操作失败，仔细查看日志输出区域的错误信息
- FATAL 错误会阻止操作继续，必须先解决
- WARNING 通常不会阻止操作，但建议关注

### 3. 日志保存
- 所有操作都会在输出目录的 `logs/` 子目录中保存详细日志
- 日志文件按时间戳命名，便于追踪

### 4. 配置修改
- 如需修改文件类型列表或其他配置，使用 Settings 标签页
- 修改配置后，点击 "Reload Configuration" 使其生效
- 无需重启 GUI

### 5. 性能优化
- 大量文件时，操作可能需要较长时间
- 进度条和日志会实时更新，无需担心程序卡死
- 不要在操作进行中关闭 GUI 窗口

## 故障排除

### 问题 1: GUI 无法启动
**错误信息**: `AttributeError: module 'ttkbootstrap' has no attribute 'ScrolledText'`

**原因**: 旧版本代码的导入错误（已在 v3.0 中修复）

**解决方案:**
```powershell
# 1. 确保使用最新版本
git pull  # 如果从 git 安装

# 2. 重新安装依赖
pip install -r requirements.txt --upgrade
```

### 问题 2: ModuleNotFoundError
**错误信息**: `No module named 'ttkbootstrap'` 或 `No module named 'PIL'`

**解决方案:**
```powershell
pip install ttkbootstrap pillow
```

### 问题 3: "Another operation is already running"
**原因:** 上一个操作尚未完成
**解决方案:** 等待当前操作完成，或重启 GUI

### 问题 4: 文件夹选择后无法执行
**检查项:**
- 确保所有必填字段都已填写
- 检查路径是否存在
- 查看日志输出是否有配置加载错误

### 问题 5: 操作执行但无进度
**可能原因:**
- 文件数量少，操作瞬间完成
- 检查日志输出确认操作状态

## 测试 GUI 功能

### 使用测试数据
如果想快速测试 GUI 的所有功能，可以使用提供的测试脚本：

```powershell
# 1. 创建测试数据
python tests\create_test_data_for_gui.py

# 2. 启动 GUI
python kb_folder_manager_gui.py

# 3. 按照屏幕上的说明测试各项功能
```

测试数据会创建在临时目录，包含：
- 11 个不同类型的测试文件
- 3 层嵌套目录结构
- 多种文件格式（.pdf, .md, .txt, .jpg, .bin, .docx, .pptx, .mp4, .py, .zip）

测试完成后，可以删除测试数据目录。

## GUI vs 命令行

### GUI 优势
- 可视化操作，更直观
- 无需记忆命令参数
- 实时进度显示
- 友好的错误提示

### 命令行优势
- 支持脚本自动化
- 可在远程服务器使用
- 更适合批量处理

### 何时使用 GUI
- 首次使用，熟悉功能
- 临时性、一次性操作
- 需要可视化确认结果
- 不熟悉命令行操作

### 何时使用命令行
- 自动化脚本
- 远程服务器操作
- 需要集成到其他工具
- 批量重复操作

## 快捷键

GUI 目前不支持自定义快捷键，但可以使用以下系统快捷键：
- `Tab`: 在字段间切换
- `Ctrl+C`: 复制日志内容
- `Alt+F4`: 关闭窗口

## 更多帮助

如遇到问题，请：
1. 查看日志输出获取详细错误信息
2. 检查 `logs/` 目录中的日志文件
3. 参考用户手册的命令行部分理解操作逻辑
4. 提交 GitHub Issue 报告问题

---

**KB Folder Manager v3.0** - 让知识库管理更轻松！
