15-112 Term Project: PokerBots Suite

This project is a suite for designing and testing poker artificial intelligence (AI) machines using the MIT PokerBots Engine. The engine runs a game of Pot Limit Texas Hold’Em with up to 3 players, each of which send/receive packets from the engine (except for ‘random’ and ‘checkfold’ bots which are run within the engine). 


The primary script, Player.py, executes the following in order:

1. Starts user input for game parameters (bots, hands, blind size)
	- saves game parameters using pickle
2. Executes bash script, which runs a .jar file (the game engine)
	- engine generates text logs for each game
3. Start threads for each individual bot
4. Attach bots to sockets on game engine
5. Log game results using pickle
6. Start game footage graphics
	- read in logs from pickle files
7. Terminate engine process

(bot processes self-terminate)

Prerequisites:

To run this project, you will need the following modules:

numpy,
socket,
os,
multiprocessing,
time,
pickle,
tkinter,
itertools,
random,
copy

Installation:

All modules listed except for numpy are part of the Python 3.4 Standard Library. The numpy module can be installed by entering 

‘python -m pip install numpy’ 

in the command line (“pip” is a package installation utility that comes standard with python 3.4). 

Running Player.py:

Run ‘python Player.py’ in the command line 
