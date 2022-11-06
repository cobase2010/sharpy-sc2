import os
import sys
import subprocess


# os.environ["SC2_WSL_DETECT"] = "0"
sys.path.insert(1, "python-sc2")

from bot_loader import GameStarter, BotDefinitions
from version import update_version_txt
from match_manager import MatchManager


def main():
    update_version_txt()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ladder_bots_path = os.path.join("Bots")
    ladder_bots_path = os.path.join(root_dir, ladder_bots_path)
    definitions: BotDefinitions = BotDefinitions(ladder_bots_path)
    
    starter = GameStarter(definitions)

   
    result = starter.play()

    print("===Game over:", result)
    print("player 1 result:", result[0].name)
    
    return result
    
    # subprocess.call("tasklist.exe |grep SC2 |awk '{print $2}' |xargs taskkill.exe /f /pid ")

if __name__ == "__main__":
    main()
