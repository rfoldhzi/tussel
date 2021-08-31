#os.chdir(r"/Users/reeganfoldhazi/Documents/PythonStuff")
from UnitDB import UnitDB
from UnitDB import TechDB
import numpy as np
import random,operator,json,copy
import methods, Computer, settings
from json import JSONEncoder

startingspots = [[0,0],[9,9], [9,0]]
board_y = 10
board_x = 10

def checkRange(a,b):
    if type(b) == list:
        return max(abs(a.position[0]-b[0]), abs(a.position[1]-b[1]))
    return max(abs(a.position[0]-b.position[0]), abs(a.position[1]-b.position[1]))

def damageCalc(a,b):
    attackPower = a.attack*(a.health/a.maxHealth)
    defensePower = b.defense*(b.health/b.maxHealth)
    return round((attackPower/(attackPower+defensePower))*a.attack*5)

def getRangeCircles(game, unit, sp = False, pos = False, ignore = False):#Could be more effiecint
    if not sp:
        sp = unit.range
    if not pos:
        pos = unit.position
    spaces = []
    for x in range(pos[0]-sp, pos[0]+1+sp):
        for y in range(pos[1]-sp, pos[1]+1+sp):
            if x >= 0 and y >= 0 and y<game.height and x<game.width:#If within board:
                if ignore or game.getAnyUnitFromPos(x,y) == None:
                    spaces.append([x,y])
    return spaces

def setDefaultState(game):
    for i in game.units:
            for u in game.units[i]:
                if u.state == None and 'resources' in u.possibleStates:
                    u.state = 'resources'
                    u.stateData = max(u.resourceGen.items(), key=operator.itemgetter(1))[0]

def getCount(n, i, game):
    count = 0
    for u in game.units[i]:
        if u.name == n:
            count+=1
    return count

def CheckIfGoodToBuild(self, i, u, Grid, pos = False):
    if not pos:
        pos = u.stateData[0]
    cost = UnitDB[u.stateData[1]]['cost']
    if 'abilities' in UnitDB[u.stateData[1]] and 'costly' in UnitDB[u.stateData[1]]['abilities']:
        cost = copy.copy(cost)
        count = getCount(u.stateData[1], i,self)
        for v in cost:
            cost[v] = cost[v]*(UnitDB[u.stateData[1]]['abilities']['costly']**count)//5*5
            
    for v in cost:
        if self.resources[i][v] < cost[v]:#Check each resource
            print("Too expensive")
            return False #If too expensive, ignore build
    if getattr(u,'maxPopulation',False):
        if u.population >= u.maxPopulation:
            print("Too populated")
            return False #Max popultion reached
    if checkRange(u, pos) > u.range:
        print("Too far")
        return False #Can't build out of range
    t = UnitDB[u.stateData[1]].get('type') or 0
    if Grid[pos[1]][pos[0]]:#on Water
        if t not in ['aircraft', 'boat']:
            print("Too much water")
            return False #Can't build type on water
    else:#on land
        if t == 'boat':
            print("Too land")
            return False #Can't build boat on land
    if t == 'building':#Can't build buildings near enemy buildings
        Range = UnitDB[u.stateData[1]].get('range') or 1
        if 'abilities' in UnitDB[u.stateData[1]] and '' in UnitDB[u.stateData[1]]['abilities']:
            Range = UnitDB[u.stateData[1]]['abilities']['closeBuild']
        for v in getRangeCircles(self,u,Range,pos, True):
            unit = self.getAnyUnitFromPos(v[0],v[1])
            if unit and unit.type == 'building':
                if not self.checkFriendly(u,unit):
                    print("Too close")
                    return False
    print("Nothing wrong!")
    return True

UnitID = 0

