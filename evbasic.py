#evbasic

from playerclass import *
from db import *

class EvBasic(Player):
    def __init__(self,name):
        super().__init__(name)
        self.type = 'evbasic'

    #bot control function
    def botLogic(self):
        super().botLogic()
        shouldReturn  = None
        actionsDict = self.actionsParse()
        if actionsDict.get('check',False):
            shouldReturn =  ('check', 0)
        elif actionsDict.get('fold',False):
            if self.EV>0 and actionsDict.get('raise',False):
                maxRaiseIndex = len(actionsDict['raiseVals'])-1
                if self.EV>0.2:
                    specRaise = maxRaiseIndex//2
                try:
                    shouldReturn = ('raise',actionsDict['raiseVals'][specRaise])    
                except:
                    #sometime we don't set a raise value
                    if self.EV>0.1:
                        shouldReturn =  ('call', actionsDict['callVals'])
                    shouldReturn =  ('fold',0)
            else:
                shouldReturn =  ('fold',0)
        return self.checkReturnVal(shouldReturn, actionsDict)