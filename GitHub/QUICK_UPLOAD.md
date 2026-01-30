# ⚡ 5 分钟快速上传到 GitHub

如果你只想快速上传而不关心细节，按这个步骤来。

---

## 前提条件（3 分钟）

### 1. 安装 Git
从 https://git-scm.com/download/win 下载并安装（保持默认）

### 2. 创建 GitHub 账户
访问 https://github.com/signup 注册账户

### 3. 配置 Git 用户信息
在 PowerShell 中运行（**替换你的信息**）：

```powershell
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

---

## 上传步骤（5 分钟）

### 第 1 步：进入项目目录（30 秒）
```powershell
cd "C:\Users\14044\Desktop\PyProj\KB-Folder-Manager"
```

### 第 2 步：初始化 Git（30 秒）
```powershell
git init
git add .
git commit -m "Initial commit: KB Folder Manager"
git branch -M main
```

### 第 3 步：创建 GitHub 仓库（1 分钟）

1. 访问 https://github.com/new
2. **Repository name**: `KB-Folder-Manager`
3. **Visibility**: 选择 **Public**
4. 点击 **Create repository**

### 第 4 步：推送到 GitHub（2 分钟）

从仓库页面复制你的仓库 URL，然后运行（**替换你的用户名**）：

```powershell
git remote add origin https://github.com/yourusername/KB-Folder-Manager.git
git push -u origin main
```

输入用户名和密码（或个人访问令牌），完成！

### 第 5 步：创建发布版本（1 分钟）

1. 在 GitHub 仓库页面点击 **Releases**
2. 点击 **Create a new release**
3. **Tag version**: `v2.8`
4. **Release title**: `KB Folder Manager v2.8`
5. **Description**: 
   ```
   Initial release with core features:
   - Split, Merge, Validate, Index operations
   - Full documentation in Chinese and English
   - MIT License
   ```
6. 点击 **Publish release**

---

## ✅ 完成！

你的项目现在在 GitHub 上了：
- 📍 项目地址：`https://github.com/yourusername/KB-Folder-Manager`
- 📚 包含所有文件和文档
- 🏷️ 有发布版本 v2.8

---

## 常见问题

### Q: 忘记了仓库 URL？
A: 在 GitHub 仓库页面点击绿色的 **Code** 按钮，复制 HTTPS 链接

### Q: 推送时要求密码？
A: 用 GitHub 用户名 + 个人访问令牌（PAT）
- Settings → Developer settings → Personal access tokens → Generate new token
- 只需勾选 `repo`，复制令牌，粘贴到密码框

### Q: 需要更新项目？
```powershell
git add .
git commit -m "Update description"
git push origin main
```

### Q: 发布新版本？
```powershell
git tag -a v2.9 -m "Release 2.9"
git push origin v2.9
# 然后在 GitHub 上创建 Release
```

---

**需要更详细的指南？** 参考 [GITHUB_UPLOAD_GUIDE.md](./GITHUB_UPLOAD_GUIDE.md) 或 [UPLOAD_CHECKLIST.md](./UPLOAD_CHECKLIST.md)
