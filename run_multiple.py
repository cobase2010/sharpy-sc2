import subprocess


for n in range(1,100):
    subprocess.call("python run_custom.py".split(" "))
    # subprocess.call("tasklist.exe |grep SC2 |awk '{print $2}' |xargs taskkill.exe /f /pid ")
