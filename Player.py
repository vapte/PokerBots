import argparse
import socket
import sys
import copy
import os
import multiprocessing
import subprocess
import time
import pickle

#my files:
from evbasic import *
from playerclass import *
from opponent import *
from afexploit import *
from settings_handler import * 
from game_footage import *
from startup import *

def startBot(num,args,botType):  #bot number, args
        num = int(num)
        print(args)
        # Create a socket connection to the engine.
        print('Connecting to %s:%d' % (args['host'], args['port']+num))
        try:
            s = socket.create_connection((args['host'], args['port']+num))
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
        botList = list(botTuple)
        botTuple = botList.sort(key = lambda x: (x not in ['random','checkfold']))
        print(botTuple)
        processes = []
        for i in range(len(botTuple)):
            if botTuple[i]!='random' and botTuple[i]!='checkfold': 
                currArgs = (portNum, i,args,botTuple[i])
                currProcess = multiprocessing.Process(target=startBot,args=currArgs)
                processes.append(currProcess)
            else:
                pass
        for process in processes:
            process.start()
            time.sleep(0.1)
        return processes

def killPickles():
    for i in range(8):
        if i!=0:
            writeFile('filename%d.pickle' % i, 'blank', True)
        else:
            writeFile('filename.pickle', 'blank', True)

if __name__ == '__main__':

    killPickles()
    runUI()

    runJar.terminate()
    runJar = multiprocessing.Process(target = subprocess.call, args = ["./runjar.sh"])
    runJar.start()
    time.sleep(1)

    botTuple = readFile('filename1.pickle', True)
    assert(len(botTuple)==3)

    # parser = argparse.ArgumentParser(description='A Pokerbot.', add_help=False, prog='pokerbot')
    # parser.add_argument('-h', dest='host', type=str, default='localhost', help='Host to connect to, defaults to localhost')
    # parser.add_argument('port', metavar='PORT', type=int, help='Port on host to connect to')
    # args = parser.parse_args()

    processes = initThreads(botTuple,{'host':'localhost','port':3000})

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
        startingStack = readFile('filename2.pickle',True)
        allHistoriesNew = []
        for i in list(range(3,6)):
            currList = readFile('filename%d.pickle' % i ,True)
            if currList == {'hello':'world'} or currList == 'blank':
                continue
            for item in currList:
                assert(type(item)==tuple)
                allHistoriesNew.append(item)
        allHistoriesNew.sort(key = lambda x: x[1])
        extra = copy.deepcopy(allHistoriesNew)
        allHistoriesNew = []
        extraBoards = []
        for i in range(1,len(extra)):
            item = extra[i]
            if item[0] !=extra[i-1][0] and item[0]!=[] and item not in extraBoards:
                allHistoriesNew.append(item[0])
            if type(item)==list and type(item[-1])==str and extra.count(item)>1:
                extraBoards.append(item)



        print(allHistoriesNew,len(allHistoriesNew))
        writeFile('filename8.pickle',allHistoriesNew,True)
      
    runFootage()
    runJar.terminate()
    













    


