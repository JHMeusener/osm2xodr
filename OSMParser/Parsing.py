#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 10:27:12 2019

@author: jhm
"""
import uuid
from .utils import getCurves, convertLongitudeLatitude, giveHeading, convertTopoMap, giveHeight, setHeights
import numpy as np
from osmread import parse_file, Way, Node
import copy
import pathlib
from .OpenDriveWriting import openDriveRoad, openDriveJunction, openDriveLane, openDriveLaneLink, openDriveRoadLink

class rNode:
    allrNodes = {}
    
    @staticmethod
    def reset():
        rNode.allrNodes = {}
    
    def __init__(self,entity, register = True, debug=False, substractMin=None):
        if debug:
            self.id = str(uuid.uuid1())
            if register: rNode.allrNodes[self.id] = self
            return
        self.id = str(entity.id)
        if register: rNode.allrNodes[self.id] = self
        self.tags = entity.tags
        try:  self.x,self.y = convertLongitudeLatitude(entity.lon, entity.lat)
        except: self.x,self.y = entity.x, entity.y
        try: self.height = giveHeight(self.x, self.y)
        except: self.height = 0.0
        if substractMin is not None:
            self.x -= substractMin[0]
            self.y -= substractMin[2]

        self.Junction = ""
        self.wayList = []
        self._PreWayIdList = []

        self.incomingWays = []   # in der regel 1
        self.incomingrNodes = []
        self.incomingLanes = []
        self.incomingLanesOpposite = []
        self.incomingTurnTags = []

        self.outgoingLanes = []
        self.outgoingLanesOpposite = []
        self.outgoingLanesOppositeTurnTags = []
        self.outgoingrNodes = []
        self.outgoingWays = []

        self.Connections = {}

        self.openDriveElements = {}   # für jede Way Way2 / Way2 Way Verbindung einmal r1rNode, r1Way, r1WayDirection, r1, r2, r3, r4, r4WayDirection, r4Way, r4rNode
        
    def _createJunctionrelevantOpenDriveLaneConnections(self):
        '''Creates openDriveLaneLinks according to self.Connections'''
        if len(self.wayList) < 2:
            return
        else:
            for roadSet in self.openDriveElements.values():
                rNode1,Way,beginningWayDirection,r1,r2,r3,r4,endWayDirection,Way2,rNode2 = roadSet
                if Way in self.Connections: #create Laneconnections for the incoming direction of way if there are any
                        for direction, wayConnections in self.Connections[Way].items():
                            if Way2 in wayConnections:
                                lanelist = wayConnections[Way2] #Waydirection ist im Predecessor schon beachtet. Einzig Roaddirection muss noch einmal beachtete werden
                                #lanelist is always - to + if ways go into each other
                                # always ++ and -- when the ways are in direction
                                # always + to - if ways go away from each other
                                for connection in lanelist:
                                    lanelink = openDriveLaneLink(r1,r2,connection[0] if r1.wayIsOpposite else -connection[0], connection[1] if r2.wayIsOpposite else -connection[1])
                                    for rlink in r1.RoadLinksSuccessor:
                                        if r2.id == rlink.oDriveRoad.id or r2.id == rlink.oDriveRoadPredecessor.id:
                                            rlink.openDriveLaneLinks.append(lanelink)
                                    
                if Way2 in self.Connections:
                        for direction, wayConnections in self.Connections[Way2].items():
                            if Way in wayConnections:
                                lanelist = wayConnections[Way] #Waydirection ist schon beachtet. Einzig Roaddirection muss noch einmal beachtete werden
                                for connection in lanelist:
                                    lanelink = openDriveLaneLink(r2,r1,connection[0] if r2.wayIsOpposite else -connection[0], connection[1] if r1.wayIsOpposite else -connection[1])
                                    for rlink in r1.RoadLinksSuccessor:
                                        if r2.id == rlink.oDriveRoad.id or r2.id == rlink.oDriveRoadPredecessor.id:
                                            rlink.openDriveLaneLinks.append(lanelink)
                #print(r1.RoadLinksSuccessor[0].openDriveLaneLinks)

    def _givePossibleTurnIdxs(self, Way):
        '''Gives the Indexes of the registered Ways with >0 outgoing Lanes'''
        turnIdxToIncoming = []
        turnIdxToOutgoing = []
        if Way in self.incomingWays or Way in self.outgoingWays:
            for incIdx in range(len(self.incomingWays)):
                if Way != self.incomingWays[incIdx]:     # no U-Turn
                    if self.incomingLanesOpposite[incIdx] > 0:  # no Turning in One-Way Streets
                        turnIdxToIncoming.append(incIdx)
            for outIdx in range(len(self.outgoingWays)):
                if Way != self.outgoingWays[outIdx]:     # no U-Turn
                    if self.outgoingLanes[outIdx] > 0:  # no Turning in One-Way Streets
                        turnIdxToOutgoing.append(outIdx)
        return turnIdxToIncoming, turnIdxToOutgoing

    def giveTurnPossibilities(self, incomingWay):
        '''Gives the Angles, Lanes, Ways, rNodes and Directions of all valid Turns from a Way as an incoming Way'''
        turnsInc = []
        turnsOut = []
        selfHeading = 0
        if incomingWay in self.incomingWays: # no turn possibilities for a not really incoming way (way with no incoming lanes)
            if self.incomingLanes[self.incomingWays.index(incomingWay)] == 0:
                return{'Angles':[],'rNodes': [],'Lanes': [],'Ways': [],'WayDirection': []}
        elif incomingWay in self.outgoingWays:
            if self.outgoingLanesOpposite[self.outgoingWays.index(incomingWay)] == 0:
                return{'Angles':[],'rNodes': [],'Lanes': [],'Ways': [],'WayDirection': []}

        incIdx, outIdx = self._givePossibleTurnIdxs(incomingWay)
        if incomingWay in self.incomingWays:
            selfincrNode = self.incomingrNodes[self.incomingWays.index(incomingWay)]
        elif incomingWay in self.outgoingWays:
            selfincrNode = self.outgoingrNodes[self.outgoingWays.index(incomingWay)]
        selfHeading = giveHeading(selfincrNode.x, selfincrNode.y, self.x, self.y) # heading von "incoming" Node to self
        if selfHeading > np.pi:  # weg im bereich -pi + pi normalisieren
            selfHeading -= 2*np.pi
        for i in range(len(incIdx)):
            nodeHeading = giveHeading(self.x, self.y, self.incomingrNodes[incIdx[i]].x, self.incomingrNodes[incIdx[i]].y)
            turn = (nodeHeading - selfHeading)
            if turn > np.pi: turn -= 2*np.pi
            if turn < -np.pi: turn += 2*np.pi
            turnsInc.append(turn)
        for i in range(len(outIdx)):
            nodeHeading = giveHeading(self.x, self.y, self.outgoingrNodes[outIdx[i]].x, self.outgoingrNodes[outIdx[i]].y)
            turn = (nodeHeading - selfHeading)
            if turn > np.pi: turn -= 2*np.pi
            if turn < -np.pi: turn += 2*np.pi
            turnsOut.append(turn)
        return {'Angles':turnsInc+turnsOut, 
                'rNodes': [self.incomingrNodes[i] for i in incIdx]+[self.outgoingrNodes[i] for i in outIdx], 
                'Lanes': [self.incomingLanesOpposite[i] for i in incIdx]+[self.outgoingLanes[i] for i in outIdx],
                'Ways': [self.incomingWays[i] for i in incIdx]+[self.outgoingWays[i] for i in outIdx],
                'WayDirection': [False]*len(turnsInc)+[True]*len(turnsOut)}
    
    def createConnections(self, Way):
        '''Creates Laneconnections ([Lane, successorLane]) of the way for all successors and stores them in self.Connections[Way][Successorway].
        The Laneconnections are already adjusted for Waydirection'''
        # check if way is incoming or outgoing and get the incoming lanes as well as the index
        positiveIncLanes = True
        lanenumbers = 0
        wayIdx = -1
        if Way in self.incomingWays:
            positiveIncLanes = False
            wayIdx = self.incomingWays.index(Way)
            lanenumbers = self.incomingLanes[wayIdx]
        else:
            wayIdx = self.outgoingWays.index(Way)
            lanenumbers = self.outgoingLanesOpposite[wayIdx]
        turnPossibilities = self.giveTurnPossibilities(Way)
        sortangles = turnPossibilities['Angles']
        sortangles.sort()
        if lanenumbers == 0 or sum(turnPossibilities['Lanes']) == 0:
            return
        wayConnections = {}
        for angle in sortangles:
            idx = turnPossibilities['Angles'].index(angle)
            lanesum = 0
            
            for i in range(idx):     # get the lanenumber of the incoming lane
                lanesum += turnPossibilities['Lanes'][i]
                if lanesum > lanenumbers:
                    lanesum = lanenumbers-1      #lanes, die bisher verbraucht wurden
                        
            # ist noch platz für die outgoinglanes?
            if lanesum+turnPossibilities['Lanes'][idx] > lanenumbers:
                lanesum = max(0,lanesum-turnPossibilities['Lanes'][idx])
            laneConnections = []
            for i in range(turnPossibilities['Lanes'][idx]):   #lanes, die hier outgoing sind
                if lanesum+i+1 > lanenumbers: # more lanes to turn into in one Possibility than incoming lanes
                    if len(sortangles) == 1: # merging and splitting Lanes - all Lanes should be accessible
                        lanesum -= 1
                    else:
                        break   # turning into a main street - only use outer lane
                # create Connection
                if positiveIncLanes:  # Way is in OutgoingWays
                    laneConnections.append([lanesum+i+1, -i-1 if turnPossibilities['WayDirection'][idx] else i+1])
                else:
                    laneConnections.append([-lanesum-i-1, -i-1 if turnPossibilities['WayDirection'][idx] else i+1])
            # extra merging lanes
            if turnPossibilities['Lanes'][idx] < lanenumbers and len(self.wayList)==2: 
                for i in range(lanenumbers-turnPossibilities['Lanes'][idx]):
                    # create Connection
                    if positiveIncLanes:  # Way is in OutgoingWays
                        laneConnections.append([turnPossibilities['Lanes'][idx]+i+1, -turnPossibilities['Lanes'][idx] if turnPossibilities['WayDirection'][idx] else turnPossibilities['Lanes'][idx]])
                    else:
                        laneConnections.append([-turnPossibilities['Lanes'][idx]-i-1, -turnPossibilities['Lanes'][idx] if turnPossibilities['WayDirection'][idx] else turnPossibilities['Lanes'][idx]])
            
            wayConnections[turnPossibilities['Ways'][idx]] = laneConnections
        if positiveIncLanes: # Way is in OutgoingWays
            try: self.Connections[Way]["Opposite"] =  wayConnections
            except: 
                self.Connections[Way] = {}
                self.Connections[Way]["Opposite"] =  wayConnections
        else:
            try: self.Connections[Way]["Direction"] =  wayConnections
            except: 
                self.Connections[Way] = {}
                self.Connections[Way]["Direction"] =  wayConnections         

    @staticmethod
    def _connectionID(Way,Way2):
        if str(Way) < str(Way2):
            return str(Way)+'#'+str(Way2)
        else:
            return str(Way2)+'#'+str(Way)

    def createOpenDriveElements(self, r=8):
        '''creates OpendriveElements for all Ways of the Node'''
        for way1 in self.incomingWays:
            for way2 in self.outgoingWays:
                self._createOpenDriveElements(way1, way2, r=r)
            for way2 in self.incomingWays:
                if way1 != way2:
                    self._createOpenDriveElements(way1, way2, r=r)
        for way1 in self.outgoingWays:
            for way2 in self.incomingWays:
                self._createOpenDriveElements(way1, way2, r=r)
            for way2 in self.outgoingWays:
                if way1 != way2:
                    self._createOpenDriveElements(way1, way2, r=r)
        if len(self.outgoingWays+self.incomingWays) == 1:  # Enden
            for way in self.incomingWays:
                self._createOpenDriveElements(way, None, r=r)
            for way in self.outgoingWays:
                self._createOpenDriveElements(None, way, r=r)

    def connectOpenDriveLanes(self):
        self._createJunctionrelevantOpenDriveLaneConnections()
        self.createOpenDriveExternalRoadLinks()

    def _createOpenDriveElements(self, Way,Way2, r=8):
        ''' für jede Way Way2 / Way2 Way Verbindung einmal r1rNode, r1Way, r1WayDirection, r1, r2, r3, r4, r4WayDirection, r4Way, r4rNode   in self.openDriveElements[WayWay2]'''
        if Way is None and Way2 is None:
            return
        else:
            if self._connectionID(Way,Way2) in self.openDriveElements:
                return
            #try: print("creating roadset for Way "+str(Way.OSMId)+" to Way "+str(Way2.OSMId))
            #except: pass
        # get the correct way direction and the corresponding rNodes
        beginningWayDirection = True
        endWayDirection = True
        if Way in self.incomingWays:
            rNode1 = self.incomingrNodes[self.incomingWays.index(Way)]
        elif Way is not None:
            rNode1 = self.outgoingrNodes[self.outgoingWays.index(Way)]
            beginningWayDirection = False
        if Way2 in self.outgoingWays:
            rNode2 = self.outgoingrNodes[self.outgoingWays.index(Way2)]
        elif Way2 is not None:
            rNode2 = self.incomingrNodes[self.incomingWays.index(Way2)]
            endWayDirection = False
        try:
            xstart = (rNode1.x+self.x)/2.0
            ystart = (rNode1.y+self.y)/2.0
        except: pass
        try:
            xend = (rNode2.x+self.x)/2.0
            yend = (rNode2.y+self.y)/2.0
        except: pass

        # create Roads and save them in openDriveElements
        if not Way:
            hdg = giveHeading(self.x, self.y, xend, yend)
            l2length = ((self.x-xend)**2+(self.y-yend)**2)**0.5
            r4 = openDriveRoad(l2length, self.x, self.y, hdg, endWayDirection, geoparam = None, OSMWayTags= Way2.tags)
            r4.heighta = str(giveHeight(self.x,self.y, minRemoved = True))
            r4.heightb = str(-(giveHeight(xend,yend, minRemoved = True) - giveHeight(self.x,self.y, minRemoved = True))/l2length)
            self.openDriveElements[self._connectionID(Way2,None)] = [None,None,beginningWayDirection,None,None,None,r4,endWayDirection,Way2,rNode2]
            return

        if not Way2:
            hdg = giveHeading(xstart,ystart, self.x, self.y)
            l1length = ((xstart-self.x)**2+(ystart-self.y)**2)**0.5
            r1 = openDriveRoad(l1length, xstart, ystart, hdg, beginningWayDirection, geoparam = None, OSMWayTags= Way.tags)
            r1.heighta = str(giveHeight(self.x,self.y, minRemoved = True))
            r1.heightb = str((giveHeight(xstart,ystart, minRemoved = True) - giveHeight(self.x,self.y, minRemoved = True))/l1length)
            self.openDriveElements[self._connectionID(Way,None)] = [rNode1,Way,beginningWayDirection,r1,None,None,None,endWayDirection,None,None]
            return
        
        line1x,line1y, phi, C1start,C1param, C1Heading, lengthC, C2start,C2param, C2Heading, line2x,line2y,theta = getCurves([xstart,self.x,xend],[ystart, self.y, yend], r=r)
        while phi < 0:        # bringe Heading ins positive
            phi += np.pi*2
        while theta < 0:
            theta += np.pi*2
        if phi > np.pi:
            phi = phi - np.pi*2
        if theta > np.pi:
            theta = theta - np.pi*2

        #create roads
        l1length = ((xstart-line1x[1])**2+(ystart-line1y[1])**2)**0.5
        l2length = ((line2x[0]-xend)**2+(line2y[0]-yend)**2)**0.5
        r1 = openDriveRoad(l1length, xstart, ystart, phi, beginningWayDirection, geoparam = None, OSMWayTags= Way.tags)
        if len(self.wayList) > 1:
            r2 = openDriveRoad(lengthC, C1start[0], C1start[1], C1Heading, not endWayDirection, geoparam = C1param, OSMWayTags= Way2.tags)
        else:
            r2 = openDriveRoad(lengthC, C1start[0], C1start[1], C1Heading, not beginningWayDirection, geoparam = C1param, OSMWayTags= Way.tags)
        r3 = openDriveRoad(lengthC, C1start[0], C1start[1], C2Heading, endWayDirection, geoparam = C2param, OSMWayTags= Way2.tags)
        r4 = openDriveRoad(l2length, line2x[0], line2y[0], phi-theta, endWayDirection, geoparam = None, OSMWayTags= Way2.tags)

        r1.heighta = str(giveHeight(xstart, ystart, minRemoved = True))
        r1.heightb = str(-(giveHeight(xstart,ystart, minRemoved = True) - giveHeight(line1x[1],line1y[1], minRemoved = True))/l1length)
        r2.heighta = str(giveHeight(C1start[0], C1start[1], minRemoved = True))
        r2.heightb = str(-(giveHeight(C1start[0], C1start[1], minRemoved = True) - giveHeight(line1x[1],line1y[1], minRemoved = True))/lengthC)
        r3.heighta = str(giveHeight(C1start[0], C1start[1], minRemoved = True))
        r3.heightb = str(-(giveHeight(C1start[0], C1start[1], minRemoved = True) - giveHeight(line2x[0], line2y[0], minRemoved = True))/lengthC)
        r4.heighta = str(giveHeight( line2x[0], line2y[0], minRemoved = True))
        r4.heightb = str(-(giveHeight( line2x[0], line2y[0], minRemoved = True) - giveHeight(xend, yend, minRemoved = True))/l2length)

        if len(self.wayList) > 1:  # junction
            junction = openDriveJunction.giveJunction(Way, self)
            junction.register(r1, r1=True)
            junction = openDriveJunction.giveJunction(Way2, self)
            junction.register(r4, r1=False)

        #r1rNode, r1Way, r1WayDirection, r1, r2, r3, r4, r4WayDirection, r4Way, r4rNode
        self.openDriveElements[self._connectionID(Way,Way2)] = [rNode1,Way,beginningWayDirection,r1,r2,r3,r4,endWayDirection,Way2,rNode2]

    def createOpenDriveLanesAndInternalRoadConnections(self):
        for roadSet in self.openDriveElements.values():
            rNode1,Way,beginningWayDirection,r1,r2,r3,r4,endWayDirection,Way2,rNode2 = roadSet
            #create lanes for non Junctions
            if len(self.wayList) < 2:  
                    #create roads lanes
                    if Way:
                        for laneId in range(1,Way.laneNumberDirection+1):
                                r1.lanesRight.append(openDriveLane(-laneId if beginningWayDirection else laneId, r1))
                        if len(r1.lanesRight) > 0: r1.lanesRight[-1].roadmark = "solid"
                        for laneId in range(1,Way.laneNumberOpposite+1):
                                r1.lanesLeft.append(openDriveLane(laneId if beginningWayDirection else -laneId, r1))
                        if len(r1.lanesLeft) > 0: r1.lanesLeft[-1].roadmark = "solid"
                        r1.laneMiddle.append(openDriveLane(0, r1))
                        r1.laneMiddle[0].roadmark = "solid"
                        if len(r1.lanesLeft) == 1 and len(r1.lanesRight) == 1:
                            r1.laneMiddle[0].roadmark = "broken"
                        ## entgegengesetzte Kurve
                        #create roads lanes
                    if r2:
                        for laneId in range(1,Way.laneNumberDirection+1):
                                r2.lanesRight.append(openDriveLane(laneId if beginningWayDirection else -laneId, r2))
                        if len(r2.lanesRight) > 0: r2.lanesRight[-1].roadmark = "solid"
                        for laneId in range(1,Way.laneNumberOpposite+1):
                                r2.lanesLeft.append(openDriveLane(-laneId if beginningWayDirection else laneId, r2))
                        if len(r2.lanesLeft) > 0: r2.lanesLeft[-1].roadmark = "solid"
                        r2.laneMiddle.append(openDriveLane(0, r2))
                        r2.laneMiddle[0].roadmark = "solid"
                        if len(r2.lanesLeft) == 1 and len(r2.lanesRight) == 1:
                            r2.laneMiddle[0].roadmark = "broken"
                        ## Kurve zum nachfolger
                        #create roads lanes
                    if r3:
                        for laneId in range(1,Way2.laneNumberDirection+1):
                                r3.lanesRight.append(openDriveLane(-laneId if endWayDirection else laneId, r3))
                        if len(r3.lanesRight) > 0: r3.lanesRight[-1].roadmark = "solid"
                        for laneId in range(1,Way2.laneNumberOpposite+1):
                                r3.lanesLeft.append(openDriveLane(laneId if endWayDirection else -laneId, r3))
                        r3.laneMiddle.append(openDriveLane(0, r3))
                        if len(r3.lanesLeft) > 0: r3.lanesLeft[-1].roadmark = "solid"
                        r3.laneMiddle[0].roadmark = "solid"
                        if len(r3.lanesLeft) == 1 and len(r3.lanesRight) == 1:
                            r3.laneMiddle[0].roadmark = "broken"
                    if Way2:
                        ## Gerade zum nachfolger
                        #create roads lanes
                        for laneId in range(1,Way2.laneNumberDirection+1):
                                r4.lanesRight.append(openDriveLane(-laneId if endWayDirection else laneId, r4))
                        if len(r4.lanesRight) > 0: r4.lanesRight[-1].roadmark = "solid"
                        for laneId in range(1,Way2.laneNumberOpposite+1):
                                r4.lanesLeft.append(openDriveLane(laneId if endWayDirection else -laneId, r4))
                        r4.laneMiddle.append(openDriveLane(0, r4))
                        if len(r4.lanesLeft) > 0: r4.lanesLeft[-1].roadmark = "solid"
                        r4.laneMiddle[0].roadmark = "solid"
                        if len(r4.lanesLeft) == 1 and len(r4.lanesRight) == 1:
                            r4.laneMiddle[0].roadmark = "broken"


            else:   #lane und Junction creation for Junction
                        for laneId in range(1,Way.laneNumberDirection+1):
                                r1.lanesRight.append(openDriveLane(-laneId if beginningWayDirection else laneId, r1))
                        if len(r1.lanesRight) > 0: r1.lanesRight[-1].roadmark = "solid"
                        for laneId in range(1,Way.laneNumberOpposite+1):
                                r1.lanesLeft.append(openDriveLane(laneId if beginningWayDirection else -laneId, r1))
                        if len(r1.lanesLeft) > 0: r1.lanesLeft[-1].roadmark = "solid"
                        r1.laneMiddle.append(openDriveLane(0, r1))
                        r1.laneMiddle[0].roadmark = "solid"
                        if len(r1.lanesLeft) == 1 and len(r1.lanesRight) == 1:
                            r1.laneMiddle[0].roadmark = "broken"
                        ## entgegengesetzte Kurve
                        #create roads lanes
                        for laneId in range(1,Way2.laneNumberDirection+1):
                                r2.lanesRight.append(openDriveLane(laneId if endWayDirection else -laneId, r2))
                                if len(r2.lanesRight) > 0: r2.lanesRight[-1].roadmark = "none"
                        for laneId in range(1,Way2.laneNumberOpposite+1):
                                r2.lanesLeft.append(openDriveLane(-laneId if endWayDirection else laneId, r2))
                                if len(r2.lanesLeft) > 0: r2.lanesLeft[-1].roadmark = "none"
                        r2.laneMiddle.append(openDriveLane(0, r2))
                        r2.laneMiddle[0].roadmark = "none"
                        ## Kurve zum nachfolger
                        #create roads lanes
                        for laneId in range(1,Way2.laneNumberDirection+1):
                                r3.lanesRight.append(openDriveLane(-laneId if endWayDirection else laneId, r3))
                                if len(r3.lanesRight) > 0: r3.lanesRight[-1].roadmark = "none"
                        for laneId in range(1,Way2.laneNumberOpposite+1):
                                r3.lanesLeft.append(openDriveLane(laneId if endWayDirection else -laneId, r3))
                                if len(r3.lanesLeft) > 0: r3.lanesLeft[-1].roadmark = "none"
                        r3.laneMiddle.append(openDriveLane(0, r3))
                        r3.laneMiddle[0].roadmark = "none"
                        ## Gerade zum nachfolger
                        for laneId in range(1,Way2.laneNumberDirection+1):
                                r4.lanesRight.append(openDriveLane(-laneId if endWayDirection else laneId, r4))
                        if len(r4.lanesRight) > 0: r4.lanesRight[-1].roadmark = "solid"
                        for laneId in range(1,Way2.laneNumberOpposite+1):
                                r4.lanesLeft.append(openDriveLane(laneId if endWayDirection else -laneId, r4))
                        r4.laneMiddle.append(openDriveLane(0, r4))
                        if len(r4.lanesLeft) > 0: r4.lanesLeft[-1].roadmark = "solid"
                        r4.laneMiddle[0].roadmark = "solid"
                        if len(r4.lanesLeft) == 1 and len(r4.lanesRight) == 1:
                            r4.laneMiddle[0].roadmark = "broken"
            #create internal Roadlinks   -> Roadlinks für interCreatorVerbindungen brauchen bereits bestehende Straßen
            if Way is not None and Way2 is not None:
                r1r2 = openDriveRoadLink(r1, r2, 'end', 'end')
                r1.RoadLinksSuccessor.append(r1r2)
                r2.RoadLinksSuccessor.append(r1r2)
                r2r3 = openDriveRoadLink(r2, r3, 'start', 'start')
                r2.RoadLinksPredecessor.append(r2r3)
                r3.RoadLinksPredecessor.append(r2r3)
                r3r4 = openDriveRoadLink(r3, r4, 'end', 'start')
                r3.RoadLinksSuccessor.append(r3r4)
                r4.RoadLinksPredecessor.append(r3r4)
            
            if False:
                print("Node "+str(self.id)+" where Way "+str(Way.OSMId)+" meets Way "+str(Way2.OSMId)+" has following Lanes:")
                print("r1:")
                print("   left:")
                for lane in r1.lanesLeft: print("      "+str(lane.id))
                print("    right:")
                for lane in r1.lanesRight: print("      "+str(lane.id))
                print("r2:")
                print("    right:")
                for lane in r2.lanesRight: print("      "+str(lane.id))
                print("   left:")
                for lane in r2.lanesLeft: print("      "+str(lane.id))
                print("r3:")
                print("   left:")
                for lane in r3.lanesLeft: print("      "+str(lane.id))
                print("    right:")
                for lane in r3.lanesRight: print("      "+str(lane.id))
                print("r4:")
                print("   left:")
                for lane in r4.lanesLeft: print("      "+str(lane.id))
                print("    right:")
                for lane in r4.lanesRight: print("      "+str(lane.id))

    def createOpenDriveExternalRoadLinks(self):
        '''Creates openDriveRoadLinks to Predecessor and Successor of the RoadSets and Connects the Roads'''
        for roadSet in self.openDriveElements.values():
            rNode1,Way,beginningWayDirection,r1,r2,r3,r4,endWayDirection,Way2,rNode2 = roadSet
            # create r1 Predecessor Connections and Lanes
            if rNode1:
                # get all PredecessorRoadSets that match self
                for PredecessorRoadSet in rNode1.openDriveElements.values():
                    if self in PredecessorRoadSet:
                        if PredecessorRoadSet.index(self) == 0:  # Predecessor to Predecessor link
                            # create RoadLink and LaneLinks
                            noExistingRoadLink = True
                            for rlp in r1.RoadLinksPredecessor:
                                if rlp.oDriveRoad.id == PredecessorRoadSet[3].id or rlp.oDriveRoadPredecessor.id == PredecessorRoadSet[3].id:
                                    noExistingRoadLink = False
                            if noExistingRoadLink:
                                rl = openDriveRoadLink(PredecessorRoadSet[3],r1,'start', 'start')
                                r1.RoadLinksPredecessor.append(rl)
                                PredecessorRoadSet[3].RoadLinksPredecessor.append(rl)
                        if PredecessorRoadSet.index(self) == 9: # Successor to Predecessor Link
                            #create RoadLink and LaneLinks
                            noExistingRoadLink = True
                            for rlp in r1.RoadLinksPredecessor:
                                if rlp.oDriveRoad.id == PredecessorRoadSet[6].id or rlp.oDriveRoadPredecessor.id == PredecessorRoadSet[6].id:
                                    noExistingRoadLink = False
                            if noExistingRoadLink:
                                rl = openDriveRoadLink(PredecessorRoadSet[6],r1,'end', 'start')
                                r1.RoadLinksPredecessor.append(rl)
                                PredecessorRoadSet[6].RoadLinksSuccessor.append(rl)
            if rNode2:
                for SuccessorRoadSet in rNode2.openDriveElements.values():
                    if self in SuccessorRoadSet:
                        if SuccessorRoadSet.index(self) == 0: #Predecessor to Successor Link
                            noExistingRoadLink = True
                            for rlp in r4.RoadLinksSuccessor:
                                if rlp.oDriveRoad.id == SuccessorRoadSet[3].id or rlp.oDriveRoadPredecessor.id == SuccessorRoadSet[3].id:
                                    noExistingRoadLink = False
                            if noExistingRoadLink:
                                rl = openDriveRoadLink(r4,SuccessorRoadSet[3],'start', 'end')
                                r4.RoadLinksSuccessor.append(rl)
                                SuccessorRoadSet[3].RoadLinksPredecessor.append(rl)
                        if SuccessorRoadSet.index(self) == 9: # Successor to Successor Link
                            noExistingRoadLink = True
                            for rlp in r4.RoadLinksSuccessor:
                                if rlp.oDriveRoad.id == SuccessorRoadSet[6].id or rlp.oDriveRoadPredecessor.id == SuccessorRoadSet[6].id:
                                    noExistingRoadLink = False
                            if noExistingRoadLink:
                                rl = openDriveRoadLink(r4,SuccessorRoadSet[6],'end', 'end')
                                r4.RoadLinksSuccessor.append(rl)
                                SuccessorRoadSet[6].RoadLinksSuccessor.append(rl)

class OSMPreWay:
    allWays = {}

    @staticmethod
    def reset():
        OSMPreWay.allWays = {}
        
    def __init__(self,entity, register = True, debug=False):
        if debug:
            self.id = str(uuid.uuid1())
            if register:
                OSMPreWay.allWays[self.id] = self
            return
        self.id = str(entity.id)
        if register:
            OSMPreWay.allWays[self.id] = self
        self.tags = entity.tags
        self.rNodes = []
        
        for node in entity.nodes:
            if str(node) not in rNode.allrNodes:
                continue
            self.rNodes.append(rNode.allrNodes[str(node)].id)
        if len(self.rNodes) > 1:
            for node in entity.nodes:
                   rNode.allrNodes[str(node)]._PreWayIdList.append(str(self.id))
            
    def _evaluate(self):
        startIdx = 0
        endIdx = -1
        if len(self.rNodes) < 2:
            return
        lastIdx = -1
        for rNodeId in self.rNodes:
            node = rNode.allrNodes[rNodeId]
            idx = self.rNodes.index(rNodeId)
            if idx < lastIdx: #straße geht im Kreis - es wurde die vorherige node gefunden
                if startIdx == lastIdx: # letzte straße war ein neubeginn
                    idx = lastIdx+1  # es hat eh eine neue straße angefangen
                else:
                    #create fake mergeRoad
                    idx = lastIdx
                    endIdx = idx+1
                    OSMWay(self.id, self.tags, self.rNodes[startIdx:endIdx], self.rNodes[startIdx], self.rNodes[endIdx-1])
                    startIdx = idx
                    idx = lastIdx+1
            if len(node._PreWayIdList) > 1:    # dies wird eine Junction - Weg muss gesplittet werden
                if idx == startIdx or idx == endIdx-1:
                    continue
                else:
                    endIdx = idx+1
                    OSMWay(self.id, self.tags, self.rNodes[startIdx:endIdx], self.rNodes[startIdx], self.rNodes[endIdx-1])
                    startIdx = idx
            lastIdx = idx
        if endIdx < len(self.rNodes):
            endIdx = len(self.rNodes)
            OSMWay(self.id, self.tags, self.rNodes[startIdx:endIdx], self.rNodes[startIdx], self.rNodes[endIdx-1])

        
        
class OSMWay:
    allWays = {}
    
    @staticmethod
    def reset():
        OSMWay.allWays = {}
        
    def __init__(self,OSMid, tags, OSMNodes, StartrNode, EndrNode, register = True, debug=False):
        
        self.id = str(uuid.uuid1())
        if debug:
            if register:
                OSMWay.allWays[self.id] = self
            return
        self.OSMId = OSMid
        if register:
            OSMWay.allWays[self.id] = self
        self.tags = tags
        self.OSMNodes = OSMNodes
        
        self.laneNumberDirection = -1
        self.laneNumberOpposite = -1     
        
        self.K1rNode = EndrNode   # end
        self.K2rNode = StartrNode   # start
        
        self.K1Links = []
        self.K2Links = []
        
        self.K1_turnLanesDirection = []
        self.K1_ConnectionsTurnLanesDirection = []
        self.K1_incomingLanesFromK1 = []
        self.K2_turnLanesOpposite = []
        self.K2_ConnectionsTurnLanesOpposite = []
        self.K2_incomingLanesFromK2 = []
        self.checkLanes()
        previousrNode = None
        if len(self.OSMNodes) > 1:
            for nodeid in self.OSMNodes:
                node = rNode.allrNodes[nodeid]
                node.wayList.append(self)
                if previousrNode is not None:
                    previousrNode.outgoingrNodes.append(node)
                    previousrNode.outgoingWays.append(self)
                    previousrNode.outgoingLanes.append(self.laneNumberDirection)
                    previousrNode.outgoingLanesOpposite.append(self.laneNumberOpposite)
                    previousrNode.outgoingLanesOppositeTurnTags.append(self.K2_turnLanesOpposite)
                    node.incomingrNodes.append(previousrNode)
                    node.incomingWays.append(self)
                    node.incomingLanes.append(self.laneNumberDirection)
                    node.incomingLanesOpposite.append(self.laneNumberOpposite)
                    node.incomingTurnTags.append(self.K1_turnLanesDirection)
                    if previousrNode:
                        if len(previousrNode.wayList) > 1:
                            assert len(previousrNode.wayList) == len(previousrNode.incomingWays)+len(previousrNode.outgoingWays)
                    if len(node.wayList) > 1:
                        assert len(node.wayList) == len(node.incomingWays)+len(node.outgoingWays)
                previousrNode = node
        
        self.prepareConnections()
        
    def prepareConnections(self):
        if len(self.K1_turnLanesDirection) < self.laneNumberDirection:
            self.K1_turnLanesDirection = [""]*self.laneNumberDirection
        if len(self.K2_turnLanesOpposite) < self.laneNumberOpposite:
            self.K2_turnLanesOpposite = [""]*self.laneNumberOpposite
        
        for i in range(self.laneNumberDirection):
            #self.K1_turnLanesDirection.append([])
            self.K2_incomingLanesFromK2.append([])
            self.K1_ConnectionsTurnLanesDirection.append([])
        for i in range(self.laneNumberOpposite):
            self.K1_incomingLanesFromK1.append([])
            #self.K2_turnLanesOpposite.append([])
            self.K2_ConnectionsTurnLanesOpposite.append([])
        
    def checkLanes(self):
        '''
        checks how many Lanes this street should have
        '''
        #laneNumberDirection und laneNumberOpposite sind die groben Uebersichten.
        laneNumberDirection = -1
        laneNumberOpposite = -1
        self.K1_turnLanesDirection = []
        self.K2_turnLanesOpposite = []
        lanes = -1
        oneWay = False
        try:
            if 'yes' in self.tags["oneway"]:
                oneWay = True
                #print("oneway found")
        except:  pass
        
        try:
            lanes = int(self.tags["lanes"])
            #print("lanes found")
        except: pass
        try:
            laneNumberDirection = int(self.tags["lanes:forward"])
            #print("lanes:forward found")
        except: pass
        try:
            laneNumberOpposite = int(self.tags["lanes:backward"])
            #print("lanes:backward found")
        except: pass
        try: self.K1_turnLanesDirection = self.tags["turn:lanes:forward"].replace("slight_left","slight_l").replace("slight_right","slight_r").replace("merge_to_right","merge_r").replace("merge_to_left", "merge_l").split("|")
        except: 
            try: self.K1_turnLanesDirection = self.tags["turn:lanes"].replace("slight_left","slight_l").replace("slight_right","slight_r").replace("merge_to_right","merge_r").replace("merge_to_left", "merge_l").split("|")
            except: pass
        try:self.K2_turnLanesOpposite = self.tags["turn:lanes:backward"].replace("slight_left","slight_l").replace("slight_right","slight_r").replace("merge_to_right","merge_r").replace("merge_to_left", "merge_l").split("|")
        except: pass
        if lanes > 0 and laneNumberDirection + laneNumberOpposite == lanes:  #best case
            #print("all clear")
            self.laneNumberDirection = laneNumberDirection
            self.laneNumberOpposite = laneNumberOpposite
        if lanes > 0 and oneWay:
            laneNumberOpposite = 0
            laneNumberDirection = lanes
            #print("all clear")
            self.laneNumberDirection = laneNumberDirection
            self.laneNumberOpposite = laneNumberOpposite
            return 
        if laneNumberDirection > 0 and oneWay:
            #print("all clear")
            lanes = laneNumberDirection
            self.laneNumberDirection = laneNumberDirection
            self.laneNumberOpposite = laneNumberOpposite
            return
        if laneNumberDirection > 0 and laneNumberOpposite>0:
            #print("all clear")
            lanes = laneNumberDirection + laneNumberOpposite
            self.laneNumberDirection = laneNumberDirection
            self.laneNumberOpposite = laneNumberOpposite
            return 
        if (len(self.K1_turnLanesDirection) > 0 or len(self.K2_turnLanesOpposite) > 0) and lanes == -1:
            lanes = len(self.K1_turnLanesDirection) + len(self.K2_turnLanesOpposite)
            self.laneNumberDirection = len(self.K1_turnLanesDirection)
            self.laneNumberOpposite = len(self.K2_turnLanesOpposite)
            return
        if lanes > 0 and laneNumberDirection >= 0:
            laneNumberOpposite = lanes - laneNumberDirection
        if lanes > 0 and laneNumberOpposite >= 0:
            laneNumberDirection = lanes - laneNumberOpposite
            self.laneNumberDirection = laneNumberDirection
            self.laneNumberOpposite = laneNumberOpposite
            return
        if lanes == -1:
            lanes = 1 if oneWay else 2
        laneNumberDirection = lanes if oneWay else 1
        laneNumberOpposite = 0 if oneWay else 1
        if len(self.K1_turnLanesDirection) > 0:
            laneNumberDirection = len(self.K1_turnLanesDirection)
            laneNumberOpposite = lanes-laneNumberDirection
        if len(self.K2_turnLanesOpposite) > 0:
            laneNumberOpposite = len(self.K2_turnLanesOpposite)
            laneNumberDirection = lanes-laneNumberOpposite
        self.laneNumberDirection = laneNumberDirection
        self.laneNumberOpposite = laneNumberOpposite

def parseAll(pfad, bildpfad = None, substractMin=True, minimumHeight = 0.0, maximumHeight = 100.0, curveRadius=8):
    global topoParameter
    setHeights(minimumHeight, maximumHeight)
    topoParameter = convertTopoMap(bildpfad, pfad)
    minLongitude = -1
    maxLongitude = 9
    minLatitude = -1
    maxLatitude = 55
    #create rNodedict with counter
    for entity in parse_file(pfad):
        if isinstance(entity, Node):
            #if minLongitude <entity.lon< maxLongitude and minLatitude <entity.lat< maxLatitude:   # approximate longitude and latitude of Wuppertal
                 rNode(entity, substractMin=topoParameter)
    #create streetrNodedict and count rNodeuse
    for entity in parse_file(pfad):
        if isinstance(entity, Way):
            for word in ["highway"]:#, "lanes", "oneway", "cycleway", "foot", "sidewalk",  "footway"]:
                if word in entity.tags and not "stairs" in entity.tags["highway"] and not "steps" in entity.tags["highway"] and not  "pedestrian" in entity.tags["highway"] and not "elevator" in entity.tags["highway"] and not "footway" in entity.tags["highway"] and not "bridleway" in entity.tags["highway"] and not "cycleway" in entity.tags["highway"] and not "path" in entity.tags["highway"]:
                    OSMPreWay(entity)
    for preWay in OSMPreWay.allWays.values():
        preWay._evaluate()
    for node in rNode.allrNodes.values():
        for way in node.incomingWays:
            node.createConnections(way)
        for way in node.outgoingWays:
            node.createConnections(way)
    for node in rNode.allrNodes.values():
        node.createOpenDriveElements(r=curveRadius)
        node.createOpenDriveLanesAndInternalRoadConnections() 
    for node in rNode.allrNodes.values():
        node.connectOpenDriveLanes()

def _test_nodes(nodes, ways):
    
    for entity in nodes:
        rNode(entity)
    for entity in ways:
        OSMPreWay(entity)
    for preWay in OSMPreWay.allWays.values():
        preWay._evaluate()
    for node in rNode.allrNodes.values():
        for way in node.incomingWays:
            node.createConnections(way)
        for way in node.outgoingWays:
            node.createConnections(way)
    for node in rNode.allrNodes.values():
        node.createOpenDriveElements(r=curveRadius)
        node.createOpenDriveLanesAndInternalRoadConnections() 
    for node in rNode.allrNodes.values():
        node.connectOpenDriveLanes()
    for node in rNode.allrNodes.values():
        printNodeInfo(node)

def printNodeInfo(node):
    print("node: "+str(node.id)+" has incomingWays: ")
    print([way.OSMId for way in node.incomingWays])
    print("with lanes:")
    print(list(zip( node.incomingLanes, node.incomingLanesOpposite)))
    print("has outgoingWays: ")
    print([way.OSMId for way in node.outgoingWays])
    print("with lanes:")
    print(list(zip(node.outgoingLanes, node.outgoingLanesOpposite)))
    for way in node.incomingWays:
        print("      Incoming way "+str(way.OSMId)+" has Turnpossibilities: ")
        turndic = node.giveTurnPossibilities(way)
        print("           Into way    "+str([w.OSMId for w in turndic["Ways"]]))
        print("           with Angle: "+str([a/np.pi*180.0 for a in turndic["Angles"]]))
        print("           with Lanes: "+str(turndic["Lanes"]))
        print("           with direc: "+str(turndic['WayDirection']))
        print("           This gives Connections:")
        print("                In Direction:")
        for w2 in turndic["Ways"]:
            print("                    to Way: "+str(w2.OSMId))                
            try: laneconnect = node.Connections[way]["Direction"][w2]
            except: laneconnect = ""
            print("                       Lanes: "+str(laneconnect))
        print("                In Opposite:")
        for w2 in turndic["Ways"]:
            print("                    to Way: "+str(w2.OSMId))                
            try: laneconnect = node.Connections[way]["Opposite"][w2]
            except: laneconnect = ""
            print("                       Lanes: "+str(laneconnect))
    for way in node.outgoingWays:
        print("      Outgoing way "+str(way.OSMId)+" has Turnpossibilities: ")
        turndic = node.giveTurnPossibilities(way)
        print("           Into way    "+str([w.OSMId for w in turndic["Ways"]]))
        print("           with Angle: "+str([a/np.pi*180.0 for a in turndic["Angles"]]))
        print("           with Lanes: "+str(turndic["Lanes"]))
        print("           with direc: "+str(turndic['WayDirection']))
        print("           This gives Connections:")
        print("                In Direction:")
        for w2 in turndic["Ways"]:
            print("                    to Way: "+str(w2.OSMId))                
            try: laneconnect = node.Connections[way]["Direction"][w2]
            except: laneconnect = ""
            print("                       Lanes: "+str(laneconnect))
        print("                In Opposite:")
        for w2 in turndic["Ways"]:
            print("                    to Way: "+str(w2.OSMId))                
            try: laneconnect = node.Connections[way]["Opposite"][w2]
            except: laneconnect = ""
            print("                       Lanes: "+str(laneconnect))
           
