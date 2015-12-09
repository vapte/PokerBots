
# To easily turn on/off db output
dbOn = True
def db(*args):
    if (dbOn): print(*args)
def isDb():
    return dbOn

