###################
# STARTUP GRAPHICS 
###################

from tkinter import *
import time
import os
import pickle

from settings_handler import *
from db import *

def init(data):
    data.numButtons = 12
    data.buttons = []
    #each buttonDict = {id: X, numPresses: X, position: X,...}
    data.column = 150   #rule of thirds
    data.margin = 10
    data.buttonSize = 15
    data.fieldWidth = 120
    data.row = 43
    data.handButton = {'id':'handX', 'numPresses': 0, 'position': 'placeholder'}
    initButtons(data)
    data.numRows = 6
    data.typeChoices =['evbasic','random','afexploit','checkfold']
    loadBackground(data)
    data.splash = True    #true = splash screen, false = setting screen
    data.exported = False
    if not isDb():
        data.maxHandsAllowed = 1000
    else:
        data.maxHandsAllowed = 50
    initInputParameters(data)

def initInputParameters(data):
    data.player1type = 0
    data.player2type = 2
    data.player3type = 1
    data.blind = 1
    data.numHands = 10
    data.pace = 1

def initButtons(data):
    #player1 up/down, player2 up/down, player 3 up/down, big blind, hands, 
    #playback pace
    for i in range(data.numButtons):  #careful with aliasing here. 
        (col,m,f,row) = (data.column, data.margin, data.fieldWidth,data.row)
        if i==0: x = {'id':'player1up', 'position':(col+m, row)}
        elif i==1: x = {'id':'player1down','position' :(col+m+f, row)}
        elif i==2: x = {'id': 'player2up', 'position':(col+m, row*2)}
        elif i==3: x = {'id': 'player2down', 'position':(col+m+f,row*2)}
        elif i==4: x = {'id':'player3up','position':(col+m,row*3)}
        elif i==5: x = {'id': 'player3down','position': (col+m+f,row*3)}
        elif i==6: x = {'id': 'blindup','position': (col+m, row*4)}
        elif i==7: x = {'id': 'blinddown','position':(col+m+f, row*4)}
        elif i==8: x = {'id': 'handsup', 'position':(col+m,row*5)}
        elif i==9: 
            x = {'id':'handsdown','position':(col+m+f, row*5)}
            data.handButton['position'] = (col+m+f+45,row*5+6)
        elif i==10: x = {'id':'paceup','position':(col+m, row*6)}
        elif i==11: x = {'id':'pacedown','position':(col+m+f, row*6)}
        #init numPresses generally
        x['numPresses'] = 0
        data.buttons.append(x)

### Splash Screen (data.splash == True): 

def timerFiredSplash(data):
    pass

def keyPressedSplash(event, data):
    pass

def mousePressedSplash(event, data):
    data.splash = False

def redrawAllSplash(canvas, data):
    splashText = "Welcome to the PokerBots Suite\n Click anywhere to continue"
    canvas.create_image(data.width/2, data.height/2, image = data.background)
    canvas.create_text(data.width/2, data.height/3, text = splashText, 
        fill = 'white', font = "msserif 20")
     #I should probably put my name on this 
    t = "Created by Vineet Apte"
    canvas.create_text(data.width-77,data.height-5, text = t, 
        fill = 'white',  font = 'msserif 14 bold')

### Input Screen (data.splash == False):

def mousePressedInput(event, data):
    for button in data.buttons:
        (x0,y0) = button['position']
        b = data.buttonSize
        if rectanglesOverlap(event.x,event.y,1,1,x0,y0,b,b):
            button['numPresses']+=1
            if button['id'] == 'handsup':
                data.numHands += 1
            elif button['id'] == 'handsdown':
                data.numHands -=  1
            if data.numHands<=0: data.numHands = 1

    (x,y) = data.handButton['position']
    if rectanglesOverlap(event.x,event.y,1,1,x-b/2,y-b/2,b,b):
        data.handButton['numPresses']+=1
        data.numHands*=10
        if data.numHands>data.maxHandsAllowed:   #max Hands = 100
            data.numHands=data.maxHandsAllowed
    buttonUpdate(data)

#updates input screen buttons
def buttonUpdate(data):
    for button in data.buttons:
        curr = button['numPresses']
        if button['id']=='player1up':
            data.player1type= (curr)%len(data.typeChoices)
        elif button['id']=='player1down':
            data.player1type= (data.player1type-curr)%len(data.typeChoices)
        elif button['id']=='player2up':
            data.player2type= (curr)%len(data.typeChoices)
        elif button['id']=='player2down':
            data.player2type= (data.player2type-curr)%len(data.typeChoices)
        elif button['id']=='player3up':
            data.player3type= (curr)%len(data.typeChoices)
        elif button['id']=='player3down':
            data.player3type= (data.player3type-curr)%len(data.typeChoices)
        elif button['id'] == 'blindup':
            data.blind = curr
        elif button['id'] == 'blinddown':
            data.blind -= curr
            if data.blind<=0: data.blind=1
        elif button['id'] == 'paceup':
            data.pace = curr
        elif button['id'] == 'pacedown':
            data.pace -= curr
            if data.pace<=0: data.pace= 1
            if data.pace>10: data.pace = 10

