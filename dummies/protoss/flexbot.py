"""
- Version 1.3: Due to the current Rush/Cheese Meta, I implemented a more defensive build order and in return deactivated
the 2-Base Immortal BO.

- Version 1.4: Switched from randomly chosen build orders to scouting based build order. Yet, still not completely with
a neural network but with basic rules, provided by a neural network.

- Version 1.5: Added a simple neural network to chose build orders based on scouting information.
Local tests with hundreds of games revealed that win rates compared to random choosing increased from 44% to 71%.
Bots used locally: YoBot, Tyr, Tyrz, 5minBot, BlinkerBot, NaughtyBot, SarsaBot, SeeBot, ramu,
Micromachine, Kagamine, AviloBot, EarlyAggro, Voidstar, ReeBot

- Version 1.6: Adapted early game rush defense in order to deal better with 12 pools (e.g. by CheeZerg).
Trained a new neural network with 730 games against the newest versions of most bots available.
Also refined scouting on 4 player maps and tuned the late game emergency strategy to prevent ties.

- Version 1.6.1: Bugfixes and new Model

- Version 1.7: Added a One-Base defence into Void-Ray build in order to deal with other very aggressive builds

- Version 1.7.1: Bugfixes and improved Voidray micro

- Version 1.7.2: Newly trained model

- Version 1.7.3 - 4: Small Bugfixes

- Version 1.7.5: Slightly improved Rush defence

- Version 1.8: Improved scouting with more scouting parameters, new model and various bug fixes / small improvements

- Version 1.9: Improved building placement and attack priorities. Oracle harass for Stargate build

- Version 2.0: Updated to Python 3.7.4 and to Burnys Python-sc2 vom 20.09.2019

- Version 2.1: Switched to game_step = 4. Added a Random Forrest Classifier and a manual BO-Choice to the chat to compare the results with those of the DNN
                Tried to increase survivalbility of the scout

- Version 3.0: Complete rewrite of MadAI in the sharpy-sc2 framework developed by Infy & merfolk. Initially implemented 3 basic strategies, i.e.
                4-Gate, 2-Base Robo and Defensive build, randomly chosen in order to gather training data

- Version 3.1: Many minor improvements due to issues revealed in ladder replays. Addition of an automtic adaptive gateway unit selector,
                based on a counter table. This should ensure that the gateway units are always the best composition with regards to the enemy units.

- Version 3.2: Added the Skytoss build with an early Oracle Harass and follow-up Voidrays with Chargelots

- Version 3.3: Added the (rather messy) neural network and random forrest classifier from MadAI 2.1 for build order choices

- Version 3.3.1: Changed the Skytoss BO from Voidrays to Tempests

- Version 3.4: Account for losses with a specific build order by having separate models trained with lost games.
                Computation of the final prediction by substracting win prediction - loss prediction for both models and
                all four build orders. Then taking the build order with the highest results. If an overall prediction for
                a specific build order has a positive value, it is more likely to win with that, while if it has a neagtive value
                it is more likely to lose with it.
- Version 4.0 Porting everything to the latest sharpy-py and python-sc2 to work with the latest game engine.
"""

from typing import Optional, List
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.ability_id import RALLY_UNITS
from sc2.ids.upgrade_id import UpgradeId
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from sharpy.managers.core.roles import UnitTask
from sharpy.knowledges import KnowledgeBot
from sharpy.plans import BuildOrder, Step, SequentialList, StepBuildGas
from sharpy.plans.acts.protoss import *

from sharpy.plans.require import *
from sharpy.plans.tactics import *
from sharpy.plans.tactics.protoss import *
from sharpy.managers.core.manager_base import ManagerBase
from sharpy.managers.extensions import BuildDetector
from sharpy.interfaces import IZoneManager, IEnemyUnitsManager
from sharpy.interfaces import IGameAnalyzer
from sharpy.combat.group_combat_manager import GroupCombatManager

from sharpy.managers.core import *
from sharpy.managers.core import ActManager, GatherPointSolver
from sharpy.managers.core import EnemyUnitsManager
from sharpy.managers.extensions import EnemyArmyPredicter
from sharpy.managers.extensions import MemoryManager
from sharpy.plans.acts import *
from sharpy.plans.acts.protoss import *
from sharpy.plans.require import *
from sharpy.plans.tactics import *
from sharpy.plans import BuildOrder, Step, SequentialList, StepBuildGas
from sharpy.knowledges import SkeletonBot
from sc2.ids.upgrade_id import UpgradeId

from typing import List
import random
import numpy as np
import time
# import pickle
# import keras


