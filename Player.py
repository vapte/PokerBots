import argparse
import socket
import sys
import itertools as it 
import random
import copy
from numpy.random import logistic
import os
import multiprocessing
import time
import tkinter 
import pickle
from tkinter import *

#The skeleton for this bot is from the MIT PokerBots course website 
#The skeleton code defined Player, run, and 'if __name__ == '__main__':" 

handsToPlay = 20
allHistories = []

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
        print([[0 for i in range(10)] for j in range(10)])
        

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
            print(self.name, data,'\n\n')
       

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
                            self.opponents[player] = Opponent(player,self.__dict__)

                self.numHands+=1

                self.gameState = 'preflop'

            elif word == "GETACTION":

                self.historyUpdate(packetValues)

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
                inputSocket.send(response)

            elif word == 'HANDOVER':
                self.stackSizes = packetValues[1:4]
                self.historyUpdate(packetValues,True)
                

            elif word == "REQUESTKEYVALUES":
                # At the end, the engine will allow your bot save key/value pairs.
                # Send FINISH to indicate you're done.
                inputSocket.send(b"FINISH\n")

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

            if self.histories!={}:

                self.statUpdate()

                #opponent attributes update
                for opponent in self.opponents:
                    currOpp = self.opponents[opponent]
                    currOpp.attrsUpdate(self.__dict__)

                #opponent stats update
                self.oppUpdate()

                varsBotCopy = copy.deepcopy(self.__dict__)
                #varsBotCopy.pop('histories')
                print('SNAPSHOT',self.name, varsBotCopy,'\n\n')


        # Clean up the socket.
        inputSocket.close()
        time.sleep(2)
        if self.name=='player1':
            print('hi\n\n',allHistories,'\n\n')

        #EXPORT allHistories to text file
        
        Player.writeFile('filename.pickle',allHistories,True)
        


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
                #print(currOpp.name, '\n', varsOppCopy,'\n\n')

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
            if ("WIN" in event or 'TIE' in event) and self.name in event:
                wins+=1
        self.winRate = wins/self.numHands

    def getExpectedValue(self):
        if len(self.hole+self.board)<=6:
            outProb = Player.monteCarloTest(self.hole+self.board, True)
            self.EV =  outProb-self.potOdds
            self.impliedEV  = outProb-self.impliedPotOdds

    def historyUpdate(self, packetValues, handOver=False):
        if not handOver:
            for value in packetValues:
                if value.count(':')==2: #raise,bets,calls have 2 colons
                    for player in self.playerNames:
                        if player in value:
                            self.histories[player].append(value)
        elif handOver:
            for value in packetValues:
                #only needs to compute winrate for self
                if ('WIN' in value or 'TIE' in value) and self.name in value:
                    self.histories[self.name].append(value)
        if self.name=='player1':
            for value in packetValues:
                if ':' in value and 'player' in value:
                    allHistories.append(value)
            allHistories.append(self.board)
            allHistories.append(['pot',self.potSize])
            allHistories.append([self.name,self.hole,self.stack])
        else:
            allHistories.append([self.name,self.hole])


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
        self.type = 'afexploit'

    def botLogic(self):
        super().botLogic()
        actionsDict = self.actionsParse()
        if actionsDict.get('check',False):
            return ('check', 0)
        elif actionsDict.get('fold',False):
            if self.impliedEV>0 and self.EV<0 and actionsDict.get('call',False):
                pass
                return ('call',actionsDict['callVals'])
            elif self.impliedEV>0.8 and self.EV>0 and actionsDict.get('bet',False):
                return ('bet', actionsDict['betVals'][0])
            elif self.impliedEV>0 and self.EV>0 and actionsDict.get('raise',False):
                maxRaiseIndex = len(actionsDict['raiseVals'])-1
                if self.impliedEV>0.8:
                    specRaise = maxRaiseIndex
                elif self.impliedEV>0.5:
                    specRaise = maxRaiseIndex//2
                try:
                    return ('raise',actionsDict['raiseVals'][specRaise])    #test value
                except:
                    #sometime we don't set a raise value
                    pass
            else:
                return ('fold',0)

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
                


