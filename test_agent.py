import subprocess
import os

# 测试在 Agent 虚拟环境中执行
cmd_parts = [
    r"F:\Miniconda39\envs\python31212\python.exe",
    r"d:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id\page_id.py"
]

work_dir = r"d:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id"

print(f"Executing: {' '.join(cmd_parts)}")
print(f"Work dir: {work_dir}")
print(f"Current dir: {os.getcwd()}")
print()

result = subprocess.run(
    cmd_parts,
    capture_output=True,
    text=True,
    cwd=work_dir
)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"Stderr: {result.stderr[:500] if result.stderr else 'empty'}")
