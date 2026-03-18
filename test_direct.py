import subprocess
import os

# 直接使用完整路径执行，不通过 shell
cmd = [
    r"F:\Miniconda39\envs\python31212\python.exe",
    r"d:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id\page_id.py"
]

work_dir = r"d:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id"

print(f"Executing: {' '.join(cmd)}")
print(f"Work dir: {work_dir}")
print()

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    cwd=work_dir
)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"Stderr: {result.stderr[:500] if result.stderr else 'empty'}")