#botTester
def readFile(path, withPickle = False):
    if withPickle:
        with open(path, "rb") as f:
            return pickle.load(f)
    else:
        with open(path, "rt") as f:
            return f.read()

def writeFile(path, contents, withPickle = False):
    if withPickle:
        with open(path, "wb") as f:
                pickle.dump(contents,f)
    else:
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

def setBotTypes(bot1 = None,bot2 = None,bot3 = None): #max 3 bots allowed
    availBotTypes = ['evbasic','random','afexploit','checkfold']
    inputTypes = ['CHECKFOLD', 'RANDOM', 'SOCKET']

    botTuple = (bot1,bot2,bot3)
    inputList = list()

    for bot in botTuple:
        if bot==None: 
            bot = 'checkfold'
        bot = bot.lower()
        if bot not in availBotTypes: #turn all bad bots in to checkfold bots
            bot = 'checkfold'
        if bot == 'checkfold':
            inputList.append('CHECKFOLD')
        elif bot=='random':
            inputList.append('RANDOM')
        else:
            inputList.append('SOCKET')

    path = os.getcwd()
    fullPath = path+os.sep+'config.txt'
    config = readFile(fullPath)
    config = config.split('\n')

    for i in range(len(config)):
        line = config[i]
        if 'PLAYER_1_TYPE = ' in line:
            bot1Index = i
        elif 'PLAYER_2_TYPE = ' in line:
            bot2Index = i
        elif 'PLAYER_3_TYPE = ' in line: 
            bot3Index = i


    bot1Line = 'PLAYER_1_TYPE = %s' % inputList[0]
    bot2Line = 'PLAYER_2_TYPE = %s' % inputList[1]
    bot3Line = 'PLAYER_3_TYPE = %s' % inputList[2]

    config[bot1Index] = bot1Line
    config[bot2Index] = bot2Line
    config[bot3Index] = bot3Line

    newConfig = '\n'.join(config)    
    writeFile(fullPath,newConfig)

    return botTuple

def startBot(num,args,botType):  #bot number, args
        num = int(num)
        # Create a socket connection to the engine.
        print('Connecting to %s:%d' % (args.host, args.port+num))
        try:
            s = socket.create_connection((args.host, args.port+num))
        except socket.error as e:
            print('Error connecting! Aborting')
            exit()

        numPlusOne = num+1
        if botType=='evbasic':
            bot = EvBasic('player%d' % numPlusOne)
            bot.run(s)
        elif botType == 'afexploit':
            bot = AfExploit('player%d' % numPlusOne)
            bot.run(s)

def initThreads(botTuple,args):
        processes = []
        print(botTuple)
        for i in range(len(botTuple)):
            if botTuple[i]!='random' and botTuple[i]!='checkfold':  
                currArgs = (i,args,botTuple[i])
                currProcess = multiprocessing.Process(target=startBot,args=currArgs)
                processes.append(currProcess)
            else:
                pass
        for process in processes:
            process.start()
            time.sleep(0.1)
        return processes




###############################
#          GRAPHICS
###############################


def init(data):
    data.playerSize = 45
    data.player1pos = (15+data.playerSize,data.height/2)
    data.player2pos = (data.width/2,data.height-15-data.playerSize)
    data.player3pos = (data.width-15-data.playerSize,data.height/2)
    data.playerPositions = [data.player1pos,data.player2pos,data.player3pos]
    data.allHistories = allHistoriesNew
    data.stack = 0
    data.board = []
    data.playerCards = []
    data.botTuple = botTupleNew
    loadPlayingCardImages(data) 
    


def mousePressed(event, data):
    # use event.x and event.y
    pass

def keyPressed(event, data):
    # use event.char and event.keysym
    pass

def timerFired(data):
    pass

def redrawAll(canvas, data):
    #table
    canvas.create_rectangle(5,5,data.width-5,data.height-5,fill = 'orange4')
    canvas.create_rectangle(10,10,data.width-10,data.height-10,fill = 'green4')
    canvas.create_text(10,10,text = 'Players: %s' % ' '.join(data.botTuple),anchor = 'sw')
    drawPlayers(canvas,data)


