# 快速 Git 命令参考

## 首次上传的完整命令序列

复制粘贴这些命令到 PowerShell 中执行：

### 第1步：进入项目目录
```powershell
cd "C:\Users\14044\Desktop\PyProj\KB-Folder-Manager"
```

### 第2步：初始化并提交（本地操作）
```powershell
git init

git config user.name "Your Name"
git config user.email "your.email@example.com"

git add .

git commit -m "Initial commit: KB Folder Manager project setup

- Core features: Split, Merge, Validate, Index
- YAML configuration support
- Comprehensive documentation
- MIT License"

git branch -M main
```

### 第3步：添加远程仓库并推送
```powershell
git remote add origin https://github.com/yourusername/KB-Folder-Manager.git

git push -u origin main
```

> **⚠️ 重要：** 将 `yourusername` 替换为你的 GitHub 用户名！

---

## 日常操作命令

### 查看当前状态
```powershell
git status
```

### 查看提交历史
```powershell
git log --oneline -10
```

### 添加文件并提交
```powershell
# 添加单个文件
git add path/to/file.py

# 添加所有修改
git add .

# 提交
git commit -m "Your commit message here"
```

### 推送到远程
```powershell
git push origin main
```

### 从远程拉取
```powershell
git pull origin main
```

### 创建新分支
```powershell
git checkout -b feature/new-feature
```

### 切换分支
```powershell
git checkout main
```

---

## 创建版本发布（Release）

### 创建标签
```powershell
git tag -a v2.8 -m "Release version 2.8"
git push origin v2.8
```

### 查看所有标签
```powershell
git tag -l
```

---

## 撤销操作

### 撤销本地修改（未提交）
```powershell
git checkout -- path/to/file.py
```

### 撤销所有本地修改
```powershell
git reset --hard HEAD
```

### 撤销上次提交（谨慎使用）
```powershell
git reset --soft HEAD~1
```

### 查看远程仓库信息
```powershell
git remote -v
```

---

## 常用场景

### 场景1：修改后上传更新
```powershell
git add .
git commit -m "Update: [describe changes]"
git push origin main
```

### 场景2：添加新的发布版本
```powershell
# 编辑 CHANGELOG.md 和版本号
git add CHANGELOG.md
git commit -m "Release v2.9"
git tag -a v2.9 -m "Release version 2.9"
git push origin main
git push origin v2.9
```

### 场景3：协作开发
```powershell
# 创建特性分支
git checkout -b feature/new-feature

# 开发...

# 推送特性分支
git push origin feature/new-feature

# 在 GitHub 上创建 Pull Request
```

---

## 故障排除

### 问题：`fatal: remote origin already exists`
```powershell
git remote remove origin
git remote add origin https://github.com/yourusername/KB-Folder-Manager.git
```

### 问题：忘记提交消息中的内容
```powershell
git commit --amend -m "New message here"
```

### 问题：看不到文件变更
```powershell
git diff                 # 查看未暂存的修改
git diff --staged        # 查看已暂存的修改
```

### 问题：需要重新配置用户信息
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 验证配置
git config --global user.name
git config --global user.email
```

---

## 有用的别名设置

简化常用命令（可选）：

```powershell
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual 'log --graph --oneline --all'
```

设置后可以使用：
```powershell
git st          # 代替 git status
git co main     # 代替 git checkout main
```

---

## 获取帮助

查看任何命令的详细帮助：
```powershell
git [command] --help
```

例如：
```powershell
git commit --help
git push --help
git log --help
```

---

**记住：** 每次推送前先检查 `git status`，确保想要上传的文件都已添加！