class Unit:
    def __init__(self, pos = [0,0], name = 'soldier', parent= None):
        global UnitID
        self.name = name
        self.parent = parent
        self.type = UnitDB[name].get('type') or 'trooper'
        self.possibleStates = UnitDB[name].get('possibleStates') or ['attack','move','resources']
        #self.possiblebuilds = UnitDB[name].get('possibleBuilds') or []
        self.state = None
        self.stateData = None
        self.speed = UnitDB[name].get('speed') or 1
        self.range = UnitDB[name].get('range') or 1
        self.attack = UnitDB[name].get('attack') or 2
        self.defense = UnitDB[name].get('defense') or 2
        self.maxHealth = UnitDB[name].get('health') or 10
        self.health = int(self.maxHealth)
        self.UnitID = str(UnitID)
        UnitID += 1
        self.resourceGen = UnitDB[name].get('resourceGen') or {
            "gold": 4,
            "metal": 0,
            "energy": 0
            }
        self.abilities = UnitDB[name].get('abilities') or {}
        self.position = pos
        if ('build' in self.possibleStates and self.type == 'building') or UnitDB[name].get('population'):
            self.population = 0
            self.maxPopulation = UnitDB[name].get('population') or 3

class Encoder(JSONEncoder):
        def default(self, o):
            #Posible thing to do is is find all units with attack as their state and change statedata to unitID
            return o.__dict__

class UnitMaker(Unit):
    def __init__(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)

