# GUI 进度反馈改进 - 手动测试指南

## 测试目标
验证 GUI 在处理大文件夹时的实时进度反馈功能

## 测试准备

### 1. 创建测试数据
运行以下命令创建测试数据：
```powershell
python tests\create_test_data_for_gui.py
```

这将创建一个包含 11 个文件的测试文件夹。

### 2. 启动 GUI
```powershell
python kb_folder_manager_gui.py
```

## 测试步骤

### 测试 1：Split 操作的进度反馈

1. **打开 Split 标签页**
2. **填写输入**：
   - Source: 选择创建的测试数据文件夹
   - Output Root: 选择一个输出目录
   - 勾选 Auto-confirm

3. **点击 "Execute Split Operation"**

4. **观察以下内容**：
   ✅ 进度条应该平滑增长（不是突然跳跃）
   ✅ 状态标签显示类似："Processing [10/30]: folder/file.txt"
   ✅ 日志输出每处理 10 个文件更新一次
   ✅ 可以看到操作阶段：
      - "Operation started..."
      - "Building index..."
      - "Processing [X/Y]: ..."
      - "Validating..."
      - "Writing indexes..."
   ✅ 界面保持响应，不会卡死

### 测试 2：Merge 操作的进度反馈

1. **打开 Merge 标签页**
2. **填写输入**：
   - Doc Folder: 选择上一步生成的 doc 文件夹
   - Res Folder: 选择上一步生成的 res 文件夹
   - Output Root: 选择新的输出目录
   - 勾选 Auto-confirm

3. **点击 "Execute Merge Operation"**

4. **观察进度反馈**：
   ✅ 进度条平滑更新
   ✅ 状态标签显示当前处理的文件
   ✅ 日志频繁更新（每 10 个文件）
   ✅ 显示 "merge copy progress (doc)" 和 "merge copy progress (res)"

### 测试 3：大文件夹测试（可选）

如果想测试更大的文件夹：

1. **创建包含更多文件的测试数据**：
```python
# 修改 create_test_data_for_gui.py 中的文件数量
# 或手动创建一个包含 100+ 文件的文件夹
```

2. **执行 Split 操作**

3. **验证**：
   ✅ 即使有 100+ 文件，也能看到频繁的进度更新
   ✅ GUI 不会看起来像卡死
   ✅ 可以随时看到当前正在处理什么文件

## 改进前后对比

### 改进前（v3.0 原版本）
- ❌ 每 200 个文件才有一次输出
- ❌ 小文件夹看不到任何进度
- ❌ 大文件夹 GUI 像卡死了
- ❌ 不知道当前在处理什么
- ❌ 没有操作阶段提示

### 改进后（当前版本）
- ✅ 每 10 个文件更新一次（提升 20 倍）
- ✅ 即使小文件夹也能看到进度
- ✅ GUI 持续有反馈，不会看起来卡死
- ✅ 实时显示当前处理的文件名
- ✅ 显示操作所在阶段（索引/拷贝/验证）
- ✅ 进度条和状态标签同步更新

## 预期结果

所有测试应该显示：
1. ✅ 频繁的进度更新（不是长时间无反应）
2. ✅ 当前文件名显示
3. ✅ 操作阶段提示
4. ✅ 进度条平滑增长
5. ✅ 日志实时输出

## 如果发现问题

如果进度反馈仍然不够频繁，可以在以下文件中调整：

**kb_folder_manager/indexer.py（第 18 行）**：
```python
progress_every = 10  # 改小这个数字，如 5 或 1
```

**kb_folder_manager/operations.py（第 100, 179, 189 行）**：
```python
if idx % 10 == 0 or idx == total_files:  # 改小这个数字
```

## 技术细节

### 改进的组件

1. **LogCapture 类**（gui.py）
   - 添加了 `status_callback` 参数
   - 改进了进度解析逻辑
   - 提取并显示当前处理的文件名
   - 识别操作阶段并更新状态

2. **OperationThread 类**（gui.py）
   - 添加了 `log_capture` 参数
   - 自动重定向 stdout/stderr

3. **后端操作函数**（operations.py, indexer.py）
   - 将进度报告间隔从 200 减少到 10
   - 在日志中包含当前文件名

4. **所有执行方法**（gui.py）
   - `execute_split()`
   - `execute_merge()`
   - `execute_validate()`
   - `execute_index()`
   - 都添加了 LogCapture 实例

---

**测试日期**: 2026-01-30  
**版本**: v3.0 (进度反馈改进版)
