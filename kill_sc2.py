import subprocess
import sys
import os
import time

# os.system('bash')

print(sys.argv)
watch_file = sys.argv[1] 
print(f"Watching {watch_file}...")
while not os.path.exists("./"+watch_file):
    time.sleep(10)

time.sleep(10)
# subprocess.run("/mnt/c/Windows/system32/tasklist.exe |grep SC2 |awk '{print $2}' |xargs /mnt/c/Windows/system32/taskkill.exe /f /pid ")

subprocess.run("./kill_it.sh")
print("SC2 process killed.")