class GetScoutingData(ActBase):
    def __init__(self):
        super().__init__()
        self.build_order = -1
        self.scout_data = []
        # self.use_model = True
        self.use_model = False

        # if self.use_model:
        #     self.model = keras.models.load_model("FlexBot/MadAI_19_07_2020")
        #     self.model_loss = keras.models.load_model("FlexBot/MadAI_19_07_2020_loss")
        #     self.RF_model = pickle.load(open('FlexBot/MadAI_RF_19_07_2020.sav', 'rb'))
        #     self.RF_model_loss = pickle.load(open('FlexBot/MadAI_RF_19_07_2020_loss.sav', 'rb'))
        #     self.choice_data = []

    async def start(self, knowledge: 'Knowledge'):
        await super().start(knowledge)
        # self.micro.load_default_methods()
        # self.micro.generic_micro = MicroAdepts(False)
        self.build_detector = knowledge.get_manager(BuildDetector)
        self.zone_manager = knowledge.get_required_manager(IZoneManager)
        self.enemy_units_manager = knowledge.get_required_manager(IEnemyUnitsManager)
        self.build_detector = knowledge.get_manager(BuildDetector)
        # self.enemy_army_detector = knowledge.get_manager(EnemyArmyPredicter)
        self.game_analyzer = knowledge.get_required_manager(IGameAnalyzer)
        # await self.micro.start(knowledge)

    async def execute(self) -> bool:

        if self.build_order == -1:

            if self.build_detector and self.build_detector.rush_detected:
                enemy_rush = 1
            else:
                enemy_rush = 0

            # enemy_pylon_pos = []
            # for pylon in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.PYLON))):
            #     enemy_pylon_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.PYLON)[pylon].position)
            # enemy_gateway_pos = []
            # for gateway in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.GATEWAY))):
            #     enemy_gateway_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.GATEWAY)[gateway].position)
            # enemy_forge_pos = []
            # for forge in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.FORGE))):
            #     enemy_forge_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.FORGE)[forge].position)
            # enemy_cannon_pos = []
            # for cannon in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON))):
            #     enemy_cannon_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)[cannon].position)
            # enemy_depot_pos = []
            # for depot in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOT))):
            #     enemy_depot_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOT)[depot].position)
            # enemy_depotlow_pos = []
            # for depotlow in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOTLOWERED))):
            #     enemy_depotlow_pos.append(
            #         self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOTLOWERED)[depotlow].position
            #     )
            # enemy_bunker_pos = []
            # for bunker in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.BUNKER))):
            #     enemy_bunker_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.BUNKER)[bunker].position)
            # enemy_barracks_pos = []
            # for barracks in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS))):
            #     enemy_barracks_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS)[barracks].position)
            # enemy_factory_pos = []
            # for factory in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.FACTORY))):
            #     enemy_factory_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.FACTORY)[factory].position)
            # enemy_pool_pos = []
            # for pool in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.SPAWNINGPOOL))):
            #     enemy_pool_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.SPAWNINGPOOL)[pool].position)
            # enemy_spine_pos = []
            # for spine in range(len(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER))):
            #     enemy_spine_pos.append(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER)[spine].position)

            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PYLON)) >= 1:
            #     pylon1_pos = enemy_pylon_pos[0][0] + enemy_pylon_pos[0][1]
            # else:
            #     pylon1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PYLON)) >= 2:
            #     pylon2_pos = enemy_pylon_pos[1][0] + enemy_pylon_pos[1][1]
            # else:
            #     pylon2_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PYLON)) >= 3:
            #     pylon3_pos = enemy_pylon_pos[2][0] + enemy_pylon_pos[2][1]
            # else:
            #     pylon3_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.GATEWAY)) >= 1:
            #     gate1_pos = enemy_gateway_pos[0][0] + enemy_gateway_pos[0][1]
            # else:
            #     gate1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.GATEWAY)) >= 2:
            #     gate2_pos = enemy_gateway_pos[1][0] + enemy_gateway_pos[1][1]
            # else:
            #     gate2_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.FORGE)) >= 1:
            #     forge1_pos = enemy_forge_pos[0][0] + enemy_forge_pos[0][1]
            # else:
            #     forge1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)) >= 1:
            #     cannon1_pos = enemy_cannon_pos[0][0] + enemy_cannon_pos[0][1]
            # else:
            #     cannon1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)) >= 2:
            #     cannon2_pos = enemy_cannon_pos[1][0] + enemy_cannon_pos[1][1]
            # else:
            #     cannon2_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)) >= 3:
            #     cannon3_pos = enemy_cannon_pos[2][0] + enemy_cannon_pos[2][1]
            # else:
            #     cannon3_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)) >= 4:
            #     cannon4_pos = enemy_cannon_pos[3][0] + enemy_cannon_pos[3][1]
            # else:
            #     cannon4_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOT)) >= 1:
            #     depot1_pos = enemy_depot_pos[0][0] + enemy_depot_pos[0][1]
            # else:
            #     depot1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOT)) >= 2:
            #     depot2_pos = enemy_depot_pos[1][0] + enemy_depot_pos[1][1]
            # else:
            #     depot2_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOT)) >= 3:
            #     depot3_pos = enemy_depot_pos[2][0] + enemy_depot_pos[2][1]
            # else:
            #     depot3_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOTLOWERED)) >= 1:
            #     depotlow1_pos = enemy_depotlow_pos[0][0] + enemy_depotlow_pos[0][1]
            # else:
            #     depotlow1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOTLOWERED)) >= 2:
            #     depotlow2_pos = enemy_depotlow_pos[1][0] + enemy_depotlow_pos[1][1]
            # else:
            #     depotlow2_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOTLOWERED)) >= 3:
            #     depotlow3_pos = enemy_depotlow_pos[2][0] + enemy_depotlow_pos[2][1]
            # else:
            #     depotlow3_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.BUNKER)) >= 1:
            #     bunker1_pos = enemy_bunker_pos[0][0] + enemy_bunker_pos[0][1]
            # else:
            #     bunker1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS)) >= 1:
            #     barracks1_pos = enemy_barracks_pos[0][0] + enemy_barracks_pos[0][1]
            # else:
            #     barracks1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS)) >= 2:
            #     barracks2_pos = enemy_barracks_pos[1][0] + enemy_barracks_pos[1][1]
            # else:
            #     barracks2_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS)) >= 3:
            #     barracks3_pos = enemy_barracks_pos[2][0] + enemy_barracks_pos[2][1]
            # else:
            #     barracks3_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.FACTORY)) >= 1:
            #     factory1_pos = enemy_factory_pos[0][0] + enemy_factory_pos[0][1]
            # else:
            #     factory1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SPAWNINGPOOL)) >= 1:
            #     pool1_pos = enemy_pool_pos[0][0] + enemy_pool_pos[0][1]
            # else:
            #     pool1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER)) >= 1:
            #     spine1_pos = enemy_spine_pos[0][0] + enemy_spine_pos[0][1]
            # else:
            #     spine1_pos = 0
            # if len(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER)) >= 2:
            #     spine2_pos = enemy_spine_pos[1][0] + enemy_spine_pos[1][1]
            # else:
            #     spine2_pos = 0

            # self.scout_data = [
            #     self.ai.enemy_start_locations[0],
            #     enemy_rush,
            #     self.enemy_units_manager.enemy_worker_count,
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.NEXUS)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.PYLON)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.GATEWAY)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.CYBERNETICSCORE)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.ASSIMILATOR)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.BUNKER)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.FORGE)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.COMMANDCENTER)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.ORBITALCOMMAND)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOT)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.SUPPLYDEPOTLOWERED)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.TECHLAB)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.REACTOR)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.REFINERY)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.FACTORY)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.HATCHERY)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.SPAWNINGPOOL)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.ROACHWARREN)),
            #     len(self.knowledge.unit_cache.enemy(UnitTypeId.EXTRACTOR)),
            #     self.enemy_units_manager.unit_count(UnitTypeId.ZEALOT),
            #     self.enemy_units_manager.unit_count(UnitTypeId.STALKER),
            #     self.enemy_units_manager.unit_count(UnitTypeId.MARINE),
            #     self.enemy_units_manager.unit_count(UnitTypeId.REAPER),
            #     self.enemy_units_manager.unit_count(UnitTypeId.ZERGLING),
            #     self.enemy_units_manager.unit_count(UnitTypeId.ROACH),
            #     pylon1_pos,
            #     pylon2_pos,
            #     pylon3_pos,
            #     gate1_pos,
            #     gate2_pos,
            #     forge1_pos,
            #     cannon1_pos,
            #     cannon2_pos,
            #     cannon3_pos,
            #     cannon4_pos,
            #     depot1_pos,
            #     depot2_pos,
            #     depot3_pos,
            #     depotlow1_pos,
            #     depotlow2_pos,
            #     depotlow3_pos,
            #     bunker1_pos,
            #     barracks1_pos,
            #     barracks2_pos,
            #     barracks3_pos,
            #     factory1_pos,
            #     pool1_pos,
            #     spine1_pos,
            #     spine2_pos,
            #     self.game_analyzer.enemy_mineral_income,
            #     self.game_analyzer.enemy_gas_income,
            #     self.game_analyzer.enemy_power.power,
            #     self.game_analyzer.enemy_predict_power.power,
            #     self.game_analyzer.our_power.power,
            #     self.game_analyzer.enemy_predicter.own_value,
            #     self.game_analyzer.enemy_predicter.enemy_value,
            #     self.game_analyzer.enemy_predicter.enemy_mined_minerals,
            #     self.game_analyzer.enemy_predicter.enemy_mined_gas,
            # ]

            # if self.use_model:
            #     self.choice_data = [
            #         self.scout_data[0][0]+self.scout_data[0][1],
            #         self.scout_data[1],
            #         self.scout_data[2],
            #         self.scout_data[3],
            #         self.scout_data[4],
            #         self.scout_data[5],
            #         self.scout_data[6],
            #         self.scout_data[7],
            #         self.scout_data[8],
            #         self.scout_data[9],
            #         self.scout_data[10],
            #         self.scout_data[11],
            #         self.scout_data[12],
            #         self.scout_data[13],
            #         self.scout_data[14],
            #         self.scout_data[15],
            #         self.scout_data[16],
            #         self.scout_data[17],
            #         self.scout_data[18],
            #         self.scout_data[19],
            #         self.scout_data[20],
            #         self.scout_data[21],
            #         self.scout_data[22],
            #         self.scout_data[23],
            #         self.scout_data[24],
            #         self.scout_data[25],
            #         self.scout_data[26],
            #         self.scout_data[27],
            #         self.scout_data[28],
            #         self.scout_data[29],
            #         self.scout_data[30],
            #         self.scout_data[31],
            #         self.scout_data[32],
            #         self.scout_data[33],
            #         self.scout_data[34],
            #         self.scout_data[35],
            #         self.scout_data[36],
            #         self.scout_data[37],
            #         self.scout_data[38],
            #         self.scout_data[39],
            #         self.scout_data[40],
            #         self.scout_data[41],
            #         self.scout_data[42],
            #         self.scout_data[43],
            #         self.scout_data[44],
            #         self.scout_data[45],
            #         self.scout_data[46],
            #         self.scout_data[47],
            #         self.scout_data[48],
            #         self.scout_data[49],
            #         self.scout_data[50],
            #         self.scout_data[51],
            #         self.scout_data[52],
            #         self.scout_data[53],
            #         self.scout_data[54],
            #         self.scout_data[55],
            #         self.scout_data[56],
            #         self.scout_data[57],
            #         self.scout_data[58],
            #         self.scout_data[59],
            #         self.scout_data[60],
            #         self.scout_data[61],
            #         self.scout_data[62],
            #         self.scout_data[63],
            #     ]

            #     # print(self.choice_data)
            #     new_choice_data = np.array(self.choice_data).reshape(-1, 64, 1)
            #     # print(new_choice_data)

            #     prediction = self.model.predict(new_choice_data)
            #     prediction_loss = self.model_loss.predict(new_choice_data)
            #     # print(prediction[0])
            #     RF_predictions = self.RF_model.predict_proba([self.choice_data])
            #     RF_predictions_loss = self.RF_model_loss.predict_proba([self.choice_data])

                # if len(self.knowledge.unit_cache.enemy(UnitTypeId.NEXUS)) > 1 or \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.COMMANDCENTER)) > 1 or \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.COMMANDCENTER)) + \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.ORBITALCOMMAND)) > 1:
                #     manual_0 = 0
                #     manual_1 = 1
                #     manual_2 = 0
                #     manual_3 = 0
                # elif len(self.knowledge.unit_cache.enemy(UnitTypeId.GATEWAY)) > 2 or \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.BARRACKS)) > 2 or \
                #         self.knowledge.enemy_units_manager.unit_count(UnitTypeId.ZERGLING) > 2:
                #     manual_0 = 0
                #     manual_1 = 0
                #     manual_2 = 1
                #     manual_3 = 0
                # elif len(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER)) > 0 or \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)) > 0 or \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.BUNKER)) > 0 or \
                #         len(self.knowledge.unit_cache.enemy(UnitTypeId.FORGE)) > 0:
                #     manual_0 = 0.5
                #     manual_1 = 0
                #     manual_2 = 0
                #     manual_3 = 0.5
                # else:
                #     manual_0 = 0.25
                #     manual_1 = 0.25
                #     manual_2 = 0.25
                #     manual_3 = 0.25

                # await self.ai.chat_send(
                #     "2-Base Robo: ["
                #     + str(round(prediction[0][0] * 100, 2))
                #     + " - "
                #     + str(round(prediction_loss[0][0] * 100, 2))
                #     + " / "
                #     + str(round(RF_predictions[0][0] * 100, 2))
                #     + " - "
                #     + str(round(RF_predictions_loss[0][0] * 100, 2))
                #     + " / "
                #     + str(round((prediction[0][0] - prediction_loss[0][0] + RF_predictions[0][0] - RF_predictions_loss[0][0]) * 100 / 2, 2))
                #     + "]; 4-Gate Proxy: ["
                #     + str(round(prediction[0][1] * 100, 2))
                #     + " - "
                #     + str(round(prediction_loss[0][1] * 100, 2))
                #     + " / "
                #     + str(round(RF_predictions[0][1] * 100, 2))
                #     + " - "
                #     + str(round(RF_predictions_loss[0][1] * 100, 2))
                #     + " / "
                #     + str(round((prediction[0][1] - prediction_loss[0][1] + RF_predictions[0][1] - RF_predictions_loss[0][1]) * 100 / 2, 2))
                #     + "]; Rush Defend: ["
                #     + str(round(prediction[0][2] * 100, 2))
                #     + " - "
                #     + str(round(prediction_loss[0][2] * 100, 2))
                #     + " / "
                #     + str(round(RF_predictions[0][2] * 100, 2))
                #     + " - "
                #     + str(round(RF_predictions_loss[0][2] * 100, 2))
                #     + " / "
                #     + str(round((prediction[0][2] - prediction_loss[0][2] + RF_predictions[0][2] - RF_predictions_loss[0][2]) * 100 / 2, 2))
                #     + "]; Skytoss: ["
                #     + str(round(prediction[0][3] * 100, 2))
                #     + " - "
                #     + str(round(prediction_loss[0][3] * 100, 2))
                #     + " / "
                #     + str(round(RF_predictions[0][3] * 100, 2))
                #     + " - "
                #     + str(round(RF_predictions_loss[0][3] * 100, 2))
                #     + " / "
                #     + str(round((prediction[0][3] - prediction_loss[0][3] + RF_predictions[0][3] - RF_predictions_loss[0][3]) * 100 / 2, 2))
                #     + "]"
                # )
                # choice = np.argmax([round((prediction[0][0] - prediction_loss[0][0] + RF_predictions[0][0] - RF_predictions_loss[0][0]) * 100 / 2, 2),
                #                     round((prediction[0][1] - prediction_loss[0][1] + RF_predictions[0][1] - RF_predictions_loss[0][1]) * 100 / 2, 2),
                #                     round((prediction[0][2] - prediction_loss[0][2] + RF_predictions[0][2] - RF_predictions_loss[0][2]) * 100 / 2, 2),
                #                     round((prediction[0][3] - prediction_loss[0][3] + RF_predictions[0][3] - RF_predictions_loss[0][3]) * 100 / 2, 2)])
                # self.build_order = choice

            # else:
            if enemy_rush:
                self.build_order = 2
                print("Flexbot Rush Defend BO chosen.")
            else:
                # self.build_order = random.choice([0, 1, 3])

                self.build_order = 0
                print("FlexBot 2-base Robo BO")
    
            if self.build_order == 0:
                await self.ai.chat_send(
                    "(glhf) FlexBot v4.0: 2-Base Robo BO chosen!"
                )
            elif self.build_order == 1:
                await self.ai.chat_send(
                    "(glhf) FlexBot v4.0: 4-Gate Proxy BO chosen!"
                )
            elif self.build_order == 2:
                await self.ai.chat_send(
                    "(glhf) FlexBot v4.0: Rush Defend BO chosen!"
                )
            elif self.build_order == 3:
                await self.ai.chat_send(
                    "(glhf) FlexBot v4.0: Skytoss BO chosen!"
                )
            else:
                await self.ai.chat_send(
                    "(glhf) FlexBot v4.0: No BO chosen! PANIC!"
                )

            return True
        else:
            return True