class Game:
    def __init__(self, id = 0, makeAreas = True):
        self.units = {} #Store players' units
        self.resources = {} #Store players' resource counts
        self.went = {}
        self.tech = {}
        self.progress = {}
        self.ready = False
        self.started = False
        self.turn = 0
        self.id = id
        self.width = settings.width #13
        self.height = settings.height #13
        self.mode = settings.mode #'halo'
        self.ai = settings.ai #1
        self.allai = settings.allai #False
        if makeAreas:
            grid = methods.newGrid(self.width,self.height)
            grid = methods.makeAreas(grid)
            self.intGrid = list(np.packbits(np.uint8(grid)))
            for i in range(len(self.intGrid)):
                self.intGrid[i] = int(self.intGrid[i])
            print(type(self.intGrid), type(self.intGrid[0]))
    def addPlayer(self):
        p = len(self.units)
        self.units[p] = []
        self.resources[p] = {'gold':20,'metal':0,'energy':0}
        self.went[p] = False
        self.tech[p] = []
        self.progress[p] = {}
        #b = Unit(startingspots[p], 'town')
        #self.units[p].append(b)
    def start(self):
        if not self.started:
            self.started = True
            for i in range(self.ai):
                self.addPlayer()
                self.went[len(self.units)-1] = True
            Grid = methods.intToList(self.intGrid, self.width)
            print('units',self.units)
            startingspots = methods.findStartSpots(Grid, len(self.units))
            if startingspots == "RETRY":
                cont = True
                while cont:
                    print("Rety retry retry retrtr retert retry ")
                    grid = methods.newGrid(self.width,self.height)
                    grid = methods.makeAreas(grid)
                    startingspots = methods.findStartSpots(Grid, len(self.units))
                    if startingspots != "RETRY":
                        cont = False
                self.intGrid = list(np.packbits(np.uint8(grid)))
                for i in range(len(self.intGrid)):
                    self.intGrid[i] = int(self.intGrid[i])
            random.shuffle(startingspots)
            print(startingspots)
            i = 0
            #starters = ['king slime', 'king blob']
            #starters = ['the hunter', 'king blob']
            for p in self.units:
                #self.units[p].append(Unit(startingspots[p], starters[i]))
                self.units[p].append(Unit(startingspots[p], "town"))
                i+=1
    def generateZippedBytes(self):
        #print(vars(self))
        SELF = self
        uncopied = True
        for i in SELF.units:
            for u in SELF.units[i]:
                if u.state == "attack" and type(u.stateData) != str and u.stateData:
                    if uncopied:
                        SELF = copy.copy(self)
                        uncopied = False
                    print("STATE DATA", type(u.stateData), u.stateData)
                    u.stateData = u.stateData.UnitID
        JSONData = json.dumps(SELF, indent=0, cls=Encoder)
        JSONData = str(JSONData)
        JSONData = JSONData.replace("\n", '')
        JSONData = JSONData.replace(": ",':')
        ZIP = methods.zipper(JSONData)
        """
        for i in self.units:
            for u in self.units[i]:
                if u.state == "attack" and type(u.stateData) == str:
                    print("STATE DATA2222", type(u.stateData), u.stateData)
                    u.stateData = self.getUnitFromID2(u.stateData)
        """
        #SON = json.loads(ZIP)
        return str.encode(ZIP)
    def getUnitFromPos(self,player,x,y):
        post = [x,y]
        for u in self.units[player]:
            if u.position == [x,y]:
                return u
        return None
    def getAnyUnitFromPos(self,x,y):
        post = [x,y]
        for i in self.units:
            for u in self.units[i]:
                if u.position == [x,y]:
                    return u
        return None
    def getPlayerfromUnit(self,unit):
        for i in self.units:
            for u in self.units[i]:
                if u == unit:
                    return i
        return None
    def checkFriendly(self, unit1, unit2):
        return unit2 in self.units[self.getPlayerfromUnit(unit1)]
    def checkFriendlyPlayer(self, unit, player):
        return unit in self.units[player]
    def getUnitFromID(self, ID):
        for i in self.units:
            for u in self.units[i]:
                if u.UnitID == ID:
                    return u
        return None
    def getUnitFromID2(self, ID):
        for i in self.units:
            for u in self.units[i]:
                if type(u) == dict and u['UnitID'] == ID:
                    return u
                elif type(u) != dict and u.UnitID == ID:
                    return u
        return None
    def upgradeTech(self, unit, v):
        currentAbility = v[0]
        if currentAbility == 'unlock build' and v[1] == unit.name:#[1] is builder
            if not getattr(unit, 'possiblebuilds', False):
                unit.possiblebuilds = list(UnitDB[unit.name].get('possibleBuilds')) or []
            unit.possiblebuilds.append(v[2])#[2] is what was unlocked
        elif currentAbility == 'lose build' and v[1] == unit.name:#[1] is builder
            if not getattr(unit, 'possiblebuilds', False):
                unit.possiblebuilds = list(UnitDB[unit.name].get('possibleBuilds')) or []
            if v[2] in unit.possiblebuilds:
                unit.possiblebuilds.remove(v[2])#[2] is what was lost
        elif currentAbility == 'stat' and v[1] == unit.name:#v[1] is unit
            print('nwe unit')
            print('we are in the belly of the beaast: stat changes', v)
            setattr(unit, v[2], getattr(unit, v[2])+v[3])#v[2] is stat, v[3] is how much it changes
        elif currentAbility == 'typeStat' and v[1] == unit.type:#[1] is what unit type was affected
            print('current')
            print('we are in the belly of the beast: stat changes', v)
            setattr(unit, v[2], getattr(unit, v[2])+v[3])#v[2] is stat, v[3] is how much it changes
        elif currentAbility == 'gain ability' and v[1] == unit.name:
            unit.abilities[v[2]] = v[3]#v[2] is ability, v[3] is value
        elif currentAbility == 'typeAbility' and v[1] == unit.type:#[1] is what unit type was affected
            unit.abilities[v[2]] = v[3]#v[2] is ability, v[3] is value
    def upgradeUnit(self, unit, player):
        for t in self.tech[player]:
            abil = TechDB[t]['ability']
            for v in abil:
                self.upgradeTech(unit, v)
    def upgradeCurrentUnits(self, player, tech):
        print('upgrading currents')
        abil = TechDB[tech]['ability']
        for unit in self.units[player]:
            for v in abil:
                self.upgradeTech(unit, v)
    def setState(self,player, data):#unit, state,statedata
        split = data.split(':')
        unit = self.getUnitFromID(split[0])
        state = split[1]
        stateData = split[2]
        if state == 'move':
            stateData = [int(split[2]),int(split[3])]
        elif state == 'attack':
            stateData = self.getUnitFromID(split[2])
        elif state == 'heal':
            stateData = self.getUnitFromID(split[2])
        elif state == 'build':
            stateData = [[int(split[2]),int(split[3])],split[4]]
        for u in self.units[player]:
            if u == unit:
                unit.state = state
                unit.stateData = stateData
                break#Stop unnessary looping
    def playerDone(self,player):
        self.went[player] = True
        allWent = True
        print(self.went)
        for p in self.went:
            if not self.went[p]:
                print(p,'is a failure')
                allWent = False
        if allWent:
            print('????')
            for p in self.went:
                self.went[p] = False
            self.round()
    def checkIfAlive(self,player):
        if len(self.units[player]) == 0:
            del(self.units[player])
            del(self.resources[player])
            del(self.went[player])
            return False
        return True
    def round(self):
        """
        grid = methods.intToList(self.intGrid, self.width)
        print("Lololsdfgosdf")
        print(grid)
        grid = methods.smoothAreas(grid)
        print('qwerttyuiu', grid)
        self.intGrid = list(np.packbits(np.uint8(grid)))
        for i in range(len(self.intGrid)):
            self.intGrid[i] = int(self.intGrid[i])
        """

        
        self.turn += 1
        print('stuff')
        #AI = range(len(self.units))
        AI = range(len(self.units)-self.ai,len(self.units))
        if self.allai:
            AI = range(len(self.units))
        for v in AI:
            Computer.CurrentAI(self,v)
            self.went[v] = True
        setDefaultState(self)
        
        #Gain resources
        for i in self.units:
            for u in self.units[i]:
                print("checking", vars(u))
                if u.state == "resources":#stateData is the type of resource generate
                    self.resources[i][u.stateData] += u.resourceGen[u.stateData]
        #Attack
        hurtList = {}
        hunterList = {}
        for i in self.units:
            for u in self.units[i]:
                if u.state == "attack" and u.stateData: #stateData is target of attack
                    goodToAttack = True
                    target = u.stateData
                    if type(target) == str:
                        target = self.getUnitFromID(target)
                    if 'onlyHit' in u.abilities:
                        if not (target.type in u.abilities['onlyHit']):
                            goodToAttack = False
                    print(vars(u))
                    if goodToAttack and checkRange(u, target) <= u.range:#Check if in range
                        if not (target in hurtList): 
                            hurtList[target] = 0
                            hunterList[target] = u
                        print("HURT",u.name, damageCalc(u, target), target.name)
                        hurtList[target] += damageCalc(u, target)
        print("HUNTER list", hunterList)
        for v in hunterList:
            print(v.name,':', hunterList[v])
        #Heal
        for i in self.units:
            for u in self.units[i]:
                if u.state == "heal" and u.stateData: #stateData is target of heal
                    goodToHeal = True
                    target = u.stateData
                    if type(target) == str:
                        target = self.getUnitFromID(target)
                    if 'onlyHeal' in u.abilities:
                        if not (target.type in u.abilities['onlyHeal']):
                            goodToHeal = False
                    print(vars(u))
                    if goodToHeal and checkRange(u, target) <= u.range:#Check if in range
                        if not (target in hurtList): 
                            hurtList[target] = 0
                        heal = UnitDB[u.name].get('heal') or 5
                        print("Heal",u.name, heal, target.name)
                        hurtList[target] -= heal
        
        for u in hurtList:#Units get hurt/healed
            print(u.name, "took", hurtList[u])
            u.health-=hurtList[u]
        RemoveList = []
        for i in self.units:#Destroy units with 0 or less health & set to max health anyone who is over
            for u in self.units[i]:
                if u.health <= 0:
                    RemoveList.append(u)
                elif u.health > u.maxHealth:
                    u.health = u.maxHealth
        
        for u in RemoveList:#more destroy
            print(u, u.name, 'is destroyed')
            if u.parent:
                par = self.getUnitFromID(u.parent)
                if par:
                    if getattr(par,'maxPopulation',False):
                        par.population = max(0,par.population-1)
            if u in hunterList:
                hunter = hunterList[u]
                print('there is a hunter', hunter.name, hunter)
                if 'takeover' in hunter.abilities:
                    if checkRange(hunter,u) <= 1:
                        hunter.state = 'build'
                        hunter.stateData = [u.position,hunter.abilities['takeover']]
                elif 'charge' in hunter.abilities:
                    print('CHAAAARGEE')
                    if checkRange(hunter,u) <= 1:
                        print('It should work')
                        hunter.state = 'move'
                        hunter.stateData = u.position
                #self.units[hunterList[u]].append(Unit(u.position,u.name))
                #print("WHY DON'T I have RESOURCES", u.name, hunterList[u])
                #self.resources[hunterList[u]]['gold'] += 500
                
            self.units[self.getPlayerfromUnit(u)].remove(u)
        for i in self.units:#Turn off attack of dead targets
            for u in self.units[i]:
                if u.state == "attack":
                    target = u.stateData
                    if type(target) == str:
                        target = self.getUnitFromID(target)
                    if target == None:
                        u.state = None
                        u.stateData = None
                    elif target.health <= 0:
                        u.state = None
                        u.stateData = None
                    """
                    if u.stateData.health <= 0:
                        u.state = None
                        u.stateData = None
                    """
        #Movement
        BlockedSpaces = []
        Grid = methods.intToList(self.intGrid, self.width)
        
        for i in self.units:
            for u in self.units[i]:
                BlockedSpaces.append(u.position)
        while True:
            cont = False
            for i in self.units:
                for u in self.units[i]:
                    if u.state == "move":
                        if checkRange(u, u.stateData) <= u.speed:
                            if not u.stateData in BlockedSpaces:#If open, move
                                water = Grid[u.stateData[1]][u.stateData[0]]
                                if (water == (u.type == 'boat')) or u.type == "aircraft":
                                    BlockedSpaces.remove(u.position)
                                    u.position = u.stateData
                                    u.state = None
                                    u.stateData = None
                                    BlockedSpaces.append(u.position)
                                    cont = True
            if cont:
                continue
            break
        #Build
        for i in self.units:
            for u in self.units[i]:
                if u.state == "build":#State data is list [0] is pos, [1] is name
                    if not u.stateData[0] in BlockedSpaces:#if not blocked
                        affordable = CheckIfGoodToBuild(self, i, u, Grid)#True
                        """
                        for v in UnitDB[u.stateData[1]]['cost']:
                            if self.resources[i][v] < UnitDB[u.stateData[1]]['cost'][v]:#Check each resource
                                affordable = False #If too expensive, ignore build
                        if getattr(u,'maxPopulation',False):
                            if u.population >= u.maxPopulation:
                                affordable = False #Max popultion reached
                        if checkRange(u, u.stateData[0]) > u.range:
                            affordable = False #Can't build out of range
                        t = UnitDB[u.stateData[1]].get('type') or 0
                        if Grid[u.stateData[0][1]][u.stateData[0][0]]:#on Water
                            if t not in ['aircraft', 'boat']:
                                affordable = False #Can't build type on water
                        else:#on land
                            if t == 'boat':
                                affordable = False #Can't build boat on land
                        if affordable and t == 'building':#Can't build buildings near enemy buildings
                            Range = UnitDB[u.stateData[1]].get('range') or 1
                            for v in getRangeCircles(self,u,Range,u.stateData[0], True):
                                unit = self.getAnyUnitFromPos(v[0],v[1])
                                if unit and unit.type == 'building':
                                    if not self.checkFriendly(u,unit):
                                        affordable = False
                        """
                        if affordable:
                            if getattr(u,'maxPopulation',False):
                                u.population += 1
                            cost = UnitDB[u.stateData[1]]['cost']
                            if 'abilities' in UnitDB[u.stateData[1]] and 'costly' in UnitDB[u.stateData[1]]['abilities']:
                                cost = copy.copy(cost)
                                count = getCount(u.stateData[1], i,self)
                                for v in cost:
                                    cost[v] = int(cost[v]*(UnitDB[u.stateData[1]]['abilities']['costly']**count)//5*5)

                            newUnit = Unit(u.stateData[0],u.stateData[1],u.UnitID)
                            self.upgradeUnit(newUnit, i)
                            self.units[i].append(newUnit)

                            for v in cost:#player loses resources
                                self.resources[i][v] -= cost[v]
                            BlockedSpaces.append(u.stateData[0])

                            if 'multibuild' in u.abilities:
                                for k in range(u.abilities['multibuild']):
                                    tiles = getRangeCircles(self, u)
                                    for j in range(len(tiles)):
                                        pos = random.choice(tiles)
                                        if (not pos in BlockedSpaces) and CheckIfGoodToBuild(self, i, u, Grid, pos):
                                            self.units[i].append(Unit(pos,u.stateData[1],u.UnitID))
                                            BlockedSpaces.append(pos)
                                            if getattr(u,'maxPopulation',False):
                                                u.population += 1
                                            break
                                        else:
                                            tiles.remove(pos)
                            
                            u.state = None
                            u.stateData = None

        #Research
        for i in self.units:
            for u in self.units[i]:
                if u.state == "research":#stateData is the tech
                    tech = u.stateData
                    if tech in self.tech[i]:#If they already have the tech, don't research it
                        continue
                    if not tech in self.progress[i]:
                        self.progress[i][tech] = 0
                    self.progress[i][tech] += 1
                    if self.progress[i][tech] >= TechDB[tech]['time']:
                        self.tech[i].append(tech)
                        self.upgradeCurrentUnits(i, tech)
                        u.state = None
                        u.stateData = None
                        del self.progress[i][tech]
        #Capout Resources at 2000
        cap = 2000
        for i in self.resources:
            for v in self.resources[i]:
                if self.resources[i][v] > cap:
                    self.resources[i][v] = cap
        print('MORE stuff')
        
                            


class GameMaker(Game):
    def __init__(self, text):
        #print("TEST", text)
        text = methods.unzipper(text)
        #print(text)
        dictionary = None
        for i in range(20):
            try:
                print("ATTEMPTING")
                dictionary = json.loads(text)
                break
            except json.decoder.JSONDecodeError as e:
                print("THE TEXT", text)
                print('e',e)
                if not e.args[0].startswith("Expecting ',' delimiter:"):
                    raise
                text = ','.join((text[:e.pos], text[e.pos:]))
        else:
            print("Stuff")
            raise Exception("Uhhh....something happened, (delimeter comma thing)") 
        for k, v in dictionary.items():
            if type(v) == dict:
                l = []
                for v2 in v:
                    l.append(v2)
                for v2 in l:
                    v[int(v2)] = v[v2]
                    del(v[v2])
            setattr(self, k, v)
        #print(dictionary)
        for i in self.units:
            for j in range(len(self.units[i])):
                self.units[i][j] = UnitMaker(self.units[i][j])
                if self.units[i][j].state == "attack" and type(self.units[i][j].stateData) == str:
                    print("Okay... I'm going to do the thing")
                    print("thingL:", self.units[i][j].stateData)
                    new = self.getUnitFromID2(self.units[i][j].stateData)
                    print("dfdfjkdrhjdhj")
                    self.units[i][j].stateData = new
