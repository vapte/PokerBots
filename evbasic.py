#evbasic

from playerclass import *

class EvBasic(Player):
    def __init__(self,name):
        super().__init__(name)
        self.type = 'evbasic'

    def botLogic(self):
        super().botLogic()
        actionsDict = self.actionsParse()
        if actionsDict.get('check',False):
            return ('check', 0)
        elif actionsDict.get('fold',False):
            if self.EV>0 and actionsDict.get('raise',False):
                maxRaiseIndex = len(actionsDict['raiseVals'])-1
                if self.EV>0.2:
                    specRaise = maxRaiseIndex//2
                try:
                    return ('raise',actionsDict['raiseVals'][specRaise])    #test value
                except:
                    #sometime we don't set a raise value
                    if self.EV>0.1:
                        return ('call', actionsDict['callVals'])
                    return ('fold',0)
            else:
                return ('fold',0)