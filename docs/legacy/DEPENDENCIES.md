# KB Folder Manager - 依赖说明

## 项目依赖

### 第三方库（需要安装）

#### PyYAML >= 6.0
- **用途**: 读取和解析 config.yaml 配置文件
- **使用位置**: `kb_folder_manager/config.py`
- **安装**: `pip install PyYAML`

#### ttkbootstrap >= 1.20.0
- **用途**: 提供现代化的 tkinter 界面组件和主题
- **使用位置**: `kb_folder_manager/gui.py`
- **功能**: GUI 主框架、按钮、标签页、进度条等
- **安装**: `pip install ttkbootstrap`

#### pillow >= 10.0.0
- **用途**: ttkbootstrap 的图像支持依赖
- **使用位置**: 由 ttkbootstrap 间接使用
- **功能**: GUI 中的图标和图像渲染
- **安装**: `pip install pillow`

### 标准库（无需安装）

以下是项目使用的 Python 标准库，随 Python 安装自动提供：

#### 核心库
- `pathlib` - 路径操作
- `sys` - 系统接口
- `os` - 操作系统接口
- `time` - 时间处理
- `datetime` - 日期时间

#### 文件和数据处理
- `json` - JSON 序列化
- `hashlib` - 哈希计算（SHA256）
- `shutil` - 高级文件操作
- `tempfile` - 临时文件/目录

#### 并发和测试
- `threading` - 多线程（GUI 后台操作）
- `queue` - 线程间通信
- `unittest` - 单元测试

#### 其他
- `argparse` - 命令行参数解析
- `re` - 正则表达式
- `dataclasses` - 数据类
- `typing` - 类型注解

#### GUI 相关（Python 自带）
- `tkinter` - 基础 GUI 框架
- `tkinter.filedialog` - 文件对话框
- `tkinter.messagebox` - 消息框
- `tkinter.scrolledtext` - 滚动文本框

## 依赖安装

### 一键安装所有依赖
```bash
pip install -r requirements.txt
```

### 单独安装
```bash
pip install PyYAML>=6.0
pip install ttkbootstrap>=1.20.0
pip install pillow>=10.0.0
```

### 验证安装
```python
# 运行此脚本验证所有依赖
import sys

dependencies = {
    'yaml': 'PyYAML',
    'ttkbootstrap': 'ttkbootstrap',
    'PIL': 'pillow',
}

print("验证依赖安装...\n")
all_ok = True

for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"✓ {package} 已安装")
    except ImportError:
        print(f"✗ {package} 未安装 - 请运行: pip install {package}")
        all_ok = False

if all_ok:
    print("\n✓ 所有依赖已正确安装！")
else:
    print("\n⚠ 请安装缺失的依赖")
    sys.exit(1)
```

## 版本要求

- **Python**: >= 3.10
- **操作系统**: Windows（主要），Linux/Mac（基本支持）

## 可选依赖

### 7-Zip
- **用途**: 压缩功能（如果 config.yaml 中 `use_7zip: true`）
- **安装**: 手动下载安装 7-Zip
- **配置**: 不需要时可在 config.yaml 中设为 `false`

## 依赖说明

### 为什么选择 ttkbootstrap？

1. **轻量级**: 基于 Python 自带的 tkinter
2. **无需编译**: 纯 Python 包，跨平台
3. **现代化**: 提供漂亮的主题和组件
4. **易用性**: API 简单，学习曲线平缓

### 为什么不用 Qt/wxPython？

- **体积**: ttkbootstrap + pillow < 5MB，Qt/wxPython > 50MB
- **依赖**: 无需额外系统依赖
- **复杂度**: 对于本项目的需求，tkinter 已足够

## 常见问题

### Q: 为什么安装失败？

A: 常见原因：
1. Python 版本 < 3.10
2. 网络问题 - 尝试使用镜像源：
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```
3. 权限问题 - 使用 `--user` 标志：
   ```bash
   pip install -r requirements.txt --user
   ```

### Q: 可以用虚拟环境吗？

A: 推荐使用虚拟环境：
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### Q: tkinter 报错怎么办？

A: tkinter 通常随 Python 安装，但某些 Linux 发行版需要单独安装：
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# macOS (Homebrew Python)
brew install python-tk
```

## 依赖更新

### 更新所有依赖到最新版本
```bash
pip install -r requirements.txt --upgrade
```

### 检查过时的包
```bash
pip list --outdated
```

## 开发依赖

如果要进行开发工作，可能还需要：
```bash
# 代码格式化
pip install black

# 类型检查
pip install mypy

# 测试覆盖率
pip install pytest-cov
```

---

**更新日期**: 2026-01-30  
**项目版本**: v3.0
