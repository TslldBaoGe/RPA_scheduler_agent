import subprocess
import os

# 使用引号包裹路径
cmd = '"F:/Miniconda39/envs/python31212/python.exe" "d:/SwagTslld1/BaiduSyncdisk/5-工作/公司/20260214-测试主页id/page_id.py"'
work_dir = r'd:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id'

print(f"Current working directory: {os.getcwd()}")
print(f"Executing: {cmd}")
print(f"Work directory: {work_dir}")
print()

result = subprocess.run(
    cmd,
    shell=True,
    capture_output=True,
    text=True,
    cwd=work_dir
)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"Stderr: {result.stderr[:500] if result.stderr else 'empty'}")
