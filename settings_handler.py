import os
import pickle


def setBlind(blind):
    if blind%2==1:
        blind+=1
    path = os.getcwd()
    fullPath = path+os.sep+'config.txt'
    config = readFile(fullPath)
    config = config.split('\n')
    config[0] = ' BIG_BLIND = %d' % blind
    newConfig = '\n'.join(config)
    writeFile(fullPath,newConfig)


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
    return new  #useful for graphics

def setBotTypes(bot1 = None,bot2 = None,bot3 = None): #max 3 bots allowed
    availBotTypes = ['evbasic','random','afexploit','checkfold']
    inputTypes = ['CHECKFOLD', 'RANDOM', 'SOCKET']
    botTuple,inputList = (bot1,bot2,bot3), list()
    for bot in botTuple:
        if bot==None: 
            bot = 'checkfold'
        bot = bot.lower()
        if bot not in availBotTypes: #turn all bad bots in to checkfold bots
            bot = 'checkfold'
        if bot == 'checkfold': inputList.append('CHECKFOLD')
        elif bot=='random': inputList.append('RANDOM')
        else: inputList.append('SOCKET')
    fullPath = os.getcwd()+os.sep+'config.txt'
    config = readFile(fullPath)
    config = config.split('\n')
    for i in range(len(config)):
        line = config[i]
        if 'PLAYER_1_TYPE = ' in line: bot1Index = i
        elif 'PLAYER_2_TYPE = ' in line: bot2Index = i
        elif 'PLAYER_3_TYPE = ' in line:  bot3Index = i
    bot1Line = 'PLAYER_1_TYPE = %s' % inputList[0]
    bot2Line = 'PLAYER_2_TYPE = %s' % inputList[1]
    bot3Line = 'PLAYER_3_TYPE = %s' % inputList[2]
    config[bot1Index] = bot1Line
    config[bot2Index] = bot2Line
    config[bot3Index] = bot3Line
    newConfig = '\n'.join(config)    
    writeFile(fullPath,newConfig)
    return botTuple


def writeFile(path, contents, withPickle = False):
    if withPickle:
        with open(path, "wb") as f:
                pickle.dump(contents,f)
    else:
        with open(path, "wt") as f:
            f.write(contents)


def readFile(path, withPickle = False):
    if withPickle:
        with open(path, "rb") as f:
            return pickle.load(f)
    else:
        with open(path, "rt") as f:
            return f.read()

def getBlind():
    path = os.getcwd()
    config = readFile(path+os.sep+'config.txt')
    return int(config.split('\n')[0][-1])


