import argparse
import socket
import sys
import itertools as it 
import random
import copy
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
        self.blindsLeft = self.potSize/self.blind
        self.ev = 0
        self.AF = 0
        self.name = name
        self.playerStats = dict()
        self.stack = 0
        self.opponents = dict()
        self.numHandsPlayed = 0
        self.winRate = 0

    def run(self, inputSocket):
        

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
            print(packetValues)
                

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
                if self.opponents == {}:
                    for player in self.playerNames:
                        if player!=self.name:
                            self.opponents[player] = Opponent(player,self.histories)
                self.numHandsPlayed+=1


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



                s.send(b'CHECK\n')

            elif word == 'HANDOVER':
                self.stackSizes = packetValues[1:4]


            elif word == "REQUESTKEYVALUES":
                # At the end, the engine will allow your bot save key/value pairs.
                # Send FINISH to indicate you're done.
                s.send(b"FINISH\n")

            #update histories
            if word == "GETACTION" or word=="HANDOVER":
                self.historyUpdate(packetValues)

            if self.histories!={}:
                self.statUpdate()

                for opponent in self.opponents:
                    currOpp = self.opponents[opponent]
                    currOpp.historyUpdate(self.histories)
                    print('opponent',currOpp.name,currOpp.histories, self.histories)

                self.oppUpdate()


                print('!!!!READOUT',vars(bot))


        # Clean up the socket.
        s.close()


    #instance methods

    #manage opponent data
    def oppUpdate(self):
        #self.opponents initialized in run()
        for opponent in self.opponents:
            currOpp = self.opponents[opponent]
            if currOpp.name!=self.name:
                currOpp.statUpdate()
                print(currOpp.name, '\n', vars(currOpp))

    #top level function for computing all stats
    def statUpdate(self):
        self.getAggressionFactor()
        #update EV, blinds left, aggro factor
        self.expectedValue()
        try:
            self.stack = int(self.stackSizes[self.playerNames.index(self.name)])
            print('????????',self.playerNames,self.stackSizes,self.playerNames.index(self.name))
        except:
            pass
        
        self.blindsLeft  = int(self.stack/self.blind)

    #stat/history computation functions (must work for opponents with only histories as input)

    def getWinRate(self):
        wins = 0
        for event in self.histories[self.name]:
            if "WIN" in event:
                wins+=1
        self.winRate = wins/self.numHandsPlayed

    def expectedValue(self):
        if len(self.hole+self.board)<=6:
            outProb = Player.monteCarloTest(self.hole+self.board, True)
            self.ev =  outProb-self.potOdds

    def historyUpdate(self, packetValues):
        for value in packetValues:
            if value.count(':')==2: #all prior actions have 2 colons
                for player in self.playerNames:
                    if player in value:
                        self.histories[player].append(value)

    def getAggressionFactor(self):
        #set both to 1 b/c divide by zero
        downs = 1 #calls or folds
        ups = 1 #bets or raises
        for event in self.histories[self.name]:
            if 'CALL' in event or 'FOLD' in event:
                downs+=1
            elif 'BET' in event or 'RAISE' in event:
                ups+=1
        print('AFAF', ups, downs)
        self.AF = ups/downs


    #class/static methods

    @staticmethod
    def readFile(path):
        with open(path, "rt") as f:
            return f.read()

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
    def __init__(self, name,histories):
        super().__init__(name)
        self.histories = histories[self.name]

    #update history on each iteration
    def historyUpdate(self,histories):
        self.histories = {self.name: histories[self.name]}

    #inherit all methods that compute stats
    def getAggressionFactor(self):
        super().getAggressionFactor()

    #top level function for all stats
    def statUpdate(self):
        super().statUpdate()

    def getWinRate(self):
        super().getWinRate()


if __name__ == '__main__':
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



    bot = Player('playa')
    bot.run(s)
