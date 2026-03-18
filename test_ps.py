import subprocess
import os
import sys

# 直接用 PowerShell 测试
cmd = '''
& "F:/Miniconda39/envs/python31212/python.exe" -c "import sys; print('Executable:', sys.executable); print('Path:', [p for p in sys.path if 'site-packages' in p])"
'''

print("Testing with PowerShell:")
result = subprocess.run(
    ["powershell", "-Command", cmd],
    capture_output=True,
    text=True
)
print(result.stdout)
print("Stderr:", result.stderr)

# 测试 pandas
cmd2 = '''
& "F:/Miniconda39/envs/python31212/python.exe" -c "import pandas; print('pandas:', pandas.__version__)"
'''

print("\nTesting pandas with PowerShell:")
result = subprocess.run(
    ["powershell", "-Command", cmd2],
    capture_output=True,
    text=True
)
print(result.stdout)
print("Stderr:", result.stderr)
