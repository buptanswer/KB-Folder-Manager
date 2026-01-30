#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 上传辅助脚本 - 用于验证项目准备就绪
可在推送前运行此脚本检查项目状态
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath):
    """检查文件是否存在"""
    return os.path.isfile(filepath)

def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_check(condition, text):
    """打印检查项"""
    symbol = "✅" if condition else "❌"
    print(f"  {symbol}  {text}")

def main():
    """主函数"""
    project_root = Path(__file__).parent
    
    print_header("KB Folder Manager - GitHub 上传准备检查")
    
    # 检查项目文件
    print("📦 项目核心文件：")
    files_to_check = [
        ("kb_folder_manager.py", "主入口文件"),
        ("requirements.txt", "Python 依赖"),
        ("config.yaml", "配置文件"),
        ("用户手册.md", "用户手册"),
    ]
    
    project_files_ok = True
    for filename, desc in files_to_check:
        exists = check_file_exists(project_root / filename)
        print_check(exists, f"{filename} - {desc}")
        project_files_ok = project_files_ok and exists
    
    # 检查项目目录
    print("\n📁 项目目录：")
    dirs_to_check = [
        ("kb_folder_manager", "源代码包"),
        ("tests", "测试文件"),
    ]
    
    project_dirs_ok = True
    for dirname, desc in dirs_to_check:
        exists = os.path.isdir(project_root / dirname)
        print_check(exists, f"{dirname}/ - {desc}")
        project_dirs_ok = project_dirs_ok and exists
    
    # 检查 GitHub 准备文件
    print("\n📄 GitHub 文件（已为你生成）：")
    github_files = [
        ("README.md", "项目首页"),
        (".gitignore", "Git 忽略配置"),
        ("LICENSE", "MIT 许可证"),
        ("CHANGELOG.md", "版本历史"),
    ]
    
    github_files_ok = True
    for filename, desc in github_files:
        exists = check_file_exists(project_root / filename)
        print_check(exists, f"{filename} - {desc}")
        github_files_ok = github_files_ok and exists
    
    # 检查上传指南文档
    print("\n📚 上传指南文档（已为你准备）：")
    guide_files = [
        ("QUICK_UPLOAD.md", "快速 5 分钟指南 ⭐"),
        ("GITHUB_UPLOAD_GUIDE.md", "详细完整指南"),
        ("UPLOAD_CHECKLIST.md", "检查清单"),
        ("GITHUB_REPO_INFO_TEMPLATE.md", "仓库信息模板"),
        ("GIT_COMMANDS_REFERENCE.md", "Git 命令参考"),
        ("GITHUB_UPLOAD_DOCS_INDEX.md", "文档总索引"),
        ("UPLOAD_SUMMARY.md", "上传完成总结"),
    ]
    
    guide_files_ok = True
    for filename, desc in guide_files:
        exists = check_file_exists(project_root / filename)
        print_check(exists, f"{filename}\n       {desc}")
        guide_files_ok = guide_files_ok and exists
    
    # 检查 Git 状态
    print("\n🔧 Git 状态检查：")
    git_dir = project_root / ".git"
    git_exists = os.path.isdir(git_dir)
    print_check(git_exists, "Git 仓库已初始化" if git_exists else "Git 仓库未初始化（稍后需要）")
    
    # 最终结果
    print_header("📊 检查结果")
    
    all_ok = project_files_ok and project_dirs_ok and github_files_ok and guide_files_ok
    
    if all_ok:
        print("""
  ✅ 所有必需文件都已准备就绪！
  
  现在你可以：
  
  1️⃣  推荐：打开 QUICK_UPLOAD.md 快速上传（5 分钟）
  2️⃣  或：打开 GITHUB_UPLOAD_GUIDE.md 详细了解
  3️⃣  或：打开 UPLOAD_CHECKLIST.md 逐步执行
  
  💡 所有上传需要的文档都在项目目录里！
  
  下一步：
  1. 安装 Git（如未安装）
  2. 创建 GitHub 账户（如未有）
  3. 按照指南操作
  
  祝你上传顺利！🚀
        """)
    else:
        print("""
  ⚠️  某些文件缺失！
  
  请确保：
  - 所有源代码文件都在项目目录中
  - 所有指南文档都已生成
  
  如有问题，请检查文件是否正确复制到项目目录。
        """)
    
    print_header("开始上传")
    print("""
  推荐步骤：
  
  Step 1: 打开 "QUICK_UPLOAD.md"
  Step 2: 按照 5 个步骤操作
  Step 3: 完成！
  
  或者访问 "GITHUB_UPLOAD_DOCS_INDEX.md" 查看所有文档说明。
    """)

if __name__ == "__main__":
    main()
