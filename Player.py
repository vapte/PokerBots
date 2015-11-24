import argparse
import socket
import sys
import itertools as it 
import random
import copy

"""
Simple example pokerbot, written in python.

This is an example of a bare bones pokerbot. It only sets up the socket
necessary to connect with the engine and then always returns the same action.
It is meant as an example of how a pokerbot should communicate with the engine.
"""
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

    def __init__(self):
        self.hole = []
        self.board = []
        self.potSize = 0
        self.numCards = 0

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
            if packetValues[0] == 'GETACTION':
                potSize = packetValues[1]
                numCards = int(packetValues[2])
                if numCards > 0:
                    board = packetValues[3:3+numCards]
                    print(board)
                stackSizes = packetValues[3+numCards:6+numCards] 

            # When appropriate, reply to the engine with a legal action.
            # The engine will ignore all spurious responses.
            # The engine will also check/fold for you if you return an
            # illegal action.
            # When sending responses, terminate each response with a newline
            # character (\n) or your bot will hang!
            word = data.split()[0]
            if word=='NEWHAND':
                self.hole = [word[3],word[4]]
            if word == "GETACTION":
                # Currently CHECK on every move. You'll want to change this.
                s.send("CHECK\n")
            elif word == "REQUESTKEYVALUES":
                # At the end, the engine will allow your bot save key/value pairs.
                # Send FINISH to indicate you're done.
                s.send("FINISH\n")
        # Clean up the socket.
        s.close()

    def raiseChoose(self):
        #minRaise = last bet
        #maxRaise = potSize
        pass

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
    def monteCarloTest(Player,allCards):
        '''
        runs a Monte Carlo sim to test probability next community card
        is an out (i.e., best hand with out better current best hand)
        '''
        simNum = 5000
        simCount = 0
        cumePower = 0
        adjustedFullDeck = copy.copy(Player.fullDeck)  #Player.fullDeck-allCards

        assert(len(allCards)<=6) 

        for card in adjustedFullDeck:
            if card in allCards:
                adjustedFullDeck.remove(card)
        initAdjustedFullDeck = copy.copy(adjustedFullDeck)


        while simCount<=simNum:
            adjustedFullDeck = copy.copy(initAdjustedFullDeck)
            print(adjustedFullDeck)
            currCards = copy.copy(allCards)
            if len(allCards)<=6:    #post-flop
                nextCard = random.choice(adjustedFullDeck)
                currCards+=[nextCard]
                adjustedFullDeck.remove(nextCard)
                if len(allCards)<=5:  #turn
                    nextCard2 = random.choice(adjustedFullDeck)
                    currCards+=[nextCard2]
                    adjustedFullDeck.remove(nextCard2)
                    if len(allCards)==2:
                        nextCard3 = random.choice(adjustedFullDeck)
                        currCards+=[nextCard3]
            print(currCards)
            cumePower+=Player.bestHand(currCards)
            simCount+=1
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
        assert(len(hand)==5)    #hold'em hands have 5 cards
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

        return (handType, Player.handOrder.index(handType)+1)
        #offset by 1 because monte carlo

        '''
        TODO
        write handPower function to give granularity between hands of same type
        '''

    def handPower(hand,handStrVals,handType):
        #returns index of highest card in Player.values
        maxPower = 0
        for i in handStr:
            if Player.values.index(i)>=maxPower:
                maxPower = Player.values.index(i)
        return maxPower


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



    bot = Player()
    bot.run(s)
