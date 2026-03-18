import subprocess
import os

# 直接测试 Python 环境
python_exe = "F:/Miniconda39/envs/python31212/python.exe"

print(f"Python exists: {os.path.exists(python_exe)}")
print()

# 测试直接导入 pandas
result = subprocess.run(
    f'"{python_exe}" -c "import pandas; print(pandas.__version__)"',
    shell=True,
    capture_output=True,
    text=True
)

print(f"Testing pandas import:")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")
print()

# 测试运行脚本
script_path = "d:/SwagTslld1/BaiduSyncdisk/5-工作/公司/20260214-测试主页id/page_id.py"
print(f"Script exists: {os.path.exists(script_path)}")

result = subprocess.run(
    f'"{python_exe}" "{script_path}"',
    shell=True,
    capture_output=True,
    text=True
)

print(f"Testing script:")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"Stderr: {result.stderr[:500] if result.stderr else 'empty'}")
