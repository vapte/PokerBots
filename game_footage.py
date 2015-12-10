
from tkinter import *
from settings_handler import *
from db import *

import pickle

###############################
#          GRAPHICS
###############################

pace = readFile('filename7.pickle',True)
if pace==1:
    devSpeed = 250 #special timerDelay for dev
else:
    devSpeed = 650

def init(data):
    data.playerSize = 45
    data.player1pos = (15+data.playerSize,data.height/2)
    data.player2pos = (data.width/2,data.height-15-data.playerSize)
    data.player3pos = (data.width-15-data.playerSize,data.height/2)
    data.playerPositions = [data.player1pos,data.player2pos,data.player3pos]
    data.playerNames = ['player1','player2','player3']
    data.readoutPositions = [(i,j-100) for (i,j) in data.playerPositions]
    data.allHistories = readFile('filename8.pickle',True)
    (data.blind, startingStack) = readFile('filename2.pickle',True)
    data.stackSizes = [startingStack]*3
    data.board = []
    #make sure data.playerCards is filled
    data.playerCards = [['back','back'],['back','back'],['back','back']]
    data.botTuple = readFile('filename1.pickle',True)
    loadPlayingCardImages(data) 
    data.cardOffset = 85
    data.boardSize = 230
    data.timerCount = 0
    data.potSize = 0
    data.readoutCount = 0
    data.gameOver = False
    data.potBoxSize = 70
    data.numHands = 0 
    data.seen = None
    data.pace = readFile('filename7.pickle',True)
   


def mousePressed(event, data):
    pass

def keyPressed(event, data):
    pass

def timerFired(data):
    if data.timerCount%data.pace == 0:
        data.readoutCount=data.timerCount//data.pace
    
    data.timerCount+=1

def parseEvent(data,event):
    if event==[]: #empty
        return None
    elif event[0] == 'pot':   #pot
       # data.potSize=event[1]
        return None 
    elif len(event)>=3 and type(event[1])==str and type(event)==list:  #board
        data.board=event
        return 'board'
    elif ':' in event:  #game event
        eventList = event.split(':')
        action = eventList[0]
        player = int(eventList[-1][-1])
        try:
            quantity = int(eventList[1])    #some actions have no quantity
            return (action,player,quantity)
        except:
            return (action,player)  
    elif 'player' in event[0]:  #player
        player = int(event[0][-1])  #player index int
        hole = event[1]
        stack = event[2]
        return ('playerEvent', player,hole,stack)


def redrawAll(canvas, data):
    #table
    canvas.create_rectangle(5,5,data.width-5,data.height-5,fill = 'orange4')
    canvas.create_rectangle(10,10,data.width-10,data.height-10,fill = 'green4')
    #gametext
    canvas.create_text(20,30,text = 'Players: %s' % ', '.join(data.botTuple),
        anchor = 'sw', font = 'msserif 12')
    drawAllActive(canvas, data)
    #readout
    if data.gameOver:
        canvas.create_text(data.width/2, 40, text = 'Game Over', 
            fill = 'white', font = 'msserif 12 bold')
    n = data.readoutCount!=None 
    if n and data.readoutCount>len(data.allHistories)-1 and not data.gameOver:
        canvas.create_text(data.width/2, 40, text = 'Game Over',
         fill = 'white', font = 'msserif 12 bold')
        data.gameOver = True
    if not n or data.readoutCount>len(data.allHistories)-1: pass
    else:
        currEvent = data.allHistories[data.readoutCount]
        db('currEvent',currEvent)
        readOut = parseEvent(data,currEvent)
        db('readout',readOut)
        if readOut!=None:
            readoutParse(readOut,data,canvas,currEvent)

#draws all entities that change during gameplay
def drawAllActive(canvas,data):
    #players
    drawPlayers(canvas,data)
    #board
    (w,b,h) = (data.width,data.boardSize,data.height)
    canvas.create_rectangle(w/2-b,h/2-172,w/2+b,h/2-72,fill=  'red4')
    #boardCards
    drawBoardCards(canvas,data)
    #drawPot
    drawPot(canvas,data)

#draws based on readout command
def readoutParse(readOut,data,canvas,currEvent):
    if readOut=='board':
        drawBoardCards(canvas,data)
    elif readOut == 'pot':
        drawPot(canvas,data)
    elif readOut[0] == 'playerEvent':
        assert(len(readOut[2])==2)  #player always has 2 hole cards
        data.playerCards[readOut[1]-1] = readOut[2] #index offset 
        drawPlayers(canvas,data)
    elif type(readOut)==tuple:   #action that adds to pot, removes player stack
        if data.seen == None:
            data.seen = readOut
        elif data.seen == readOut:  #prevent same action from repeat recording
            pass
        else:
            actionDataUpdate(readOut, data)
            drawAction(canvas,data,currEvent)
            data.seen = readOut

#update data based on action type/quantity
def actionDataUpdate(readOut,data):
    try:
        (action,player,quantity) = readOut
    except:
        (action,player) = readOut
    cutStack = ['POST','CALL','TIE','BET','RAISE']
    padStack = ['WIN','REFUND']
    if action=='WIN':
        data.numHands+=1
    elif action=='TIE': 
        data.numHands+=0.5
    if action in cutStack:
        data.stackSizes[player-1] -= quantity
        data.potSize += quantity
    elif action in padStack:
        data.stackSizes[player-1] += quantity
        data.potSize -= quantity 