class Dt_Harass(ActBase):
    #TODO: Let only the frist DT walk to base and the rest attack the closest enemy, just as in the old MadBot
    def __init__(self):
        super().__init__()
        self.dts_detected = False
        self.already_merging_tags: List[int] = []
        self.main_dt_tag: List[int] = []
        self.first_dts = False

    async def execute(self) -> bool:
        if (self.cache.own(UnitTypeId.DARKTEMPLAR).ready and not self.dts_detected and self.cache.own(UnitTypeId.DARKTEMPLAR).ready.random.shield < 60) or \
                (len(self.knowledge.unit_cache.enemy(UnitTypeId.PHOTONCANNON)) > 0 and not self.dts_detected) or \
                (len(self.knowledge.unit_cache.enemy(UnitTypeId.SPINECRAWLER)) > 0 and not self.dts_detected) or \
                (len(self.knowledge.unit_cache.enemy(UnitTypeId.MISSILETURRET)) > 0 and not self.dts_detected) or \
                (len(self.knowledge.unit_cache.enemy(UnitTypeId.OVERSEER)) > 0 and not self.dts_detected):
            # Don't even start the harass if the enemy has some sort of detection
            self.dts_detected = True
            for dt in self.cache.own(UnitTypeId.DARKTEMPLAR):
                # Get back to the gather point to be morphed to Archons savely
                dt.move(self.zone_manager.expansion_zones[-2].gather_point)
            print('DTs detected!!')
        # Start dark templar attack
        if not self.dts_detected:
            if self.cache.own(UnitTypeId.DARKTEMPLAR).exists:
                if not self.first_dts:
                    dt1 = self.cache.own(UnitTypeId.DARKTEMPLAR)[0]
                    self.main_dt_tag.append(dt1.tag)
                    # self.do(
                    dt1(
                        RALLY_UNITS,
                        self.zone_manager.expansion_zones[-1].mineral_line_center,
                    )
                    # )
                    self.knowledge.roles.set_task(UnitTask.Reserved, dt1)
                    self.first_dts = True
                else:
                    dts = self.cache.own(UnitTypeId.DARKTEMPLAR).ready.tags_not_in(self.main_dt_tag)
                    if dts.amount == 1:
                        exe_dt = dts[0]
                        # self.do(exe_dt.attack(self.zone_manager.expansion_zones[-2].mineral_line_center))
                        exe_dt.attack(self.zone_manager.expansion_zones[-2].mineral_line_center)
                        self.knowledge.roles.set_task(UnitTask.Reserved, exe_dt)
                    elif dts.amount >= 2:
                        dts = dts.random_group_of(2)
                        exe_dt = dts[0]
                        attack_dt = dts[1]
                        exe_dt.attack(self.zone_manager.expansion_zones[-2].mineral_line_center)
                        attack_dt.attack(self.zone_manager.enemy_main_zone.center_location)
                        self.knowledge.roles.set_task(UnitTask.Reserved, exe_dt)
                        self.knowledge.roles.set_task(UnitTask.Reserved, attack_dt)
                        self.main_dt_tag.append(exe_dt.tag)
                        self.main_dt_tag.append(attack_dt.tag)

        else:
            if len(self.ai.units(UnitTypeId.DARKTEMPLAR).ready.closer_than(10, self.zone_manager.expansion_zones[-2].gather_point)) >= 2:
                # Only morph Archons when its safe, i.e. at the current gather point
                templars = self.cache.own(UnitTypeId.DARKTEMPLAR).ready.tags_not_in(self.already_merging_tags)
                if templars.amount > 1:
                    unit: Unit = templars[0]
                    self.already_merging_tags.append(unit.tag)
                    target: Unit = templars.tags_not_in(self.already_merging_tags).closest_to(unit)
                    self.already_merging_tags.append(target.tag)
                    self.knowledge.roles.set_task(UnitTask.Reserved, unit)
                    self.knowledge.roles.set_task(UnitTask.Reserved, target)
                    self.knowledge.print(f"[ARCHON] merging {str(unit.tag)} and {str(target.tag)}")
                    from s2clientprotocol import raw_pb2 as raw_pb
                    from s2clientprotocol import sc2api_pb2 as sc_pb
                    command = raw_pb.ActionRawUnitCommand(
                        ability_id=AbilityId.MORPH_ARCHON.value,
                        unit_tags=[unit.tag, target.tag],
                        queue_command=False
                    )
                    action = raw_pb.ActionRaw(unit_command=command)
                    await self.ai._client._execute(action=sc_pb.RequestAction(
                        actions=[sc_pb.Action(action_raw=action)]
                    ))

        return True


