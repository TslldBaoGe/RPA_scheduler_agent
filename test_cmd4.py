import subprocess
import os
import sys

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

# 测试使用完整路径
python_exe = r"F:\Miniconda39\envs\python31212\python.exe"
print(f"Target Python exists: {os.path.exists(python_exe)}")

# 使用 list 形式传递参数，避免 shell 解析问题
result = subprocess.run(
    [python_exe, "-c", "import pandas; print(pandas.__version__)"],
    capture_output=True,
    text=True
)

print(f"\nTesting pandas import with list args:")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")

# 测试运行脚本
script_path = r"d:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id\page_id.py"
print(f"\nScript exists: {os.path.exists(script_path)}")

result = subprocess.run(
    [python_exe, script_path],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(script_path)
)

print(f"\nTesting script with list args:")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"Stderr: {result.stderr[:500] if result.stderr else 'empty'}")
