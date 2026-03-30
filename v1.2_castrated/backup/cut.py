import os
import glob
import subprocess
import argparse

def get_video_duration(input_path):
    """获取视频时长（秒）"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        return duration
    except:
        return None

def trim_video_ffmpeg(input_path, output_path, start_cut, end_cut):
    """使用ffmpeg裁剪视频"""
    try:
        # 获取视频时长
        duration = get_video_duration(input_path)
        if duration is None:
            print(f"无法获取视频时长: {input_path}")
            return False
        
        # 计算新时长
        new_duration = duration - start_cut - end_cut
        if new_duration <= 0:
            print(f"警告：视频 {input_path} 时长过短，跳过裁剪")
            return False
        
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg', '-y',  # -y: 覆盖输出文件
            '-i', input_path,
            '-ss', str(start_cut),  # 开始时间
            '-t', str(new_duration),  # 持续时间
            '-c:v', 'copy',  # 复制视频流（无需重新编码）
            '-c:a', 'copy',  # 复制音频流
            '-avoid_negative_ts', 'make_zero',  # 处理时间戳
            output_path
        ]
        
        print(f"正在处理: {os.path.basename(input_path)}")
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"  成功: {duration:.2f}秒 -> {new_duration:.2f}秒")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg处理失败: {str(e)}")
        return False
    except Exception as e:
        print(f"处理 {input_path} 时出错: {str(e)}")
        return False

def process_all_videos_ffmpeg(start_cut=5, end_cut=5, output_dir="trimmed_videos"):
    """处理所有视频（ffmpeg版本）"""
    # 支持的视频格式
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv', '*.webm']
    
    # 获取所有视频文件
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(ext))
    
    if not video_files:
        print("当前目录下未找到视频文件！")
        return
    
    print(f"找到 {len(video_files)} 个视频文件")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理每个视频
    success_count = 0
    for video_file in video_files:
        filename, ext = os.path.splitext(os.path.basename(video_file))
        output_filename = f"{filename}_trimmed{ext}"
        output_path = os.path.join(output_dir, output_filename)
        
        if trim_video_ffmpeg(video_file, output_path, start_cut, end_cut):
            success_count += 1
    
    print(f"\n处理完成！成功: {success_count}/{len(video_files)}")

if __name__ == "__main__":
    process_all_videos_ffmpeg(50, 46)