#from my submission of hw1:
def rectanglesOverlap(left1, top1, width1, h1, left2, top2, width2, h2):
    if (left1+width1>=left2 and 
        top1+h1>=top2 and 
        top2+h2>=top1 and left1<=left2+width2):
        return True
    elif (left1+width1>=left2 and 
        top2+h2>=top1 and 
        top2<=top1+h1 and left1<=left2+width2):
        return True
    elif (left2+width2<=left1+width1 and 
        top1+h1>=top2 and 
        top1+h1<=top2+h2 and left2+width2>=left1):
        return True
    elif (left2+width2<=left1+width1 and 
        top2+h2>=top1 and 
        top2+h2<=top1+h1 and left2+width2>=left1):
        return True
    else:
        return False

#draw user selections
def drawSelections(canvas,data):
    for i in range(1,data.numRows+1):
        currText = ''
        if i==1:
            currText = data.typeChoices[data.player1type]
        elif i==2:
            currText = data.typeChoices[data.player2type]
        elif i==3:
            currText = data.typeChoices[data.player3type]
        elif i==4:
            currText = str(data.blind)
        elif i==5:
            currText = str(data.numHands)
        elif i==6:
            if data.pace>1:
                currText = "Spectator"
            else:
                currText = "Developer"
        canvas.create_text(data.column+75,i*data.row+7, text = currText, 
            fill = 'white',  font = 'msserif 14 bold')

def keyPressedInput(event,data):
    if event.keysym == 'r':
        initInputParameters(data)
    elif event.keysym == 'c':
        export(data)
        data.exported = True
    pass


def timerFiredInput(data):
    pass

def redrawAllInput(canvas,data):
    canvas.create_image(data.width/2, data.height/2, image = data.background)
    drawButtons(canvas,data)
    drawTags(canvas, data)
    drawSelections(canvas, data)
    #close when done message
    canvas.create_text(data.width/2, data.height-100, text = "Close when done", 
        fill = 'white', font = 'msserif 18 bold')
    #reset
    if data.exported:
        canvas.create_rectangle(data.width-77-70,25,data.width-77+100-30,40,
            fill = 'red')
    data.exported = False
    canvas.create_text(data.width-77,25, 
        text = "Press 'r' to reset\nPress 'c' to confirm", fill = 'white',  
        font = 'msserif 14 bold')

#draw names for each use chose n
def drawTags(canvas,data): 
    for i in range(1,data.numRows+1):
        currText = ''
        if i==1:
            currText = 'Player 1 type:'
        elif i==2:
            currText = 'Player 2 type:'
        elif i==3:
            currText = 'Player 3 type:'
        elif i==4:
            currText = 'Big Blind:'
        elif i==5:
            currText = "Hands to Play:"
        elif i==6:
            currText = "Playback Lag:"
        canvas.create_text(100,i*data.row+7, text = currText, fill = 'white',
         font = 'msserif 14 bold')

def drawButtons(canvas,data):
    b = data.buttonSize
    k = data.buttonSize/5
    for button in data.buttons:
        (x0,y0) = button['position']
        if 'down' in button['id']:
            #draw down button
            v1  = (x0+k,y0+k)
            v2 = (x0+b-k,y0+k)
            v3 = (x0+b/2, y0+b-k)
            canvas.create_polygon(v1,v2,v3, fill = 'red')
            if button['id']=='handsdown': #draw hand 10x button
                (x,y)=  data.handButton['position']
                canvas.create_rectangle(x-b,y-b,x+b,y+b,fill= 'red',width= 0)  
                canvas.create_text(x,y,text = '10X', fill = 'white',
                    font = 'msserif 12 bold')
        elif 'up' in button['id']:
            #draw up button
            v1 = (x0+b/2, y0+k)
            v2 = (x0+k, y0+b-k)
            v3 = (x0+b-k, y0+b-k)
            canvas.create_polygon(v1,v2,v3,fill = 'red')
            

def loadBackground(data):
    data.background = None
    filename = "dogs_background.gif"
    data.background = PhotoImage(file=filename)


def export(data):
    startingStack = setHands(data.numHands)
    setBlind(data.blind)
    choice1 = data.typeChoices[data.player1type]
    choice2 = data.typeChoices[data.player2type]
    choice3 = data.typeChoices[data.player3type]
    bots = setBotTypes(choice1,choice2,choice3)
    writeFile('filename1.pickle', bots,True)
    writeFile('filename2.pickle',(data.blind, startingStack),True)
    writeFile('filename7.pickle', data.pace, True)

### Master graphics functions:

def mousePressed(event,data):
    if data.splash:
        mousePressedSplash(event,data)
    else:
        mousePressedInput(event,data)

def keyPressed(event, data):
    if data.splash:
        keyPressedSplash(event,data)
    else:
        keyPressedInput(event, data)        

def redrawAll(canvas, data):
    if data.splash:
        redrawAllSplash(canvas,data)
    else:
        redrawAllInput(canvas, data)

def timerFired(data):
    if data.splash:
        timerFiredSplash(data)
    else:
        timerFiredInput(data)
    


####################################
# run function from 15-112 course notes
####################################

def runUI(width=450, height=450):
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