def drawPlayers(canvas,data):
    playerCount = 0
    for player in data.playerPositions:
        d = data.playerSize
        (x0,y0,x1,y1) = (player[0]-d,player[1]-10,player[0]+d,player[1]+10)
        canvas.create_rectangle(x0,y0,x1,y1, fill = 'red4')
        canvas.create_text(player[0],player[1], text = '%s' % botTupleNew[playerCount].upper())
        playerCount+=1

#loadPlayingCardImages, getPlayingCardImage, getSpecialPlayingCardImage from 15-112 graphics course notes

def loadPlayingCardImages(data):
    cards = 55 # cards 1-52, back, joker1, joker2
    data.cardImages = [ ]
    for card in range(cards):
        rank = (card%13)+1
        suit = "cdhsx"[card//13]
        filename = "playing-card-gifs/%s%d.gif" % (suit, rank)
        data.cardImages.append(PhotoImage(file=filename))

def getPlayingCardImage(data, rank, suitName):
    suitName = suitName[0].lower() # only car about first letter
    suitNames = "cdhsx"
    assert(1 <= rank <= 13)
    assert(suitName in suitNames)
    suit = suitNames.index(suitName)
    return data.cardImages[13*suit + rank - 1]

def getSpecialPlayingCardImage(data, name):
    specialNames = ["back", "joker1", "joker2"]
    return getPlayingCardImage(data, specialNames.index(name)+1, "x")


################################
#graphics run function taken from 15-112 course notes

def run(width=300, height=300):
    def redrawAllWrapper(canvas, data):
        canvas.delete(ALL)
        redrawAll(canvas, data)
        canvas.update()    

    def mousePressedWrapper(event, canvas, data):
        mousePressed(event, data)
        redrawAllWrapper(canvas, data)

    def keyPressedWrapper(event, canvas, data):
        keyPressed(event, data)
        redrawAllWrapper(canvas, data)

    def timerFiredWrapper(canvas, data):
        timerFired(data)
        redrawAllWrapper(canvas, data)
        # pause, then call timerFired again
        canvas.after(data.timerDelay, timerFiredWrapper, canvas, data)
    # Create root before calling init (so we can create images in init)
    root = Tk()
    # Set up data and call init
    class Struct(object): pass
    data = Struct()
    data.width = width
    data.height = height
    data.timerDelay = 250 # milliseconds
    init(data)
    # create the root and the canvas
    canvas = Canvas(root, width=data.width, height=data.height)
    canvas.pack()
    # set up events
    root.bind("<Button-1>", lambda event:
                            mousePressedWrapper(event, canvas, data))
    root.bind("<Key>", lambda event:
                            keyPressedWrapper(event, canvas, data))
    timerFiredWrapper(canvas, data)
    # and launch the app
    root.mainloop()  # blocks until window is closed
    print("bye!")

if __name__ == '__main__':
    
    setHands(handsToPlay)
    botTuple = setBotTypes('afexploit','random','random')
    writeFile('filename1.pickle', botTuple,True)

    assert(len(botTuple)==3)

    parser = argparse.ArgumentParser(description='A Pokerbot.', add_help=False, prog='pokerbot')
    parser.add_argument('-h', dest='host', type=str, default='localhost', help='Host to connect to, defaults to localhost')
    parser.add_argument('port', metavar='PORT', type=int, help='Port on host to connect to')
    args = parser.parse_args()


    processes = initThreads(botTuple,args)

    processesDead = False
    while not processesDead:
        eachProcess = 0
        for process in processes:
            if process.is_alive():
                eachProcess+=1
        if eachProcess==0:
            processesDead = True

    #read and parse output log
    if processesDead:
        botTupleNew = readFile('filename1.pickle',True)
        allHistoriesNew = readFile('filename.pickle',True)
        print(allHistoriesNew)
        run(1200, 600) 
    



#CHANGE paths to os.getcwd() 










    


