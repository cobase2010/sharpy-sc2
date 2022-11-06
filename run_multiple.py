import subprocess
import time
from os import environ


for n in range(1,100):
    if 'PYTHON' in environ:
        subprocess.run("$PYTHON run_custom.py -p1 4gate".split(" "))
        
    else:
        subprocess.run("python run_custom.py -p1 4gate".split(" "))
    time.sleep(10)