class Oracle_Harass(ActBase):
    def __init__(self):
        super().__init__()
        self.harass_started = False
        self.do_something_after_travel = 0

    async def execute(self) -> bool:
        if len(self.ai.units(UnitTypeId.ORACLE)) >= 1 and not self.harass_started:
            self.save_target_main = self.ai.enemy_start_locations[0].towards(self.ai.game_info.map_center,
                                                                               -25)
            # print('X:', self.knowledge.ai.game_info.map_center[0] - self.knowledge.ai.start_location[0], 'Y:',
            #       self.knowledge.ai.game_info.map_center[1] - self.knowledge.ai.start_location[1])
            if self.knowledge.ai.game_info.map_center[0] - self.knowledge.ai.start_location[0] < 0:
                self.safe_spot1 = 1
            else:
                self.safe_spot1 = (self.knowledge.ai.game_info.map_center[0] * 2) - 1
            if self.knowledge.ai.game_info.map_center[1] - self.knowledge.ai.start_location[1] > 0:
                self.safe_spot2 = 1
            else:
                self.safe_spot2 = (self.knowledge.ai.game_info.map_center[1] * 2) - 1
            or1 = self.ai.units(UnitTypeId.ORACLE)[0]
            self.knowledge.roles.set_task(UnitTask.Reserved, or1)
            or1.move(Point2((self.safe_spot1, self.safe_spot2)))
            or1.move(self.save_target_main, queue=True)
            self.harass_started = True
            self.do_something_after_travel = self.ai.time + 50
        elif len(self.ai.units(UnitTypeId.ORACLE)) >= 1 and self.harass_started:
            if self.ai.time > self.do_something_after_travel:
                or1 = self.ai.units(UnitTypeId.ORACLE)[0]
                self.knowledge.roles.set_task(UnitTask.Reserved, or1)
                attack_target_main = self.ai.enemy_start_locations[0].towards(self.ai.game_info.map_center, -5)
                save_target_main = self.ai.enemy_start_locations[0].towards(self.ai.game_info.map_center, -25)
                if or1.shield_percentage > 0.5 and or1.energy_percentage > 0.25:
                    workers = self.knowledge.ai.enemy_units.of_type({UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV})
                    if workers:
                        or1.attack(workers.closest_to(or1.position))
                        or1(AbilityId.BEHAVIOR_PULSARBEAMON, queue=True)
                    else:
                        or1.attack(attack_target_main)
                        or1(AbilityId.BEHAVIOR_PULSARBEAMON, queue=True)

                    # self.do(or1(BUILD_STASISTRAP, attack_target_main))
                    # self.do_something_after_trap1 = self.time + 20
                    # self.do_something_after_trap2 = self.time + 10
                elif or1.shield_percentage < 0.1 or or1.energy_percentage < 0.02:
                    or1(AbilityId.BEHAVIOR_PULSARBEAMOFF)
                    or1.move(save_target_main, queue=True)
                    print('Moving out again')

        return True


