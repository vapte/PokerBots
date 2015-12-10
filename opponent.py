from playerclass import * 
from db import *


#Player will have a list of Opponent instances
class Opponent(Player):
    def __init__(self, name, playerDict):
        super().__init__(name)
        self.histories = playerDict['histories'][self.name]

    #update attributes on each packet
    def attrsUpdate(self,playerDict):
        self.histories = {self.name: playerDict['histories'][self.name]}
        self.numHands = playerDict['numHands']