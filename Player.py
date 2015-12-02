import argparse
import socket
import sys
import itertools as it 
import random
import copy
from numpy.random import logistic
import os

#The skeleton for this bot is from the MIT PokerBots course website 
#The skeleton code defined Player, run, and 'if __name__ == '__main__':" 


class Player(object):
    values = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'] #ordered lo to hi
    handOrder = ['highcard', '1pair', '2pair', '3ofakind', 'straight', 
    'flush', 'fullhouse', '4ofakind', 'straightflush'] #lo to hi
    valuesStr = ''.join(values)
    suits = ['d','c','s','h']
    fullDeck = list(it.product(values,suits))
    for i in range(len(fullDeck)):
        hand = fullDeck[i]
        fullDeck[i] = hand[0]+hand[1] #tuple>>str
    assert(len(fullDeck)==52)

    def __init__(self,name):    #must set name to name in config.txt
        self.hole = []
        self.board = []
        self.potSize = 0
        self.actions = []
        self.playerNames = []
        self.histories = dict()
        self.stackSizes = []
        self.potOdds = 0
        self.blind = Player.getBlind()
        self.blindsLeft = 0
        self.EV = 0
        self.impliedEV = 0
        self.AF = 0       
        self.AFtype = None
        self.name = name
        self.stack = 0
        self.opponents = dict()
        self.numHands = 0
        self.winRate = 0
        #index in histories where all entries with index>self.flop are post-flop
        self.flop = 0
        self.gameState = None
        self.impliedPotOdds = 0

    def run(self, inputSocket):

        #game separator
        print([[0 for i in range(30)] for j in range(30)])
        

        # Get a file-object for reading packets from the socket.
        # Using this ensures that you get exactly one packet per read.
        f_in = inputSocket.makefile()
        while True:
            # Block until the engine sends us a packet.
            data = f_in.readline().strip()
            # If data is None, connection has closed.
            if not data:
                print("Gameover, engine disconnected.")
                break
            # Here is where you should implement code to parse the packets from
            # the engine and act on it. We are just printing it instead.

            packetValues = data.split(' ')
            print(packetValues,'\n\n')
                

            # When appropriate, reply to the engine with a legal action.
            # The engine will ignore all spurious responses.
            # The engine will also check/fold for you if you return an
            # illegal action.
            # When sending responses, terminate each response with a newline
            # character (\n) or your bot will hang!


            word = packetValues[0]

            if word=='NEWHAND':
                self.hole = [packetValues[3],packetValues[4]]
                self.playerNames = []
                for piece in packetValues[5:-5]:
                    if not piece.isdigit():
                        self.playerNames+=[piece]

                #need to initialize histories/opponents on first hand
                if self.histories == {}:
                    for player in self.playerNames:
                        self.histories[player] = []
                    assert(len(self.playerNames)<=3) #engine allows 3 players max
                if self.opponents == {}:
                    for player in self.playerNames:
                        if player!=self.name:
                            self.opponents[player] = Opponent(player,vars(bot))

                self.numHands+=1

                self.gameState = 'preflop'

            elif word == "GETACTION":

                #get player actions
                self.actions = packetValues[-4:-1]
                if self.actions[0].isdigit():
                    self.actions.pop(0)

                #update potSize, board, stacksizes
                self.potSize = int(packetValues[1])
                numCards = int(packetValues[2])
                if numCards > 0:
                    self.board = packetValues[3:3+numCards]
                self.stackSizes = packetValues[3+numCards:6+numCards] 


                #compute pot odds
                for action in self.actions:
                    if "CALL" in action:
                        callSize = int(action.split(':')[1])
                self.potOdds = callSize/self.potSize


                #run logic and send message
                rawBotResponse = self.botLogic()
                if rawBotResponse!=None:
                    response = Player.botResponse(rawBotResponse)
                else:
                    response = Player.botResponse()
                s.send(response)

            elif word == 'HANDOVER':
                self.stackSizes = packetValues[1:4]


            elif word == "REQUESTKEYVALUES":
                # At the end, the engine will allow your bot save key/value pairs.
                # Send FINISH to indicate you're done.
                s.send(b"FINISH\n")

            #update histories and stats
            if word == "GETACTION" or word=="HANDOVER":

                
                #gameState, self.flop
                for event in packetValues:
                    if 'FLOP' in event:
                        self.gameState = 'flop'
                        self.flop = len(self.histories)
                        for opponent in self.opponents:
                            currOpp = self.opponents[opponent]
                            currOpp.flop = len(currOpp.histories)
                    elif 'TURN' in event:
                        self.gameState = 'turn'
                    elif 'RIVER' in event:
                        self.gameState = 'river'

                self.historyUpdate(packetValues)

            if self.histories!={}:

                self.statUpdate()

                #opponent attributes update
                for opponent in self.opponents:
                    currOpp = self.opponents[opponent]
                    currOpp.attrsUpdate(vars(bot))

                #opponent stats update
                self.oppUpdate()

                #print('READOUT',vars(bot),'\n\n')
                varsBotCopy = copy.deepcopy(vars(bot))
                varsBotCopy.pop('histories')
                print('SNAPSHOT',varsBotCopy)


        # Clean up the socket.
        s.close()

    def botLogic(self): #top level function for bot logic
        pass

    #override in subclasses 
    #should return (action, quantity)
    #actions = 'check','fold','bet','raise','call'
    #quantity is needed for all (0 if check or fold)

    def actionsParse(self): #parses self.actions
        check = fold = False
        actionsDict = dict()
        minRaise = maxRaise = minBet = maxBet = callSize = None

        for value in self.actions:
            if 'RAISE' in value:
                minRaise = int(value.split(':')[1])
                maxRaise = int(value.split(':')[2])
            elif 'BET' in value:
                minBet = int(value.split(':')[1])
                maxBet = int(value.split(':')[2])
            elif 'CALL' in value:
                callSize = int(value.split(':')[1])
            elif 'CHECK' in value:
                check = True
            elif 'FOLD' in value:
                fold = True

        if minBet!=None and maxBet!=None: 
            actionsDict['bet']=True
            actionsDict['betVals'] = list(range(minBet,maxBet+1))
        if minRaise!=None and maxRaise!=None:
            actionsDict['raiseVals'] = list(range(minRaise,maxRaise+1))
            actionsDict['raise'] = True
        if callSize!=None:
            actionsDict['callVals'] = callSize
            actionsDict['call'] = True
        if check:
            actionsDict['check'] = True
        if fold:
            actionsDict['fold'] = True

        return actionsDict

    @classmethod
    def botResponse(self, logicTuple = ('check',0)):  #formats output of botLogic
        possibleActions = ['check','fold','bet','raise','call']
        responseType = logicTuple[0]
        quantity = logicTuple[1]
        assert(responseType in possibleActions)
        if responseType=='check' or responseType=='fold':
            response = str.encode(responseType.upper()+'\n')
        else:
            response = str.encode(responseType.upper()+':'+str(quantity)+'\n')
        return response

    #manage opponent data
    def oppUpdate(self):
        #self.opponents initialized in run()
        for opponent in self.opponents:
            currOpp = self.opponents[opponent]
            if currOpp.name!=self.name:
                currOpp.statUpdate()
                varsOppCopy = copy.deepcopy(vars(currOpp))
                varsOppCopy.pop('histories')
                print(currOpp.name, '\n', varsOppCopy,'\n\n')

    #top level function for computing all stats
    def statUpdate(self):
        self.getAggressionFactor()
        self.getExpectedValue()
        self.getWinRate()
        self.getImpliedPotOdds()
        try:
            self.stack = int(self.stackSizes[self.playerNames.index(self.name)])
        except:
            pass
        
        self.blindsLeft  = int(self.stack/self.blind)

    #stat/history computation functions (must work for opponents with only histories as input)

    #implied  pot odds

    def getImpliedPotOdds(self):
        impliedPot = self.potSize
        for action in self.actions:
            if "CALL" in action:
                callSize = int(action.split(':')[1])
            elif "RAISE" in action or "BET" in action:
                minRaise = int(action.split(':')[1])
                maxRaise = int(action.split(':')[2])+minRaise #if we raise
                enumRaises = list(range(minRaise,maxRaise+1))
        try:
            #enumRaises = [0]+[callSize]+enumRaises  fold,call,raise
            #we shift 0->callSize-1 because statistics
            enumRaises = [callSize-1]+[callSize]+enumRaises

        except:
            pass

        try:
            if len(enumRaises)>1: #not just callSize-1
                expectedActions = dict()
                for opponent in self.opponents:
                    currOpp = self.opponents[opponent]
                    randomAction  = 0 
                    samples = 1000
                    for i in range(samples):
                        #scale chosen by inspection
                        randomAction +=int(abs(logistic(currOpp.AF*maxRaise,1)))
                    randomAction /= samples
                    expectedActions[currOpp.name] = Player.closestInt(enumRaises,randomAction)
                for oppAction in expectedActions:
                    if expectedActions[oppAction]==callSize-1:
                        continue
                    else:
                        impliedPot+=expectedActions[oppAction]
                self.impliedPotOdds = callSize/impliedPot
            else:
                pass
        except:
            #no CALL or RAISE in histories
            pass

    @staticmethod
    def closestInt(L,num):
        minDiff = currDiff = None
        minElem = None
        for i in range(len(L)):
            currDiff = abs(L[i]-num)
            if minDiff == None: minDiff=currDiff
            if currDiff<=minDiff: #break ties downwards
                minDiff = currDiff
                minElem = L[i]
        return minElem

    def getWinRate(self):
        wins = 0
        for event in self.histories[self.name]:
            if "WIN" in event and self.name in event:
                wins+=1
        self.winRate = wins/self.numHands

    def getExpectedValue(self):
        if len(self.hole+self.board)<=6:
            outProb = Player.monteCarloTest(self.hole+self.board, True)
            self.EV =  outProb-self.potOdds
            self.impliedEV  = outProb-self.impliedPotOdds

    def historyUpdate(self, packetValues):
        for value in packetValues:
            if value.count(':')==2: #all prior actions have 2 colons
                for player in self.playerNames:
                    if player in value:
                        self.histories[player].append(value)

    '''
    AF benchmark values: 
    http://poker.gamblefaces.com/understanding-hud/post-flop-aggression-factor/

AF Value       Category

0<AF<1         Passive
1<AF<1.5       Neutral
AF>1.5        Aggressive

    '''
    def getAggressionFactor(self):
        #set both to 1 b/c divide by zero
        downs = 1 #calls or folds
        ups = 1 #bets or raises
        for event in self.histories[self.name]:
            if 'CALL' in event: #or 'FOLD' in event:
                downs+=1
            elif 'BET' in event or 'RAISE' in event:
                ups+=1
        self.AF = ups/downs
        if self.AF<1:
            self.AFtype = 'passive'
        elif self.AF>=1 and self.AF<1.5:
            self.AFtype = 'neutral'
        elif self.AF>=1.5:
            self.AFtype = 'aggressive'


    #class/static methods

    @staticmethod
    def readFile(path):
        with open(path, "rt") as f:
            return f.read()

    #get blind size from config.txt
    @classmethod
    def getBlind(self):
        path = os.getcwd()
        config = Player.readFile(path+os.sep+'config.txt')
        return int(config.split('\n')[0][-1])


    @classmethod
    def bestHand(Player,cards):
        #call this function post-flop and on turn to compute best hand
 
        #get unordered 5-tuples from allCards
        hands = list(it.combinations(cards,5)) #list of tuples
        best = 0    #power of best hand 
        for hand in hands:
            result = Player.checkHandType(hand)
            if result[1]>=best:
                best=result[1]
        return best

    @classmethod
    def monteCarloTest(Player,allCards,returnProb = False):
        #runs Monte Carlo sim to get average best hand if cards are added
        #to community

        simNum = 100
        simCount = 0
        cumePower = 0
        adjustedFullDeck = copy.copy(Player.fullDeck) 

        assert(len(allCards)<=6) 

        if returnProb:
            beatCount = 0
            currBest = Player.bestHand(allCards)

        #removing hole cards
        for card in adjustedFullDeck:
            if card in allCards:
                adjustedFullDeck.remove(card)
        initAdjustedFullDeck = copy.copy(adjustedFullDeck)

        while simCount<=simNum:
            adjustedFullDeck = copy.copy(initAdjustedFullDeck)
            currCards = copy.copy(allCards)
            if len(allCards)<=6:    #river
                nextCard = random.choice(adjustedFullDeck)
                currCards+=[nextCard]
                adjustedFullDeck.remove(nextCard)
                if len(allCards)<=5:  #turn
                    nextCard2 = random.choice(adjustedFullDeck)
                    currCards+=[nextCard2]
                    adjustedFullDeck.remove(nextCard2)
                    if len(allCards)==2: #flop
                        nextCard3 = random.choice(adjustedFullDeck)
                        currCards+=[nextCard3]
            if Player.bestHand(currCards)>currBest:
                beatCount+=1
            cumePower+=Player.bestHand(currCards)
            simCount+=1
        if returnProb:
            return beatCount/simNum #probabilty of getting a better hand than currBest
        else:
            return cumePower/simNum
    
    @classmethod
    def powerRatio(Player,allCards):
        currBest = Player.bestHand(allCards)
        predictedBest = Player.monteCarloTest(allCards)
        #my own definition of pot odds
        return predictedBest/currBest


    @classmethod
    def checkHandType(Player,hand):
        #returns hand type, as well as power index
        def highFreq(handStr):
            uniques = list(set(handStr))
            maxFreq = 0
            for i in uniques:
                if handStr.count(i)>maxFreq:
                    maxFreq=handStr.count(i)
            return maxFreq
        def twoPair(hand,handStrVals):
            valList = list(set(handStrVals))
            counts = []
            for i in counts:
                counts+=handStrVals.count(i)
            if sorted(counts)==[1,2,2]:
                return True
        assert(len(hand)==5)    #texas hold'em hands have 5 cards
        handStr = ''.join(hand)
        handStrVals = ''.join(sorted([x[:-1] for x in hand])) #just values
        handStrSuits = ''.join([x[-1] for x in hand]) #just suits

        #royal flush
        if handStrVals in Player.valuesStr and len(set(handStrSuits))==1:
            handType = 'straightflush' #royal flush is just straight flush with maxPower
        elif highFreq(handStrVals)==4:
            handType = '4ofakind'
        elif len(set(handStrVals))==2:
            handType = 'fullhouse'
        elif len(set(handStrSuits))==1:
            handType = 'flush'  #doesn't conflict with straight flush b/c elif
        elif handStrVals in Player.valuesStr:
            handType = 'straight'
        elif highFreq(handStrVals)==3:
            handType = '3ofakind'
        elif twoPair(hand,handStrVals):
            handType = '2pair'
        elif highFreq(handStrVals)==2:
            handType =  '1pair'
        else:
            handType =  'highcard'

        #particular power within hand family
        #subPower =  handPower(hand,handStrVals,handType)
        return (handType, Player.handOrder.index(handType)+1)
        #offset handOrder.index(handType) by 1 because list index starts at 0


