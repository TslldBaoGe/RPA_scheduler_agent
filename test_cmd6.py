import subprocess
import os

# 检查两个 Python 环境
pythons = [
    r"F:\Miniconda39\envs\python31212\python.exe",
    r"F:\Miniconda39\envs\python31212\Scripts\python.exe",  # 可能存在
]

for py in pythons:
    if os.path.exists(py):
        print(f"\n=== Testing: {py} ===")
        
        # 检查 sys.path 和 site-packages
        result = subprocess.run(
            [py, "-c", "import sys; import site; print('Executable:', sys.executable); print('Site:', site.getsitepackages()); print('Path:', sys.path)"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Stderr:", result.stderr[:200])
    else:
        print(f"\n=== Not found: {py} ===")
