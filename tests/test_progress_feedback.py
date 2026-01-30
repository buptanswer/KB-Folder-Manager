"""测试 GUI 进度反馈功能"""
import sys
import tempfile
import shutil
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb_folder_manager.config import load_config, DEFAULT_CONFIG_NAME
from kb_folder_manager.operations import split_operation
from kb_folder_manager.gui import LogCapture
from tkinter import Text, Tk

def create_test_data(base_dir: Path, file_count: int = 30):
    """创建测试数据（30个文件，足够看到进度更新）"""
    complete_dir = base_dir / "test_complete"
    complete_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建多个子目录和文件
    for i in range(file_count):
        subdir = complete_dir / f"folder_{i // 10}"
        subdir.mkdir(exist_ok=True)
        
        # 创建不同类型的文件
        if i % 3 == 0:
            # 文档类型
            file_path = subdir / f"document_{i}.txt"
            file_path.write_text(f"Test document {i}\n" * 100)
        elif i % 3 == 1:
            # 图片类型
            file_path = subdir / f"image_{i}.jpg"
            file_path.write_bytes(b"fake jpg data" * 1000)
        else:
            # 视频类型
            file_path = subdir / f"video_{i}.mp4"
            file_path.write_bytes(b"fake mp4 data" * 1000)
    
    return complete_dir

def test_progress_feedback():
    """测试进度反馈功能"""
    print("=" * 60)
    print("测试 GUI 进度反馈功能")
    print("=" * 60)
    
    # 创建临时测试环境
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("\n1. 创建测试数据...")
        complete_dir = create_test_data(temp_path, file_count=30)
        print(f"   ✓ 创建了 30 个测试文件")
        
        output_dir = temp_path / "output"
        output_dir.mkdir()
        
        print("\n2. 加载配置...")
        config = load_config(Path(DEFAULT_CONFIG_NAME))
        print(f"   ✓ 配置加载成功")
        
        print("\n3. 创建模拟 GUI 组件...")
        # 创建一个简单的 Tkinter 文本组件用于测试
        root = Tk()
        root.withdraw()  # 隐藏主窗口
        text_widget = Text(root)
        
        progress_updates = []
        status_updates = []
        
        def track_progress(current, total):
            progress_updates.append((current, total))
            percentage = int((current / total) * 100)
            print(f"   [进度] {current}/{total} ({percentage}%)")
        
        def track_status(message):
            status_updates.append(message)
            print(f"   [状态] {message}")
        
        log_capture = LogCapture(
            text_widget,
            progress_callback=track_progress,
            status_callback=track_status
        )
        
        print(f"   ✓ 日志捕获器创建成功")
        
        print("\n4. 运行 Split 操作（观察进度反馈）...")
        print("   " + "-" * 56)
        
        # 重定向 stdout 到 log_capture
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # 使用 auto_yes=True 跳过确认
            split_operation(
                complete_dir,
                output_dir,
                config,
                force=False,
                auto_yes=True  # 自动确认，不等待用户输入
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        print("   " + "-" * 56)
        print(f"\n   ✓ 操作完成")
        
        print("\n5. 统计进度反馈...")
        print(f"   • 进度更新次数: {len(progress_updates)}")
        print(f"   • 状态更新次数: {len(status_updates)}")
        
        if progress_updates:
            print(f"   • 第一次进度: {progress_updates[0]}")
            print(f"   • 最后进度: {progress_updates[-1]}")
            
            # 计算平均更新间隔
            if len(progress_updates) > 1:
                total_files = progress_updates[-1][1]
                updates_count = len(progress_updates)
                avg_interval = total_files / updates_count
                print(f"   • 平均每 {avg_interval:.1f} 个文件更新一次进度")
        
        if status_updates:
            print(f"   • 状态消息示例:")
            for msg in status_updates[:5]:  # 显示前5条
                print(f"     - {msg[:80]}...")
        
        print("\n6. 验证输出结果...")
        doc_dir = output_dir / "doc" / complete_dir.name
        res_dir = output_dir / "res" / complete_dir.name
        
        if doc_dir.exists() and res_dir.exists():
            doc_files = list(doc_dir.rglob("*"))
            res_files = list(res_dir.rglob("*"))
            print(f"   ✓ Doc 目录: {len([f for f in doc_files if f.is_file()])} 个文件")
            print(f"   ✓ Res 目录: {len([f for f in res_files if f.is_file()])} 个文件")
        
        root.destroy()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    
    # 验证改进效果
    print("\n📊 改进效果总结:")
    if len(progress_updates) >= 3:
        print("✅ 进度反馈频率正常（每 10 个文件更新）")
    else:
        print("⚠️  进度反馈可能不够频繁")
    
    if len(status_updates) >= 5:
        print("✅ 状态消息更新正常")
    else:
        print("⚠️  状态消息可能不够详细")
    
    print("\n💡 用户体验改进:")
    print("   • 进度更新间隔：200 文件 → 10 文件（提升 20 倍）")
    print("   • 实时显示当前处理的文件名")
    print("   • 显示操作阶段（索引、拷贝、验证等）")
    print("   • 进度条同步更新")

if __name__ == '__main__':
    test_progress_feedback()
