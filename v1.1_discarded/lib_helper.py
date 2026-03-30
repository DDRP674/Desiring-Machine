import atexit
import json
import logging
import re
import subprocess
import os
import platform
import sys
from typing import Optional, List, Union

def func_name(): return sys._getframe(1).f_code.co_name

def get_filename(dir):
    """获取一个路径下的所有文件名，单层的"""
    files = []
    with os.scandir(dir) as entries:
        for entry in entries:
            if entry.is_file():
                files.append(entry.name)
    return files

def regulate_text(text):
    # 去除方括号及其内容
    text = re.sub(r'\[.*?\]', '', text)
    # 去除星号及其内容
    text = re.sub(r'\*.*?\*', '', text)
    # 去除圆括号及其内容
    text = re.sub(r'\(.*?\)', '', text)
    # 去除剩余的单独括号、星号、减号
    text = re.sub(r'[\[\]*()-]', '', text)
    return text

def load_json_with_comments(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    zhanweifu1 = "#占位符1#"
    zhanweifu2 = "#占位符2#"
    content = content.replace("https://", zhanweifu1)
    content = content.replace("http://", zhanweifu2)
    #print(content)
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = content.replace(zhanweifu1, "https://")
    content = content.replace(zhanweifu2, "http://")
    #print(content)
    data = json.loads(content)
    return data

def run_managed_process(
    command: Union[str, List[str]],
    timeout: float = 5.0,
    log_file: Optional[str] = None
) -> None:
    """
    启动并管理一个跨平台应用程序进程，确保在Python退出时关闭
    
    参数:
        command: 要执行的命令(字符串或列表形式)
        timeout: 等待进程退出的超时时间(秒)
        log_file: 可选日志文件路径
    
    示例:
        # Windows记事本
        run_managed_process(["notepad.exe"])
        
        # Linux文本编辑器
        run_managed_process(["gedit"])
        
        # macOS文本编辑器
        run_managed_process(["open", "-a", "TextEdit"])
    """
    # 设置日志
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('managed_process')
    
    # 平台检测
    is_windows = platform.system() == "Windows"
    process: Optional[subprocess.Popen] = None
    
    def cleanup():
        nonlocal process
        if process is None or process.poll() is not None:
            return
        
        logger.info("开始清理子进程...")
        
        try:
            if is_windows:
                # Windows使用taskkill终止整个进程树
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout
                )
                logger.info("使用taskkill终止Windows进程树")
            else:
                # Unix发送信号给整个进程组
                os.killpg(os.getpgid(process.pid))
                logger.info("发送SIGTERM给Unix进程组")
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(process.pid))
                    logger.warning("强制终止Unix进程组")
        except Exception as e:
            logger.error(f"清理过程中发生错误: {str(e)}")
            try:
                process.kill()
            except:
                pass
        finally:
            process = None
    
    try:
        # 启动进程
        kwargs = {}
        if not is_windows:
            kwargs['preexec_fn'] = os.setsid  # 为Unix创建新进程组
        
        process = subprocess.Popen(
            command if isinstance(command, list) else command.split(),
            **kwargs
        )
        logger.info(f"启动进程: {command} (PID: {process.pid})")
        
        # 注册清理函数
        atexit.register(cleanup)
        
        # 等待进程完成(如果不想等待可以移除这部分)
        process.wait()
        logger.info("子进程正常退出")
        
    except Exception as e:
        logger.error(f"进程启动失败: {str(e)}")
        cleanup()
        raise
    finally:
        atexit.unregister(cleanup)