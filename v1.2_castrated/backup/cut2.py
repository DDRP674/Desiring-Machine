import subprocess
import os

def split_video(input_path, n_segments, output_dir="output"):
    """
    将视频粗略切割成n段
    
    Args:
        input_path: 输入视频路径
        n_segments: 分割段数
        output_dir: 输出目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取视频总时长
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_path
    ]
    
    try:
        duration = float(subprocess.check_output(cmd).decode().strip())
    except Exception as e:
        print(f"获取视频时长失败: {e}")
        return
    
    segment_duration = duration / n_segments
    
    # 基础输出文件名
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # 切割视频
    for i in range(n_segments):
        start_time = i * segment_duration
        output_path = os.path.join(output_dir, f"{base_name}_part_{i+1:03d}.mp4")
        
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-ss', str(start_time),
            '-i', input_path,
            '-t', str(segment_duration),
            '-c', 'copy',  # 直接复制流，速度极快
            output_path
        ]
        
        try:
            print(f"正在生成第 {i+1}/{n_segments} 段: {output_path}")
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"分割第 {i+1} 段失败: {e}")
    
    print(f"分割完成！文件保存在: {output_dir}")

if __name__ == "__main__":
    # 使用示例
    input_video = "./assets/SNOW/1.mp4"  # 你的视频文件路径
    num_segments = 10  # 想分割成几段
    
    split_video(input_video, num_segments)