# GitHub 上传指南

本文档详细说明如何将 KB Folder Manager 项目上传到 GitHub。

## 目录
1. [准备工作](#准备工作)
2. [本地初始化 Git](#本地初始化-git)
3. [创建 GitHub 仓库](#创建-github-仓库)
4. [推送代码](#推送代码)
5. [完成发布](#完成发布)

---

## 准备工作

### 1. 检查项目状态

确保你的项目目录结构完整：
```
KB-Folder-Manager/
├── kb_folder_manager/        ✓ 已有
├── tests/                     ✓ 已有
├── kb_folder_manager.py       ✓ 已有
├── requirements.txt           ✓ 已有
├── config.yaml                ✓ 已有
├── README.md                  ✓ 已创建
├── .gitignore                 ✓ 已创建
├── LICENSE                    ✓ 已创建
├── CHANGELOG.md               ✓ 已创建
└── 用户手册.md                ✓ 已有
```

### 2. 安装 Git

- 访问 https://git-scm.com/download/win 下载 Git
- 安装时保持默认配置即可
- 验证安装：打开 PowerShell，运行 `git --version`

### 3. 配置 Git 用户信息

在 PowerShell 中运行：

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

> **提示：** 将 "Your Name" 和 "your.email@example.com" 替换为你的实际信息

### 4. 创建 GitHub 账户

如果还没有 GitHub 账户，请：
1. 访问 https://github.com/signup
2. 按提示注册账户
3. 验证邮箱

---

## 本地初始化 Git

### 1. 进入项目目录

在 PowerShell 中运行：

```powershell
cd "C:\Users\14044\Desktop\PyProj\KB-Folder-Manager"
```

### 2. 初始化 Git 仓库

```powershell
git init
```

输出应显示：
```
Initialized empty Git repository in C:\Users\14044\Desktop\PyProj\KB-Folder-Manager\.git/
```

### 3. 添加所有文件到暂存区

```powershell
git add .
```

验证操作：
```powershell
git status
```

输出应显示所有文件都是绿色的 "new file:"

### 4. 创建首次提交

```powershell
git commit -m "Initial commit: KB Folder Manager project setup

- 核心功能：Split、Merge、Validate、Index
- 支持 YAML 配置文件
- 包含详细文档和用户手册
- 添加 README、LICENSE、CHANGELOG 等文档"
```

验证提交：
```powershell
git log
```

应显示你刚创建的提交信息

---

## 创建 GitHub 仓库

### 1. 登录 GitHub

访问 https://github.com 并登录你的账户

### 2. 创建新仓库

点击右上角头像旁的 **+** 号，选择 **New repository**

### 3. 填写仓库信息

| 字段 | 填写内容 | 说明 |
|------|--------|------|
| **Repository name** | KB-Folder-Manager | 仓库名称，不要有中文 |
| **Description** | A Windows/Python tool for personal knowledge base organization | 简短描述 |
| **Visibility** | Public | 公开仓库，方便分享 |
| **Initialize this repository with:** | ✓ 保持全部未勾选 | 因为本地已有文件 |

### 4. 点击 "Create repository"

完成后 GitHub 会显示一个空仓库的操作指导页面

### 5. 复制仓库地址

页面会显示一个形如 `https://github.com/yourusername/KB-Folder-Manager.git` 的地址

记下这个地址，接下来需要用到

---

## 推送代码

### 1. 添加远程仓库

在 PowerShell 中运行（**替换下面的地址**）：

```powershell
git remote add origin https://github.com/yourusername/KB-Folder-Manager.git
```

> **重要：** 将 `yourusername` 替换为你的 GitHub 用户名

验证添加成功：
```powershell
git remote -v
```

应显示：
```
origin  https://github.com/yourusername/KB-Folder-Manager.git (fetch)
origin  https://github.com/yourusername/KB-Folder-Manager.git (push)
```

### 2. 推送代码到 GitHub

```powershell
git branch -M main
git push -u origin main
```

**首次推送时可能需要验证身份：**

- **如果弹出浏览器登录页面**：按提示完成 GitHub 登录即可
- **如果要求输入用户名/密码**：输入你的 GitHub 用户名，密码处输入个人访问令牌 (PAT)

#### 获取个人访问令牌（PAT）

如果密码方式不可用：

1. 登录 GitHub，进入 Settings → Developer settings → Personal access tokens
2. 点击 "Generate new token"，选择 "Generate new token (classic)"
3. 设置 Token name：`KB-Folder-Manager`
4. 勾选 `repo` 权限
5. 点击 "Generate token"，复制显示的令牌
6. 粘贴到密码输入框中

### 3. 验证上传成功

推送完成后，应显示：
```
Enumerating objects: XX, done.
Compressing objects: 100% (XX/XX), done.
Writing objects: 100% (XX/XX), 9.XX KiB | 1.XX MiB/s, done.
...
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

刷新 GitHub 仓库页面，应该看到所有文件都已上传

---

## 完成发布

### 1. 创建发布版本（Release）

在 GitHub 仓库页面：

1. 点击右侧 "Releases"
2. 点击 "Create a new release"
3. 填写以下信息：

| 字段 | 填写内容 |
|------|--------|
| **Tag version** | v2.8 |
| **Release title** | KB Folder Manager v2.8 |
| **Describe this release** | 详见下方示例 |

**发布描述示例：**

```markdown
# KB Folder Manager v2.8

## ✨ 新增功能
- 完善的索引生成功能，支持多种哈希算法
- 详细的校验日志和诊断信息
- 支持 7-Zip 压缩功能（可选）

## 🔧 改进
- 优化文件校验逻辑，提高检查精度
- 改进用户交互体验，新增友好的确认提示
- 完善错误提示和异常处理

## 🐛 修复
- 修复某些特殊字符文件名的处理问题
- 修复占位符识别的边界情况

## 📥 安装

```bash
git clone https://github.com/yourusername/KB-Folder-Manager.git
cd KB-Folder-Manager
pip install -r requirements.txt
python kb_folder_manager.py --help
```

## 📚 文档
- [README](./README.md) - 项目简介和快速开始
- [用户手册](./用户手册.md) - 详细的功能说明
- [项目设计文档](./KB-Folder-Manager项目文档/) - 技术细节
```

4. 点击 "Publish release"

### 2. 设置仓库话题（Topics）

在仓库 Settings 页面下滑到 "About" 部分，点击齿轮图标：

添加以下话题（可选）：
- `knowledge-management`
- `file-management`
- `python`
- `windows`
- `utility`
- `folder-organization`

### 3. 优化仓库信息

在仓库首页点击齿轮图标进入设置：

- **Description**: `A Windows/Python tool for personal knowledge base organization with Split, Merge, Validate and Index features`
- **Website**: 可留空或填写个人网站
- **Topics**: 见上方
- **Visibility**: Public（公开）

### 4. 激活 Discussions（可选）

在仓库 Settings → Features 页面，勾选 "Discussions" 以启用讨论功能

---

## 后续维护

### 更新代码到 GitHub

当本地代码有更新时：

```powershell
cd "C:\Users\14044\Desktop\PyProj\KB-Folder-Manager"
git add .
git commit -m "Your commit message here"
git push origin main
```

### 发布新版本

修改版本号后：

1. 更新 `CHANGELOG.md`
2. 提交更改：`git commit -m "Release v2.9"`
3. 创建新标签：`git tag -a v2.9 -m "Release version 2.9"`
4. 推送标签：`git push origin v2.9`
5. 在 GitHub 上创建 Release

---

## 常见问题

### Q: 上传时出现 "fatal: remote origin already exists"
A: 运行 `git remote remove origin`，然后重新运行 `git remote add origin ...`

### Q: 忘记了什么文件？
A: 修改本地文件后运行 `git add .` 和 `git commit` 更新，然后 `git push origin main`

### Q: 想修改仓库名称？
A: 在 GitHub 仓库 Settings 的 "Repository name" 修改即可

### Q: 如何删除已推送的文件？
A: 运行 `git rm --cached <filename>`，然后 `git commit` 和 `push`

---

## 检查清单

在推送前确保完成：

- [x] 安装了 Git
- [x] 配置了 Git 用户信息
- [x] 创建了 GitHub 账户
- [x] 本地初始化了 Git (`git init`)
- [x] 本地提交了代码 (`git commit`)
- [x] 在 GitHub 创建了仓库
- [x] 添加了远程仓库 (`git remote add`)
- [x] 推送了代码 (`git push`)
- [ ] 在 GitHub 上验证文件都已上传
- [ ] 创建了 Release 版本
- [ ] 设置了仓库 Topics

---

**完成以上步骤后，你的项目就成功上传到 GitHub 了！🎉**

有任何问题，欢迎在 GitHub Issues 中提出。
