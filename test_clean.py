import subprocess
import os

# 清理环境变量
clean_env = {}
for key in ['PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE', 'COMPUTERNAME', 'USERNAME']:
    if key in os.environ:
        clean_env[key] = os.environ[key]

cmd = r'F:\Miniconda39\envs\python31212\python.exe d:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id\page_id.py'
work_dir = r'd:\SwagTslld1\BaiduSyncdisk\5-工作\公司\20260214-测试主页id'

print(f"Executing: {cmd}")
print(f"Work dir: {work_dir}")
print(f"PATH: {clean_env.get('PATH', 'Not set')[:100]}...")
print()

result = subprocess.run(
    cmd,
    shell=True,
    capture_output=True,
    text=True,
    cwd=work_dir,
    env=clean_env
)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"Stderr: {result.stderr[:500] if result.stderr else 'empty'}")
