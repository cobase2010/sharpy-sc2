import subprocess
import time


for n in range(1,100):
    subprocess.run("python run_custom.py -p1 4gate".split(" "))
    time.sleep(120)
    # subprocess.call("tasklist.exe |grep SC2 |awk '{print $2}' |xargs taskkill.exe /f /pid ")
