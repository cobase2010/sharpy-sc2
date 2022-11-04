import os
import sys
import subprocess


# os.environ["SC2_WSL_DETECT"] = "0"
sys.path.insert(1, "python-sc2")

from bot_loader import GameStarter, BotDefinitions
from version import update_version_txt
from match_manager import MatchManager
from sc2.data import Result


def main():
    update_version_txt()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ladder_bots_path = os.path.join("Bots")
    ladder_bots_path = os.path.join(root_dir, ladder_bots_path)
    definitions: BotDefinitions = BotDefinitions(ladder_bots_path)
    player_list = list(definitions.random_bots.keys())
    match_mgr = MatchManager(player_list)
    print(player_list)
    print("Restoring history...")
    match_mgr.restore_history()
    print("Current standings:")
    match_mgr.print_standings()
    # pairings = match_mgr.determine_pairings()
    rounds = 10
    starting_round = 3
    match_num = 1
    pairings = match_mgr.get_programme(rounds, player_list)
    print(f"Starting round {starting_round}")
    # print(pairings)
    for i in range(starting_round, rounds):
        match_num = i * len(pairings[i]) + 1
        print(f"Starting tournament of {len(pairings[i])} numbers of games...")
        print(f"Round {i} pairings")
        print(pairings[i])
        for m in pairings[i]:
            sys.argv = [sys.argv[0], f"--player1", f"{m[0]}", f"--player2", f"{m[1]}"]
            starter = GameStarter(definitions)
            result = starter.play()
            print("result is valid: ", isinstance(result, list))
            if  isinstance(result, list):
                player1_score = 1.0 if result[0].name == "Victory" else 0.0 if result[0].name == "Defeat" else 0.5
                player2_score = 1.0 - player1_score
            else:
                # game crashes, no score
                player1_score = 0.0
                player2_score = 0.0
            
            print(f"===Match {match_num}: {m[0]} vs {m[1]}", result)
            match_mgr.add_result(match_num, player_one=m[0], player_two=m[1], 
                player_one_score = player1_score, player_two_score = player2_score)
            print(f"Round: {i} Current standings after match {match_num}:")
            match_mgr.print_standings()
            print(match_mgr.match_history)
            match_num += 1
    
    # subprocess.call("tasklist.exe |grep SC2 |awk '{print $2}' |xargs taskkill.exe /f /pid ")

if __name__ == "__main__":
    main()
