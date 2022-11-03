import pandas as pd
from tabulate import tabulate
import numpy as np
import pickle



class MatchManager:

    def __init__(self, list_of_players):
        # Example list of players
        # self.list_of_players = ["Bulbasaur", 
        #                 "Pikachu", 
        #                 "Squirtle", 
        #                 "Charmander",
        #                 "Caterpie",
        #                 "Pidgey",
        #                 "Spearow",
        #                 "Eevee"]
        self.list_of_players = list_of_players
        

        self.standings_df = pd.DataFrame(list(zip(self.list_of_players, 
                                     [0 for i in self.list_of_players],
                                     [0 for i in self.list_of_players],
                                     [0 for i in self.list_of_players])), 
                                    columns = ["Player", "Played", "Points", "OMW"])

        # Example match history
        # self.match_history = {0: {'Player_1': 'Eevee', 'Player_2': 'Bulbasaur', 'Score': '1.0-0.0', 'Result': 'W'},
        # 1: {'Player_1': 'Pikachu', 'Player_2': 'Pidgey', 'Score': '1.0-0.0', 'Result': 'W'},
        # 2: {'Player_1': 'Charmander', 'Player_2': 'Spearow', 'Score': '2.0-1.0', 'Result': 'W'},
        # 3: {'Player_1': 'Squirtle', 'Player_2': 'Caterpie', 'Score': '1.0-0.0', 'Result': 'W'},
        # 4: {'Player_1': 'Pikachu', 'Player_2': 'Squirtle', 'Score': '1.0-0.0', 'Result': 'W'},
        # 5: {'Player_1': 'Charmander', 'Player_2': 'Eevee', 'Score': '1.0-1.0', 'Result': 'D'},
        # 6: {'Player_1': 'Spearow', 'Player_2': 'Pidgey', 'Score': '1.0-1.0', 'Result': 'D'},
        # 7: {'Player_1': 'Bulbasaur', 'Player_2': 'Caterpie', 'Score': '1.0-0.0', 'Result': 'W'}}
        self.match_history = {}


    def add_result(self, match_num, player_one, player_two, player_one_score, player_two_score):
        """
        Prompts user for result and records it in the given dictionary
        
        Arguments:
        
            match_num - int
            player_one - string
            player_two - string
            player_one_score - float
            player_two_score - float
        
        match_history - the dictionary where we want to store this data.
        
        Does not return anything, merely updates the match_history dictionary with the
        results
        """
        
        # Note that the "Result" is from the perspective of Player_1 - it should either be
        # W or D
        
        # If player one won
        # Note that we use this really weird way of calculating to avoid floating point errors. 
        if player_one_score - player_two_score > 0.0001:
            self.match_history[match_num] = {
                'Player_1': player_one,
                'Player_2': player_two,
                'Score': str(player_one_score) + "-" + str(player_two_score),
                'Result': "W"
            }
            
        # If player two won
        # Note that because we want our match_history dictionary to have the winning player in the 
        # "Player_1" slot, we swap the order of player_two and player_one below.
        elif player_two_score - player_one_score > 0.0001:
            self.match_history[match_num] = {
                'Player_1': player_two,
                'Player_2': player_one,
                'Score': str(player_two_score) + "-" + str(player_one_score),
                'Result': "W"
            }
        
        # If its a draw:
        else:
            self.match_history[match_num] = {
                'Player_1': player_one,
                'Player_2': player_two,
                'Score': str(player_one_score) + "-" + str(player_two_score),
                'Result': "D"
            }
        self.update_standings()


    def update_standings(self):
        """
        Generates the standings of a given match history dictionary.
        
        Requires match_history plus the list of remaining players (in case of drops)
            Also because its easier.
        
        The returned standings_df has the following:
            "Player", "Points", "OMW"
        """
        
        # We have an opponents key, but we'll get rid of it after calculating OMW
        standings_dict = {
            "Player": self.list_of_players,
            "Played": [],
            "Points": [],
            # Add lists for Opponent Match Win% and Opponents
            "OMW": [],
            "Opponents": []
        }
        
        # For each player 
        for player in self.list_of_players:
            
            played = 0
            points = 0
            # Create a list that will house the opponents they've played.
            opponents = []
            
            # Check to see if they were involved in a match
            for match in self.match_history:
                # If they were player 1
                if player == self.match_history[match]["Player_1"]:
                    # Increased played by 1
                    played += 1
                    # Fill the opponents list with the names of each opponent
                    opponents.append(self.match_history[match]["Player_2"])
                    
                    # If they won, add 1 point
                    if self.match_history[match]["Result"] == "W":
                        points += 1
                    # If they drew, add 0.5 point
                    elif self.match_history[match]["Result"] == "D":
                        points += 0.5
                
                # If they were player 2
                elif player == self.match_history[match]["Player_2"]:
                    
                    # Increase games played and add opponent.
                    played += 1
                    opponents.append(self.match_history[match]["Player_1"])
                    
                    # If they drew, add 0.5 point
                    if self.match_history[match]["Result"] == "D":
                        points += 0.5
                        
            # Once we've looped through all the matches
            # Append the stats to the standings_dict
            standings_dict["Played"].append(played)
            standings_dict["Points"].append(points)
            standings_dict["Opponents"].append(opponents)
        
        # We can only calculate OMW after all matches have been added to the standings
        for opponent_list in standings_dict["Opponents"]:
            
            # Create a list with the OMW of each of their opponents.
            running_omw = []
            
            # For each opponent they've previously played, find their win percentage.
            for opponent in opponent_list:
                
                # Find index of their opponent
                opponent_index = standings_dict["Player"].index(opponent)

                # Calculate their OMW by dividing the points they've earned by the 
                # number of games they've played.
                running_omw.append(standings_dict["Points"][opponent_index] / 
                                standings_dict["Played"][opponent_index])

            # If it's the first round, no one has played anyone yet and the length of running_omw 
            # will be 0. 
            if len(running_omw) == 0:
                standings_dict["OMW"].append(0)
            else:
                # Get the average OMW and round to three decimal places. 
                standings_dict["OMW"].append(np.round(np.mean(running_omw), 3))
        
        # Remove the opponents key:value pair
        standings_dict.pop("Opponents")
        
        # Turn the dictionary into a dataframe
        self.standings_df = pd.DataFrame.from_dict(standings_dict).sort_values(["Points", "OMW"], ascending = False)

        

    def determine_pairings(self):
            """
            Determines pairings for a set of standings and the match_history of the tournament
            
            standings_df should have:
                "Player", "Points", "OMW"
            """
            # Create a list to hold our pairings
            pairings = list()
            
            # Sort the standings_df from best performing to worst performing
            # Note that we use sample(frac = 1) to ensure that the duplicates are not sorted
            # alphabetically
            sorted_df = self.standings_df.sample(frac = 1).sort_values(["Points", "OMW"], ascending = False)
            
            # Note that this preserves the ordering
            player_list = list(sorted_df["Player"].unique())
            
            # Code runs until player_list is empty, i.e. there are no players left to be paired
            while len(player_list) > 0:
                
                # We are going to try and match the first player in player_list - the "primary"
                # player. They'll be denoted by player_list[0]
                
                # First check - who has this player played before?
                previously_played = []
                
                for match in self.match_history:
                
                    # If our primary player was one of the belligerents, put the other guy in
                    # previously played
                    if player_list[0] == self.match_history[match]["Player_1"]:
                        previously_played.append(self.match_history[match]["Player_2"])
                    elif player_list[0] == self.match_history[match]["Player_2"]:
                        previously_played.append(self.match_history[match]["Player_1"])
                        
                
                # Pair with next highest legal player. 
                for index in range(1, len(player_list)):
                    # If the players have not played before, add them to pairings and remove them
                    # from the player_list
                    # Then break the for loop.
                    if player_list[index] not in previously_played:
                        # Note that we have to use .pop(index-1) because
                        # .pop(0) happens FIRST, so all indices are moved back by 1.
                        pairings.append([player_list.pop(0), player_list.pop(index-1)])
                        break
            
            # Return our list of pairings
            return pairings

    def print_standings(self):
        print(tabulate(self.standings_df, headers = 'keys', tablefmt = 'psql'))

    # a table is a simple list of humans
    def next_table(selfl, table):
        return [table[0]] + [table[-1]] + table[1:-1]
        # [0 1 2 3 4 5 6 7] -> [0 7 1 2 3 4 5 6]

    # a pairing is a list of pairs of humans
    def pairing_from_table(self, table):
        return list(zip(table[:len(table)//2], table[-1:len(table)//2-1:-1]))
        # [0 1 2 3 4 5 6 7] -> [(0,7), (1,6), (2,5), (3,4)]

    # a human is an int
    def get_programme(self, programme_length, table):
        pairing_list = []
        for day in range(programme_length):
            pairing_list.append(self.pairing_from_table(table))
            table = self.next_table(table)
        return pairing_list


def main():
    list_of_players = ["Bulbasaur", 
                        "Pikachu", 
                        "Squirtle", 
                        "Charmander",
                        "Caterpie",
                        "Pidgey",
                        "Spearow",
                        "Eevee"]
    match_mgr = MatchManager(list_of_players)
    match_mgr.print_standings()
    print("Initial pairing")
    print(match_mgr.determine_pairings())

    history = {0: {'Player_1': 'Eevee', 'Player_2': 'Bulbasaur', 'Score': '1.0-0.0', 'Result': 'W'},
        1: {'Player_1': 'Pikachu', 'Player_2': 'Pidgey', 'Score': '1.0-0.0', 'Result': 'W'},
        2: {'Player_1': 'Charmander', 'Player_2': 'Spearow', 'Score': '2.0-1.0', 'Result': 'W'},
        3: {'Player_1': 'Squirtle', 'Player_2': 'Caterpie', 'Score': '1.0-0.0', 'Result': 'W'},
        4: {'Player_1': 'Pikachu', 'Player_2': 'Squirtle', 'Score': '1.0-0.0', 'Result': 'W'},
        5: {'Player_1': 'Charmander', 'Player_2': 'Eevee', 'Score': '1.0-1.0', 'Result': 'D'},
        6: {'Player_1': 'Spearow', 'Player_2': 'Pidgey', 'Score': '1.0-1.0', 'Result': 'D'},
        7: {'Player_1': 'Bulbasaur', 'Player_2': 'Caterpie', 'Score': '1.0-0.0', 'Result': 'W'}}
    for k in history.keys():
        match_mgr.add_result(k, history[k]['Player_1'], history[k]['Player_2'], 
            float(history[k]['Score'].split('-')[0]), float(history[k]['Score'].split('-')[1]))
    
    match_mgr.update_standings()
    match_mgr.print_standings()
    print("Round 2 pairing")
    print(match_mgr.determine_pairings())
    

if __name__ == "__main__":
    main()
