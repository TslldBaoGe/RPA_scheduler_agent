import subprocess
import os

python_exe = r"F:\Miniconda39\envs\python31212\python.exe"

# 检查 Python 路径
result = subprocess.run(
    [python_exe, "-c", "import sys; print(sys.executable); print(sys.path)"],
    capture_output=True,
    text=True
)

print(f"Python executable and path:")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")
print()

# 检查 site-packages
result = subprocess.run(
    [python_exe, "-c", "import site; print(site.getsitepackages())"],
    capture_output=True,
    text=True
)

print(f"Site packages:")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")
print()

# 检查 pip list
result = subprocess.run(
    [python_exe, "-m", "pip", "list"],
    capture_output=True,
    text=True
)

print(f"Pip list (first 500 chars):")
print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout[:500]}")
print(f"Stderr: {result.stderr[:200] if result.stderr else 'empty'}")