class FlexBot(KnowledgeBot):

    def __init__(self):
        super().__init__("FlexBot")
        self.proxy_location = None
        self.train_data = []
        self.scout = GetScoutingData()
        # self.knowledge.print(f"Flexbot Build Order {self.scout.build_order}", tag="Start", stats=False)
        print(f"Flexbot Build Order {self.scout.build_order}")
        

    # def configure_managers(self) -> Optional[List[ManagerBase]]:
    #     return [
    #         MemoryManager(),
    #         PreviousUnitsManager(),
    #         LostUnitsManager(),
    #         EnemyUnitsManager(),
    #         UnitCacheManager(),
    #         UnitValue(),
    #         UnitRoleManager(),
    #         PathingManager(),
    #         ZoneManager(),
    #         BuildingSolver(),
    #         IncomeCalculator(),
    #         CooldownManager(),
    #         GroupCombatManager(),
    #         GatherPointSolver(),
    #         ActManager(self.create_plan()),
    #     ]

    async def start(self, knowledge: 'Knowledge'):
        await super().start(knowledge)

    async def on_end(self, game_result):
        print("OnGameEnd() was called.")
        if str(game_result) == "Result.Victory":
            result = 1
        else:
            result = 0

        # if self.scout.scout_data:
        #     self.train_data.append(
        #         [
        #             result,
        #             self.scout.build_order,
        #             self.scout.scout_data[0][0]+self.scout.scout_data[0][1],
        #             self.scout.scout_data[1],
        #             self.scout.scout_data[2],
        #             self.scout.scout_data[3],
        #             self.scout.scout_data[4],
        #             self.scout.scout_data[5],
        #             self.scout.scout_data[6],
        #             self.scout.scout_data[7],
        #             self.scout.scout_data[8],
        #             self.scout.scout_data[9],
        #             self.scout.scout_data[10],
        #             self.scout.scout_data[11],
        #             self.scout.scout_data[12],
        #             self.scout.scout_data[13],
        #             self.scout.scout_data[14],
        #             self.scout.scout_data[15],
        #             self.scout.scout_data[16],
        #             self.scout.scout_data[17],
        #             self.scout.scout_data[18],
        #             self.scout.scout_data[19],
        #             self.scout.scout_data[20],
        #             self.scout.scout_data[21],
        #             self.scout.scout_data[22],
        #             self.scout.scout_data[23],
        #             self.scout.scout_data[24],
        #             self.scout.scout_data[25],
        #             self.scout.scout_data[26],
        #             self.scout.scout_data[27],
        #             self.scout.scout_data[28],
        #             self.scout.scout_data[29],
        #             self.scout.scout_data[30],
        #             self.scout.scout_data[31],
        #             self.scout.scout_data[32],
        #             self.scout.scout_data[33],
        #             self.scout.scout_data[34],
        #             self.scout.scout_data[35],
        #             self.scout.scout_data[36],
        #             self.scout.scout_data[37],
        #             self.scout.scout_data[38],
        #             self.scout.scout_data[39],
        #             self.scout.scout_data[40],
        #             self.scout.scout_data[41],
        #             self.scout.scout_data[42],
        #             self.scout.scout_data[43],
        #             self.scout.scout_data[44],
        #             self.scout.scout_data[45],
        #             self.scout.scout_data[46],
        #             self.scout.scout_data[47],
        #             self.scout.scout_data[48],
        #             self.scout.scout_data[49],
        #             self.scout.scout_data[50],
        #             self.scout.scout_data[51],
        #             self.scout.scout_data[52],
        #             self.scout.scout_data[53],
        #             self.scout.scout_data[54],
        #             self.scout.scout_data[55],
        #             self.scout.scout_data[56],
        #             self.scout.scout_data[57],
        #             self.scout.scout_data[58],
        #             self.scout.scout_data[59],
        #             self.scout.scout_data[60],
        #             self.scout.scout_data[61],
        #             self.scout.scout_data[62],
        #             self.scout.scout_data[63],
        #         ]
        # )
        # print(self.train_data)

        # np.save("data/{}_first.npy".format(str(int(time.time()))), np.array(self.train_data))

    async def create_plan(self) -> BuildOrder:
        # Common Start Build Order
        #TODO: Implement more BOs
        #TODO: Build second pylon at reaper ramp against Terran
        #TODO: Ignore Larva and Eggs even more?
        #TODO: Reenable Defence when Retreating
        #TODO: Ignore Hallucinations
        #TODO: Add time depended scouting variables, e.g. hatch before pool, etc.
        #TODO: Use the Phoenix-Scout-Info to make the attack trigger more flexible, based on the power difference
        #TODO: Position Rallypoint behind natural wall on Discobloodbath
        #TODO: Move the builder probe towards the expansion already before minerals are at 400 just as it is done in BuildPosition
        #TODO: Keep the units together better, i.e. not get lured out when defending or fight buildings while the other half of the army is fighting units somewhere close
        #TODO: Defence against a single attacking worker is not functioning as intended
        return BuildOrder([
            Step(None, ChronoUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS),
                 skip=UnitExists(UnitTypeId.PROBE, 19, include_pending=True), skip_until=UnitExists(UnitTypeId.PYLON, 1)),
            SequentialList([
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 14),
                GridBuilding(UnitTypeId.PYLON, 1),
                Step(UnitExists(UnitTypeId.PYLON, 1, include_pending=False), WorkerScout(), skip=RequireCustom(lambda k: self.scout.build_order >= 0)),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 15),
                GridBuilding(UnitTypeId.GATEWAY, 1),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 16),
                StepBuildGas(1),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 18),
                GridBuilding(UnitTypeId.PYLON, 2),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 20),
                StepBuildGas(2),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 21),
                GridBuilding(UnitTypeId.CYBERNETICSCORE, 1),
                ProtossUnit(UnitTypeId.ZEALOT, 1),
                ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 23),
                Step(None, self.scout, skip_until=UnitExists(UnitTypeId.CYBERNETICSCORE, 1))
            ]),
            Step(lambda k: self.scout.build_order == 0, self.two_base_robo()),
            Step(lambda k: self.scout.build_order == 1, self.four_gate()),
            Step(lambda k: self.scout.build_order == 2, self.defend_dt()),
            Step(lambda k: self.scout.build_order == 3, self.skytoss()),
            # Step(lambda k: self.scout.build_order == 4, self.two_base_stalker()),
            
            SequentialList([
                Step(None, PlanZoneDefense(), skip=UnitExists(UnitTypeId.PROBE, 23)),
                RestorePower(),
                DistributeWorkers(),
                Step(None, PlanZoneGather(), skip=UnitExists(UnitTypeId.PROBE, 23))
            ])
        ])

    def four_gate(self) -> ActBase:
        print(f"Flexbot Build Order four_gate")
        #TODO: Follow-up BO
        random_location = random.randrange(0, 2)
        if random_location == 0 and not self.knowledge.enemy_race == Race.Zerg:
            natural = self.zone_manager.expansion_zones[-3]
            pylon_pos: Point2 = natural.mineral_line_center.towards(
                    self.zone_manager.expansion_zones[-3].behind_mineral_position_center, -5)
        else:
            pylon_pos = self.game_info.map_center.towards(self.enemy_start_locations[0],
                                                                   17).position
        return BuildOrder([
            SequentialList([
                GridBuilding(UnitTypeId.GATEWAY, 2),
                BuildOrder(
                    [
                        AutoPylon(),
                        Tech(UpgradeId.WARPGATERESEARCH, UnitTypeId.CYBERNETICSCORE),
                        ProtossUnit(UnitTypeId.STALKER, 1, priority=True),
                        GridBuilding(UnitTypeId.GATEWAY, 3),
                        Step(TechReady(UpgradeId.WARPGATERESEARCH, 0.4), BuildPosition(UnitTypeId.PYLON, pylon_pos,
                                                exact=False, only_once=True), skip=TechReady(UpgradeId.WARPGATERESEARCH)),
                        GridBuilding(UnitTypeId.GATEWAY, 4),
                        [
                            Step(None, ProtossUnit(UnitTypeId.SENTRY, 1),
                                 skip_until=UnitExists(UnitTypeId.STALKER, 2, include_pending=True)),
                            Step(None, ProtossUnit(UnitTypeId.SENTRY, 2),
                                 skip_until=UnitExists(UnitTypeId.STALKER, 6, include_pending=True)),
                            Step(None, GateUnit()),
                        ],
                    ])
            ]),
            SequentialList([
                ChronoTech(AbilityId.RESEARCH_WARPGATE, UnitTypeId.CYBERNETICSCORE),
                ChronoUnit(UnitTypeId.STALKER, UnitTypeId.GATEWAY),
            ]),
            SequentialList([
                # Stop Defending when attacking, i.e. Base-Trade
                Step(None, PlanZoneDefense(), skip=TechReady(UpgradeId.WARPGATERESEARCH)),
                PlanZoneGather(),
                # Step(UnitExists(UnitTypeId.GATEWAY, 4), PlanZoneGather()),
                PlanZoneAttack(16),
                PlanFinishEnemy(),
            ])
        ])

    def two_base_robo(self) -> ActBase:
        print(f"Flexbot Build Order two_base_robo")
        #TODO: Archons as follow-up after first push (ActArchon)
        pylon_pos = self.game_info.map_center.position
        attack = PlanZoneAttack(12)
        attack.enemy_power_multiplier = 0.8  # Attack even if it might be a bad idea
        return BuildOrder([
            SequentialList([
                Expand(2),
                BuildOrder(
                    [
                        Tech(UpgradeId.WARPGATERESEARCH, UnitTypeId.CYBERNETICSCORE),
                        ProtossUnit(UnitTypeId.STALKER, 1),
                        Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 24)),
                    ]),
                GridBuilding(UnitTypeId.ROBOTICSFACILITY, 1),
                Step(None, ProtossUnit(UnitTypeId.SENTRY, 1), skip=TechReady(UpgradeId.CHARGE)),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 25)),
                GridBuilding(UnitTypeId.PYLON, 3),
                GridBuilding(UnitTypeId.GATEWAY, 2),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 26)),
                BuildOrder(
                    [
                        Step(None, ProtossUnit(UnitTypeId.SENTRY, 2), skip=TechReady(UpgradeId.CHARGE)),
                        Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 30)),
                        GridBuilding(UnitTypeId.PYLON, 4),
                        SequentialList([
                            Step(UnitExists(UnitTypeId.SENTRY, 1), HallucinatedPhoenixScout()),
                            Step(UnitExists(UnitTypeId.SENTRY, 1), PlanHallucination()),
                        ])
                    ]),
                Step(UnitExists(UnitTypeId.ROBOTICSFACILITY, 1), ProtossUnit(UnitTypeId.IMMORTAL, 1)),
                Step(None, ProtossUnit(UnitTypeId.ZEALOT, 3), skip=TechReady(UpgradeId.CHARGE)),
                GridBuilding(UnitTypeId.GATEWAY, 3),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 32)),
                Step(UnitExists(UnitTypeId.IMMORTAL, 1), ProtossUnit(UnitTypeId.OBSERVER, 1)),
                StepBuildGas(3),
                Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1), GridBuilding(UnitTypeId.TWILIGHTCOUNCIL, 1)),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 34)),
                Step(UnitExists(UnitTypeId.ROBOTICSFACILITY, 1), ProtossUnit(UnitTypeId.IMMORTAL, 2)),
                Step(None, ProtossUnit(UnitTypeId.SENTRY, 4), skip=TechReady(UpgradeId.CHARGE)),
                GridBuilding(UnitTypeId.GATEWAY, 4),
                Step(UnitExists(UnitTypeId.IMMORTAL, 1), Tech(UpgradeId.CHARGE, UnitTypeId.TWILIGHTCOUNCIL)),
                StepBuildGas(4),
                Step(UnitExists(UnitTypeId.IMMORTAL, 3), BuildPosition(UnitTypeId.PYLON, pylon_pos, exact=False, only_once=True)),
            ]),
            BuildOrder(
                [
                    AutoPylon(),
                    Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 44)),
                    Step(UnitExists(UnitTypeId.IMMORTAL, 3),
                         ProtossUnit(UnitTypeId.WARPPRISM, 1, priority=True)),
                    Step(UnitExists(UnitTypeId.ROBOTICSFACILITY, 1),
                         ProtossUnit(UnitTypeId.IMMORTAL, 20, priority=True)),
                    Step(UnitExists(UnitTypeId.ROBOTICSFACILITY, 1), ProtossUnit(UnitTypeId.ZEALOT, 7),
                         skip=UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1)),
                    Step(UnitExists(UnitTypeId.IMMORTAL, 1), GateUnit()),

                ]),
            SequentialList([
                ChronoTech(AbilityId.RESEARCH_WARPGATE, UnitTypeId.CYBERNETICSCORE),
                ChronoUnit(UnitTypeId.IMMORTAL, UnitTypeId.ROBOTICSFACILITY),
                Step(UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1), ChronoAnyTech(0),
                     skip=UnitExists(UnitTypeId.IMMORTAL, 3)),
            ]),
            SequentialList([
                # Stop Defending when attacking, i.e. Base-Trade
                Step(None, PlanZoneDefense(), skip=TechReady(UpgradeId.CHARGE, 0.9)),
                PlanZoneGather(),
                Step(TechReady(UpgradeId.CHARGE, 0.9), attack),
                PlanFinishEnemy(),
            ])
        ])

    def defend_dt(self) -> ActBase:
        print(f"Flexbot Build Order defend_dt")
        #TODO: Proxy-Pylon for DTs only, Follow-Up
        #TODO: Give DTs something to do if everything is dead near them
        pylon_pos = self.game_info.map_center.position
        defensive_position1 = self.main_base_ramp.top_center.towards(self.main_base_ramp.bottom_center, -4)
        defensive_position2 = self.main_base_ramp.top_center.towards(self.main_base_ramp.bottom_center, -5)
        attack = PlanZoneAttack(10)
        attack.retreat_multiplier = 0.5  # All in
        attack.enemy_power_multiplier = 0.7  # Attack even if it might be a bad idea
        return BuildOrder([
            SequentialList([
                GridBuilding(UnitTypeId.FORGE, 1),
                BuildOrder(
                    [
                        Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1),
                             BuildPosition(UnitTypeId.SHIELDBATTERY, defensive_position1, exact=False, only_once=True)),
                        Tech(UpgradeId.WARPGATERESEARCH, UnitTypeId.CYBERNETICSCORE),
                        ProtossUnit(UnitTypeId.STALKER, 1),
                    ]),
                Step(UnitExists(UnitTypeId.FORGE, 1),
                     BuildPosition(UnitTypeId.PHOTONCANNON, defensive_position1, exact=False, only_once=True)),
                Step(UnitExists(UnitTypeId.FORGE, 1),
                     BuildPosition(UnitTypeId.PHOTONCANNON, defensive_position2, exact=False, only_once=True)),
                Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1), GridBuilding(UnitTypeId.TWILIGHTCOUNCIL, 1)),
                Step(None, ProtossUnit(UnitTypeId.SENTRY, 1), skip=UnitExists(UnitTypeId.DARKSHRINE, 1)),
                GridBuilding(UnitTypeId.PYLON, 3),
                GridBuilding(UnitTypeId.GATEWAY, 2),
                Step(UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1), GridBuilding(UnitTypeId.DARKSHRINE, 1)),
                BuildOrder(
                    [
                        Step(None, ProtossUnit(UnitTypeId.SENTRY, 2), skip=UnitExists(UnitTypeId.DARKSHRINE, 1)),
                        Step(None, ProtossUnit(UnitTypeId.ZEALOT, 3), skip=UnitExists(UnitTypeId.DARKSHRINE, 1)),
                        GridBuilding(UnitTypeId.GATEWAY, 3),
                        SequentialList([
                            Step(UnitExists(UnitTypeId.SENTRY, 1), HallucinatedPhoenixScout()),
                            Step(UnitExists(UnitTypeId.SENTRY, 1), PlanHallucination()),
                        ])
                    ]),
            ]),
            [
                AutoPylon(),
                Step(UnitExists(UnitTypeId.DARKSHRINE, 1), ProtossUnit(UnitTypeId.DARKTEMPLAR, 3, priority=True),
                     skip_until=UnitExists(UnitTypeId.DARKSHRINE, 1), skip=(UnitExists(UnitTypeId.DARKTEMPLAR, 1) or UnitExists(UnitTypeId.ARCHON, 1))),
                Step(UnitExists(UnitTypeId.DARKSHRINE, 1), GateUnit()),
                Step(UnitExists(UnitTypeId.DARKSHRINE, 1), ProtossUnit(UnitTypeId.SENTRY, 5)),
            ],
            SequentialList([
                Step(UnitExists(UnitTypeId.DARKTEMPLAR, 1), Tech(UpgradeId.CHARGE, UnitTypeId.TWILIGHTCOUNCIL)),
                Step(UnitExists(UnitTypeId.DARKTEMPLAR, 1), Tech(UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1, UnitTypeId.FORGE)),
                Step(TechReady(UpgradeId.CHARGE, 0.1),
                     BuildPosition(UnitTypeId.PYLON, pylon_pos, exact=False, only_once=True))
            ]),
            SequentialList([
                ChronoTech(AbilityId.RESEARCH_WARPGATE, UnitTypeId.CYBERNETICSCORE),
                ChronoUnit(UnitTypeId.STALKER, UnitTypeId.GATEWAY),
                ChronoAnyTech(0)
            ]),
            SequentialList([
                PlanZoneDefense(),
                Step(None, PlanZoneGather(), skip=UnitExists(UnitTypeId.DARKSHRINE, 1)),
                Step(UnitExists(UnitTypeId.DARKSHRINE, 1), Dt_Harass()), # skip=TechReady(UpgradeId.CHARGE)),
                Step(TechReady(UpgradeId.CHARGE, 0.8), PlanZoneGather()),
                Step(TechReady(UpgradeId.CHARGE), attack),
                PlanFinishEnemy(),
            ])
        ])

    def skytoss(self) -> ActBase:
        print(f"Flexbot Build Order skytoss")
        #TODO: Follow-up
        #TODO: Don't suicide the Oracle if there are units already waiting
        #TODO: Strange freezing of Units and Groups after the first attack
        #TODO: Switch to Tempests/Carrier and see how they perform
        natural_pylon_pos = self.zone_manager.expansion_zones[1].mineral_line_center.towards(
                self.zone_manager.expansion_zones[1].behind_mineral_position_center, -12)

        attack = PlanZoneAttack(12)
        attack.enemy_power_multiplier = 0.8  # Attack even if it might be a bad idea
        return BuildOrder([
            SequentialList([
                Expand(2),
                ProtossUnit(UnitTypeId.STALKER, 1),
                BuildPosition(UnitTypeId.PYLON, natural_pylon_pos, exact=False, only_once=True),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 24)),
                GridBuilding(UnitTypeId.STARGATE, 1),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 25)),
                Step(None, ProtossUnit(UnitTypeId.SENTRY, 1), skip=UnitExists(UnitTypeId.TEMPEST, 1)),
                BuildPosition(UnitTypeId.SHIELDBATTERY, natural_pylon_pos, exact=False, only_once=True),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 26)),
                ProtossUnit(UnitTypeId.ZEALOT, 2),
                BuildOrder(
                    [
                        Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 28)),
                        SequentialList([
                            Step(UnitExists(UnitTypeId.SENTRY, 1), HallucinatedPhoenixScout()),
                            Step(UnitExists(UnitTypeId.SENTRY, 1), PlanHallucination()),
                        ])
                    ]),
                Step(UnitExists(UnitTypeId.STARGATE, 1), GridBuilding(UnitTypeId.FLEETBEACON, 1)),
                Tech(UpgradeId.WARPGATERESEARCH, UnitTypeId.CYBERNETICSCORE),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 30)),
                ProtossUnit(UnitTypeId.ZEALOT, 3),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 32)),
                Step(UnitExists(UnitTypeId.FLEETBEACON, 1), ProtossUnit(UnitTypeId.TEMPEST, 1)),
                StepBuildGas(3),
                ProtossUnit(UnitTypeId.ZEALOT, 4),
                Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1), GridBuilding(UnitTypeId.TWILIGHTCOUNCIL, 1)),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 34)),
                Step(UnitExists(UnitTypeId.STARGATE, 1), ProtossUnit(UnitTypeId.TEMPEST, 2)),
                StepBuildGas(4),
                GridBuilding(UnitTypeId.STARGATE, 2),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 36)),
                Step(UnitExists(UnitTypeId.TEMPEST, 1), Tech(UpgradeId.PROTOSSAIRWEAPONSLEVEL1, UnitTypeId.CYBERNETICSCORE)),
                ProtossUnit(UnitTypeId.ZEALOT, 5),
                Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 38)),
                Step(UnitExists(UnitTypeId.STARGATE, 1), ProtossUnit(UnitTypeId.TEMPEST, 3)),
                Step(UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1), Tech(UpgradeId.CHARGE, UnitTypeId.TWILIGHTCOUNCIL)),
                GridBuilding(UnitTypeId.GATEWAY, 2),
                Step(Minerals(500), GridBuilding(UnitTypeId.GATEWAY, 3)),

            ]),
            BuildOrder(
                [
                    Step(UnitExists(UnitTypeId.NEXUS, 2), AutoPylon()),
                    Step(UnitExists(UnitTypeId.NEXUS, 2), ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 44)),
                    Step(UnitExists(UnitTypeId.TEMPEST, 1), ProtossUnit(UnitTypeId.TEMPEST, 20, priority=True)),
                    Step(UnitExists(UnitTypeId.STARGATE, 2), ProtossUnit(UnitTypeId.ZEALOT, 50)),
                    Step(TechReady(UpgradeId.PROTOSSAIRWEAPONSLEVEL1),
                         Tech(UpgradeId.PROTOSSAIRWEAPONSLEVEL2, UnitTypeId.CYBERNETICSCORE)),
                    Step(TechReady(UpgradeId.PROTOSSAIRWEAPONSLEVEL2),
                         Tech(UpgradeId.PROTOSSAIRWEAPONSLEVEL3, UnitTypeId.CYBERNETICSCORE)),
                ]),
            SequentialList([
                ChronoUnit(UnitTypeId.STALKER, UnitTypeId.GATEWAY),
                ChronoUnit(UnitTypeId.TEMPEST, UnitTypeId.STARGATE),
                ChronoAnyTech(0)
            ]),
            SequentialList([
                PlanZoneDefense(),
                PlanZoneGather(),
                # Step(UnitExists(UnitTypeId.ORACLE, 1), Oracle_Harass()),
                Step(TechReady(UpgradeId.PROTOSSAIRWEAPONSLEVEL1, 0.9), attack),
                PlanFinishEnemy(),
            ])
        ])

    def two_base_stalker(self) -> ActBase:
        print(f"Flexbot Build Order two_base_stalker")
        #TODO: Adapt Unit Composition, Improve Timings, Hallu-Phoenix-Scout
        natural = self.zone_manager.expansion_zones[-3]
        pylon_pos: Point2 = natural.behind_mineral_position_center
        return BuildOrder([
            SequentialList([
                Expand(2),
                BuildOrder(
                    [
                        AutoPylon(),
                        Tech(UpgradeId.WARPGATERESEARCH, UnitTypeId.CYBERNETICSCORE),
                        [
                            Step(UnitExists(UnitTypeId.NEXUS, 2),
                                 ActUnit(UnitTypeId.PROBE, UnitTypeId.NEXUS, 44)),
                            StepBuildGas(3, skip=Gas(300)),
                            StepBuildGas(4, skip=Gas(200)),
                        ],
                        [
                            Step(None, ProtossUnit(UnitTypeId.SENTRY, 1),
                                 skip_until=UnitExists(UnitTypeId.STALKER, 2, include_pending=True)),
                            Step(None, ProtossUnit(UnitTypeId.SENTRY, 2),
                                 skip_until=UnitExists(UnitTypeId.STALKER, 6, include_pending=True)),
                            Step(None, ProtossUnit(UnitTypeId.STALKER, 100)),
                        ],
                        [
                            Step(UnitExists(UnitTypeId.GATEWAY, 3),
                                 BuildPosition(UnitTypeId.PYLON, pylon_pos, exact=False, only_once=True))
                        ],
                        SequentialList([
                            GridBuilding(UnitTypeId.GATEWAY, 4),
                            Step(UnitExists(UnitTypeId.CYBERNETICSCORE, 1),
                                 GridBuilding(UnitTypeId.TWILIGHTCOUNCIL, 1)),
                            GridBuilding(UnitTypeId.GATEWAY, 6),
                            Step(UnitExists(UnitTypeId.TWILIGHTCOUNCIL, 1),
                                 Tech(UpgradeId.BLINKTECH, UnitTypeId.TWILIGHTCOUNCIL)),
                            GridBuilding(UnitTypeId.GATEWAY, 7),
                        ]),

                    ])
            ]),
            SequentialList([
                ChronoTech(AbilityId.RESEARCH_WARPGATE, UnitTypeId.CYBERNETICSCORE),
                ChronoTech(AbilityId.RESEARCH_BLINK, UnitTypeId.TWILIGHTCOUNCIL),
                ChronoUnit(UnitTypeId.STALKER, UnitTypeId.GATEWAY),
            ]),
            SequentialList([
                Step(UnitExists(UnitTypeId.GATEWAY, 4), PlanZoneGather()),
                Step(UnitExists(UnitTypeId.STALKER, 4), PlanZoneAttack(12)),
                PlanFinishEnemy(),
            ])
        ])


class LadderBot(FlexBot):
    @property
    def my_race(self):
        return Race.Protoss
