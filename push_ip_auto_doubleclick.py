import subprocess
import os
import sys
import hashlib
from datetime import datetime

file_to_push = "ip.txt"
log_file = "push_log.txt"

def get_git_root():
    """获取当前目录或父目录的 Git 根目录"""
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if result.returncode != 0:
            print("❌ 当前目录不是 Git 仓库！")
            sys.exit(1)
        return result.stdout.strip()
    except Exception as e:
        print("❌ 获取 Git 根目录失败:", e)
        sys.exit(1)

def get_current_branch():
    """获取当前 Git 分支"""
    try:
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        return result.stdout.strip()
    except Exception as e:
        print("❌ 获取 Git 分支失败:", e)
        return "main"

def file_hash(filepath):
    """计算文件哈希，用于判断内容是否变化"""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def log(message):
    """写日志"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {message}\n")
    print(message)

def push_ip_file():
    # 自动获取脚本目录
    repo_path = os.path.abspath(os.path.dirname(__file__))
    branch = get_current_branch()
    os.chdir(repo_path)

    if not os.path.exists(file_to_push):
        log(f"❌ {file_to_push} 文件不存在！")
        return

    # 检查内容变化
    current_hash = file_hash(file_to_push)
    last_hash = None
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                if file_to_push in line and "hash=" in line:
                    last_hash = line.split("hash=")[-1].strip()
                    break
    if current_hash == last_hash:
        log(f"ℹ {file_to_push} 内容未变化，无需提交")
        return

    # 添加文件
    subprocess.run(["git", "add", file_to_push], check=True, encoding="utf-8")

    # 提交
    subprocess.run(["git", "commit", "-m", f"Update {file_to_push}"], check=True, encoding="utf-8")

    # 推送
    result = subprocess.run(["git", "push", "origin", branch],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            encoding="utf-8")
    if result.returncode != 0:
        log(f"❌ 推送 {file_to_push} 失败！")
        log(result.stderr)
    else:
        log(f"✅ {file_to_push} 已成功推送到 GitHub！ hash={current_hash}")

if __name__ == "__main__":
    push_ip_file()