#draw the action box
def drawAction(canvas,data,event):
    (actionX,actionY) = data.playerPositions[int(event[-1])-1]  #-1 for list 
    d = data.playerSize
    (x0,y0,x1,y1) = (actionX-d,actionY-25,actionX+d,actionY+25)
    eventList = event.split(':')
    action = eventList[0]
    player = int(eventList[-1][-1])
    if action in ['WIN','TIE','REFUND']:    #taking from the pot
        canvas.create_rectangle(x0,y0,x1,y1, fill = 'green')
    elif action in ['RAISE', 'BET', 'POST', 'CALL']:    #adding to the pot
        canvas.create_rectangle(x0,y0,x1,y1, fill = 'red')
    else:   #actions that don't affect the pot (directly)
        canvas.create_rectangle(x0,y0,x1,y1, fill = 'floralwhite')
    actionY-=8
    try:
        quantity = int(eventList[1])    #some actions have no quantity
        canvas.create_text(actionX,actionY, text = "%s:%d" % (action,quantity), 
            font = 'msserif 18 bold')
    except:
        canvas.create_text(actionX,actionY, text = "%s" % action, 
            font = 'msserif 18 bold')

#draws the pot box with hands played
def drawPot(canvas,data):
    (x0,y0,x1,y1) = (data.width/2-data.potBoxSize,
        100-data.potBoxSize/2,data.width/2+data.potBoxSize,
        100+data.potBoxSize/2)
    canvas.create_rectangle(x0,60,x1,110,fill = 'floralwhite')
    canvas.create_text(data.width/2, 80, text = 'POT: %d' % data.potSize, 
        font = 'msserif 12 bold')
    canvas.create_text(data.width/2,95, 
        text = 'HANDS PLAYED: %d' % data.numHands, font = 'msserif 12 bold')

#draws cards on the board
def drawBoardCards(canvas,data):
    initX = data.width/2-data.boardSize+25
    y0 = data.height/2-150-20
    count = 0 
    while len(data.board)<5:
        data.board.append('back')
    for card in data.board:
        if card!='back':
            (rank,suit) = getRankSuit(card)
            canvas.create_image(initX+count*data.cardOffset,y0,
                image = getPlayingCardImage(data,rank,suit),anchor='nw')
        else:
            canvas.create_image(initX+count*data.cardOffset,y0,
                image = getSpecialPlayingCardImage(data,'back'),anchor = 'nw')
        count+=1
    boardState = ''
    if data.board.count('back')==2: boardState = 'FLOP'
    elif data.board.count('back')==1: boardState = 'TURN'
    elif data.board.count('back')== 0: boardState = 'RIVER'
    if data.board.count('back')==5: boardState = 'PREFLOP'
    canvas.create_text(initX+(count+1)*data.cardOffset, data.height/2-130, 
        text = boardState, font = 'msserif 14 bold')

#return (rank,suit) tuple from string pair representation of cards
def getRankSuit(card):
    if card == 'back':
        return 'back'
    rank = card[0]
    suit = card[1]
    if rank not in list(range(2,10)):
        if rank == 'A':
            rank = 1
        elif rank == 'K':
            rank = 13
        elif rank == 'Q':
            rank = 12
        elif rank == 'T':
            rank = 10
        elif rank == 'J':
            rank = 11
    rank = int(rank)
    return (rank,suit)


def drawPlayers(canvas,data):
    playerCount = 0
    for player in data.playerPositions:
        #draw player box, type, stack
        drawBoxTypeStack(canvas, data, player,playerCount)
        d = data.playerSize
        (x0,y0,x1,y1) = (player[0]-d,player[1]-25,player[0]+d,player[1]+25)
        #draw hole cards
        currPlayer =  list(map(getRankSuit, data.playerCards[playerCount]))
        if playerCount==0:
            initX,initY = player[0]+d+50, player[1]
        elif playerCount==1:
            initX,initY =player[0]-data.cardOffset/2-5,player[1]-data.cardOffset
        elif playerCount==2:
            initX,initY = player[0]-d-50-data.cardOffset, player[1]
        for i in range(2):
            if type(currPlayer[i])==tuple:
                rank = currPlayer[i][0]
                suit = currPlayer[i][1]
                canvas.create_image(initX+data.cardOffset*i,initY,
                    image = getPlayingCardImage(data,rank,suit))
            else:
                canvas.create_image(initX+data.cardOffset*i,initY,
                    image = getSpecialPlayingCardImage(data,'back'))
        playerCount+=1

#draw player box, type, stack
def drawBoxTypeStack(canvas,data, player, playerCount):
    d = data.playerSize
    (x0,y0,x1,y1) = (player[0]-d,player[1]-25,player[0]+d,player[1]+25)
    canvas.create_rectangle(x0,y0,x1,y1, fill = 'floralwhite')
    canvas.create_text(player[0],player[1], 
        text = '%s' % data.botTuple[playerCount].upper(), 
        font = 'msserif 12 bold')
    canvas.create_text(player[0],player[1]+15, 
        text = '%d' % max(data.stackSizes[playerCount],0),
         font = 'msserif 12 bold')

#loadPlayingCardImages, getPlayingCardImage, getSpecialPlayingCardImage
# from 15-112 graphics course notes
#playing-card-gifs and all its contents from 15-112 graphics course notes

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
#graphics run function from 15-112 course notes
###############################


def runFootage(width=800, height=600):
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
    data.timerDelay = devSpeed # milliseconds
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