#Player will have a list of Opponent instances
class Opponent(Player):
    def __init__(self, name, playerDict):
        super().__init__(name)
        self.histories = playerDict['histories'][self.name]

    #update attributes on each packet
    def attrsUpdate(self,playerDict):
        self.histories = {self.name: playerDict['histories'][self.name]}
        self.numHands = playerDict['numHands']



#AF Exploit Bot
#   exploits AF of other bots conditional on implied EV premium 
#   checks all to get data on other players
class AfExploit(Player):
    def __init__(self, name):
        super().__init__(name)

    def botLogic(self):
        super().botLogic()
        actionsDict = self.actionsParse()
        if actionsDict.get('check',False):
            return ('check', 0)
        elif actionsDict.get('fold',False):
            if self.impliedEV<0 and self.EV<0:
                return ('fold',0)
            elif self.impliedEV>0 and self.EV<0 and actionsDict.get('fold',False):
                return ('fold',0)
            elif self.impliedEV>0 and self.EV>0 and actionsDict.get('raise',False):
                return ('raise',actionsDict['raiseVals'][len(actionsDict['raiseVals'])-1])    #test value


if __name__ == '__main__':
    #botTester
    def readFile(path):
        with open(path, "rt") as f:
            return f.read()

    def writeFile(path, contents):
        with open(path, "wt") as f:
            f.write(contents)

    def getBlind():
        path = os.getcwd()
        config = readFile(path+os.sep+'config.txt')
        return int(config.split('\n')[0][-1])

    def setHands(handNum):
        path = os.getcwd()
        fullPath = path+os.sep+'config.txt'
        config = readFile(fullPath)
        config = config.split('\n')
        handsIndex = 0
        stackIndex = 0
        for i in range(len(config)):
            line = config[i]
            if 'NUMBER_OF_HANDS' in line:
                handsIndex = i
            if 'STARTING_STACK' in line:
                stackIndex = i
        new = handNum*getBlind()
        newStackLine = ' STARTING_STACK = %s' % new
        newLine = ' NUMBER_OF_HANDS = %s' % handNum
        config[handsIndex] = newLine
        config[stackIndex] = newStackLine
        newConfig = '\n'.join(config)    
        writeFile(fullPath,newConfig)

    setHands(50)

    parser = argparse.ArgumentParser(description='A Pokerbot.', add_help=False, prog='pokerbot')
    parser.add_argument('-h', dest='host', type=str, default='localhost', help='Host to connect to, defaults to localhost')
    parser.add_argument('port', metavar='PORT', type=int, help='Port on host to connect to')
    args = parser.parse_args()

    # Create a socket connection to the engine.
    print('Connecting to %s:%d' % (args.host, args.port))
    try:
        s = socket.create_connection((args.host, args.port))
    except socket.error as e:
        print('Error connecting! Aborting')
        exit()




    bot = AfExploit('playa')
    bot.run(s)
