import subprocess
try:
    subprocess.call(["App.exe"])
except Exception as e:
    print(e)