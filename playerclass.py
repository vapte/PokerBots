import itertools as it 
import random
import copy
from numpy.random import logistic
import os
import multiprocessing
import time
import tkinter 
import pickle
from db import *


#Skeleton code for Player obtained from MIT PokerBots course website 
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
        self.hole = self.board =  self.actions = self.playerNames = []
        self.potSize = 0
        self.histories = dict()
        self.stackSizes = self.allHistories = [] 
        self.potOdds = 0
        self.blind = Player.getBlind()
        self.blindsLeft = self.EV = self.impliedEV = 0
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
        # Get a file-object for reading packets from the socket.
        # Using this ensures that you get exactly one packet per read.
        f_in = inputSocket.makefile()
        while True:
            data = f_in.readline().strip() # Block until engine sends packet
            if not data: # If data is None, connection has closed.
                break
            packetValues = data.split(' ')
            db(self.name, data,'\n\n')
            word = packetValues[0]
            if word=='NEWHAND': 
                self.newHandUpdate(packetValues)
            elif word == "GETACTION":
                self.getActionUpdate(packetValues, inputSocket)
            elif word == 'HANDOVER':
                self.stackSizes = packetValues[1:4]
                self.historyUpdate(packetValues,True)
            elif word == "REQUESTKEYVALUES":
                inputSocket.send(b"FINISH\n")
            #update histories and stats
            if word == "GETACTION" or word=="HANDOVER":
                self.gameStateUpdate(packetValues)
            if self.histories!={}:
                self.allStats()
        # Clean up the socket.
        inputSocket.close()
        self.export()

    #EXPORT allHistories to text file
    def export(self):
        fileIndex = int(self.name[-1])+2
        Player.writeFile('filename%d.pickle' % fileIndex ,self.allHistories,True)

    #update stats and attributes for players and opponents
    def allStats(self):
        self.statUpdate()
        #opponent attributes update
        for opponent in self.opponents:
            currOpp = self.opponents[opponent]
            currOpp.attrsUpdate(self.__dict__)
        #opponent stats update
        self.oppUpdate()
        varsBotCopy = copy.deepcopy(self.__dict__)
        #varsBotCopy.pop('histories')
        db('SNAPSHOT',self.name, varsBotCopy,'\n\n')

    #update game state based on packet values
    def gameStateUpdate(self,packetValues):
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

    #gets and sends action through socket, updates game attributes
    def getActionUpdate(self,packetValues,inputSocket):
        self.historyUpdate(packetValues)
        #get player actions
        self.actions = packetValues[-4:-1]
        if self.actions[0].isdigit(): self.actions.pop(0)
        #update potSize, board, stacksizes
        self.potSize = int(packetValues[1])
        numCards = int(packetValues[2])
        if numCards > 0: self.board = packetValues[3:3+numCards]
        self.stackSizes = packetValues[3+numCards:6+numCards] 
        #compute pot odds
        for action in self.actions:
            if "CALL" in action: callSize = int(action.split(':')[1])
        try:
            self.potOdds = self.potSize/(callSize+self.potSize)
        except:
            self.potOdds = 1/len(self.playerNames)    #1/3 of the pot for 3 players
        #run logic and send message
        rawBotResponse = self.botLogic()
        if rawBotResponse!=None: response = Player.botResponse(rawBotResponse)
        else: response = Player.botResponse()
        inputSocket.send(response)

    #intiializes histories on first hand, resets board
    def newHandUpdate(self, packetValues):
        self.boardReset()
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
                    self.opponents[player] = Opponent(player,self.__dict__)
        self.numHands+=1
        self.gameState = 'preflop'

    #top level function for bot logic
    def botLogic(self): 
        pass

    #override in subclasses 
    #should return (action, quantity)
    #actions = 'check','fold','bet','raise','call'
    #quantity is needed for all (0 if check or fold)

    #makes sure players have integrity
    def checkReturnVal(self,shouldReturn, actionsDict):
        #sometimes the engine let's players spend more than they have...
        if shouldReturn[0] in ['call','bet','raise']:
            if shouldReturn[1]>self.stack:
                if actionsDict.get('check',False):
                    return ('check',0)
                else:
                    return ('fold',0)
            else:
                return shouldReturn
        else:
            return shouldReturn

    #parses self.actions
    def actionsParse(self): 
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
            elif 'CHECK' in value: check = True
            elif 'FOLD' in value: fold = True
        if minBet!=None and maxBet!=None: 
            actionsDict['bet']=True
            actionsDict['betVals'] = list(range(minBet,maxBet+1))
        if minRaise!=None and maxRaise!=None:
            actionsDict['raiseVals'] = list(range(minRaise,maxRaise+1))
            actionsDict['raise'] = True
        if callSize!=None:
            actionsDict['callVals'] = callSize
            actionsDict['call'] = True
        if check: actionsDict['check'] = True
        if fold: actionsDict['fold'] = True
        return actionsDict

    #formats output of botLogic
    @classmethod
    def botResponse(self, logicTuple = ('check',0)):  
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

    #top level function for computing all stats
    def statUpdate(self):
        self.getWinRate()
        self.getAggressionFactor()
        self.getImpliedPotOdds()
        self.getExpectedValue()
        try:
            self.stack = int(self.stackSizes[self.playerNames.index(self.name)])
        except:
            pass
        self.blindsLeft  = int(self.stack/self.blind)

    #implied  pot odds
    def getImpliedPotOdds(self):
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
                expectedActions, impliedPot = dict(), self.potSize
                for opponent in self.opponents:
                    currOpp = self.opponents[opponent]
                    randomAction , samples = 0 , 1000
                    for i in range(samples):
                        #scale chosen by inspection
                        randomAction +=int(abs(logistic(currOpp.AF*maxRaise,1)))
                    randomAction /= samples
                    p = Player.closestInt(enumRaises,randomAction)
                    expectedActions[currOpp.name] = p
                for oppAction in expectedActions:
                    if expectedActions[oppAction]==callSize-1:continue
                    else: impliedPot+=expectedActions[oppAction]
                self.impliedPotOdds = impliedPot/(callSize+impliedPot)
            else:pass
            #no CALL or RAISE in historie
        except: pass

    #finds element of list that is closest to given integer
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

    #calculates win rate
    def getWinRate(self):
        wins = 0
        for event in self.histories[self.name]:
            if ("WIN" in event or 'TIE' in event) and self.name in event:
                wins+=1
        self.winRate = wins/self.numHands

    #calulates expected value
    def getExpectedValue(self):
        if len(self.hole+self.board)<=6:
            outProb = Player.monteCarloTest(self.hole+self.board, True)
            self.EV =  outProb*self.potOdds
            self.impliedEV  = outProb*self.impliedPotOdds
            db(outProb,'ev',self.EV,'implied',self.impliedEV,self.potOdds,
                self.impliedPotOdds,'\n\n')

    #resets board to back of cards
    def boardReset(self):
        self.allHistories.append((['back']*5,time.time()))        

    #updates histories for player, adds to allHistories
    def historyUpdate(self, packetValues, handOver=False):
        if not handOver:
            for value in packetValues:
                if value.count(':')==2: #raise,bets,calls have 2 colons
                    for player in self.playerNames:
                        if player in value:
                            self.histories[player].append(value)
        elif handOver:
            river = []
            for value in packetValues:
                #only needs to compute winrate for self
                if ('WIN' in value or 'TIE' in value) and self.name in value:
                    self.histories[self.name].append(value)
                elif len(value)==2:
                    if value[0] in Player.values and value[1] in Player.suits:
                        river.append(value)
            self.allHistories.append((river,time.time()))
            self.allHistoriesUpdate(packetValues)
        
    #updates allHistories
    def allHistoriesUpdate(self,packetValues):
        #repeats in board, potsize, and playerinfo are fine
        self.allHistories.append((self.board,time.time()))
        self.allHistories.append((['pot',self.potSize],time.time()))
        db('historyUpdate check', self.name, self.hole)
        self.allHistories.append(([self.name,self.hole,self.stack],time.time()))
        if self.name=='player1':
            for value in packetValues:
                if ':' in value and 'player' in value:
                    self.allHistories.append((value,time.time()))  #no repeats 
        db(self.allHistories,'\n\n')

    '''
    AF benchmark values: 
    http://poker.gamblefaces.com/understanding-hud/post-flop-aggression-factor/
AF Value       Category
0<AF<1         Passive
1<AF<1.5       Neutral
AF>1.5        Aggressive
    '''
    #computes aggression factor
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

    #withPickle parameter on readFile and writeFile writes to pickle object
    #instead of text file

    @staticmethod
    def readFile(path, withPickle = False):
        if withPickle:
            with open(path, "rb") as f:
                return pickle.load(f)
        else:
            with open(path, "rt") as f:
                return f.read()

    @staticmethod
    def writeFile(path, contents, withPickle = False):
        if withPickle:
            with open(path, "wb") as f:
                    pickle.dump(contents,f)
        else:
            with open(path, "wt") as f:
                f.write(contents)


    #get blind size from config.txt
    @classmethod
    def getBlind(self):
        path = os.getcwd()
        config = Player.readFile(path+os.sep+'config.txt')
        return int(config.split('\n')[0][-1])

    #call this function post-flop and on turn to compute best hand
    @classmethod
    def bestHand(Player,cards):
        #get unordered 5-tuples from allCards
        hands = list(it.combinations(cards,5)) #list of tuples
        best = 0    #power of best hand 
        for hand in hands:
            result = Player.checkHandType(hand)
            if result[1]>=best:
                best=result[1]
        return best

    #runs Monte Carlo sim to get average best hand if cards are added
    #to community
    @classmethod
    def monteCarloTest(Player,allCards,returnProb = False):
        simNum,simCount,cumePower = 100,0,0
        adjustedFullDeck = copy.copy(Player.fullDeck) 
        if returnProb: beatCount,currBest = 0,Player.bestHand(allCards)
        #removing hole cards
        for card in adjustedFullDeck: #remove hole/board cards
            if card in allCards: adjustedFullDeck.remove(card)
        initAdjustedFullDeck = copy.copy(adjustedFullDeck)
        while simCount<=simNum:
            adjustedFullDeck = copy.copy(initAdjustedFullDeck)
            currCards = copy.copy(allCards)
            if len(allCards)<=6:    #river
                nextCard = random.choice(adjustedFullDeck)  #pull random card
                currCards+=[nextCard]
                adjustedFullDeck.remove(nextCard)
                if len(allCards)<=5:  #turn
                    nextCard2 = random.choice(adjustedFullDeck)
                    currCards+=[nextCard2]
                    adjustedFullDeck.remove(nextCard2)
                    if len(allCards)==2: #flop
                        nextCard3 = random.choice(adjustedFullDeck)
                        currCards+=[nextCard3]
            if Player.bestHand(currCards)>currBest: beatCount+=1
            cumePower+=Player.bestHand(currCards)
            simCount+=1
        if returnProb: return beatCount/simNum #probabilty of better hand
        else:return cumePower/simNum
    
    #computes hand odds ratio
    @classmethod
    def powerRatio(Player,allCards):
        currBest = Player.bestHand(allCards)
        predictedBest = Player.monteCarloTest(allCards)
        return predictedBest/currBest
        
    #returns hand type, as well as power index
    @classmethod
    def checkHandType(Player,hand):
        assert(len(hand)==5)    #texas hold'em hands have 5 cards
        handStr = ''.join(hand)
        handStrVals = ''.join(sorted([x[:-1] for x in hand])) #just values
        handStrSuits = ''.join([x[-1] for x in hand]) #just suits
        if handStrVals in Player.valuesStr and len(set(handStrSuits))==1:
            handType = 'straightflush' 
        elif Player.highFreq(handStrVals)==4:
            handType = '4ofakind'
        elif len(set(handStrVals))==2:
            handType = 'fullhouse'
        elif len(set(handStrSuits))==1:
            handType = 'flush'  #doesn't conflict with straight flush b/c elif
        elif handStrVals in Player.valuesStr:
            handType = 'straight'
        elif Player.highFreq(handStrVals)==3:
            handType = '3ofakind'
        elif Player.twoPair(hand,handStrVals):
            handType = '2pair'
        elif Player.highFreq(handStrVals)==2:
            handType =  '1pair'
        else:
            handType =  'highcard'
        return (handType, Player.handOrder.index(handType)+1)

    @classmethod
    def highFreq(Player, handStr):
            uniques = list(set(handStr))
            maxFreq = 0
            for i in uniques:
                if handStr.count(i)>maxFreq:
                    maxFreq=handStr.count(i)
            return maxFreq

    @classmethod
    def twoPair(Player, hand,handStrVals):
        valList = list(set(handStrVals))
        counts = []
        for i in valList:
            counts+=[handStrVals.count(i)]
        if sorted(counts)==[1,2,2]:
            return True


#Player will have a list of Opponent instances
class Opponent(Player):
    def __init__(self, name, playerDict):
        super().__init__(name)
        self.histories = playerDict['histories'][self.name]

    #update attributes on each packet
    def attrsUpdate(self,playerDict):
        self.histories = {self.name: playerDict['histories'][self.name]}
        self.numHands = playerDict['numHands']