#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 10:27:12 2019

@author: jhm
"""
import uuid
from .utils import getCurves, convertLongitudeLatitude
import numpy as np
from osmread import parse_file, Way, Node
import copy

def parseAll(pfad):
    minLongitude = -1
    maxLongitude = 9
    minLatitude = -1
    maxLatitude = 55
    #create Nodedict with counter
    for entity in parse_file(pfad):
        if isinstance(entity, Node):
            if minLongitude <entity.lon< maxLongitude and minLatitude <entity.lat< maxLatitude:   # approximate longitude and latitude of Wuppertal
                OSMNode(entity)
    #create streetnodedict and count nodeuse
    for entity in parse_file(pfad):
        if isinstance(entity, Way):
            for word in ["highway"]:#, "lanes", "oneway", "cycleway", "foot", "sidewalk",  "footway"]:
                if word in entity.tags and not "stairs" in entity.tags["highway"] and not "steps" in entity.tags["highway"] and not  "pedestrian" in entity.tags["highway"] and not "elevator" in entity.tags["highway"] and not "footway" in entity.tags["highway"] and not "bridleway" in entity.tags["highway"] and not "cycleway" in entity.tags["highway"] and not "path" in entity.tags["highway"]:
                    OSMPreWay(entity)
    for preWay in OSMPreWay.allWays.values():
        preWay._evaluate()
    for node in OSMNode.allOSMNodes.values():
        node._evaluate()


class OSMNode:
    allOSMNodes = {}
    
    @staticmethod
    def reset():
        OSMNode.allOSMNodes = {}
    
    def __init__(self,entity, register = True, debug=False):
        if debug:
            self.id = str(uuid.uuid1())
            if register:
                OSMNode.allOSMNodes[self.id] = self
            return
        self.id = str(entity.id)
        if register:
            OSMNode.allOSMNodes[self.id] = self
        self.tags = entity.tags
        self.x = 0
        self.y = 0
        try:
            self.x,self.y = convertLongitudeLatitude(entity.lon, entity.lat)
        except:
            self.x,self.y = entity.x, entity.y
            
        self.isJunction = False
        self.idJunction = ""
        self.wayIDList = []
        self.PreWayIdList = []
        self.incomingWays = []   # in der regel 1
        self.incomingLanes = []
        self.outgoingLanes = []
        self.lanespecificWay = []
        self.outgoingWays = []   # in der regel 1
        self.incomingNodes = []   #in der regel 1
        self.outgoingNodes = []   #in der regel 1
        
                
        
    def _evaluate(self):
        if len(self.wayIDList) > 1:
            self.isJunction = True
            j = OSMJunction(self)
            self.idJunction = j.id
            incways = self.incomingWays
            incnodes = self.incomingNodes
            outways = self.outgoingWays
            outnodes = self.outgoingNodes
            
            idx2min = 0
            nodes = incnodes + outnodes
            ways = incways + outways
            
            for idx1 in range(len(ways)):
                for idx2 in range(len(ways)):
                    if idx2 < idx2min or idx1 == idx2:
                        continue
                    OSMNodeLink(nodes[idx1],
                                True if idx1 < len(incways) else False,
                                ways[idx1],
                                self.id,
                                nodes[idx2],
                                True if idx2 < len(incways) else False,
                                ways[idx2])
                    
                idx2min +=1
        elif len(self.wayIDList) == 1:    # ENDNodes
            if self.id not in OSMNodeLink.nodes:
                if len(self.outgoingNodes) == 1:
                    #predecessorNodeid, predecessorincoming, predecessorway, nodeid, successorNodeid, successorincoming, successorway, register
                    OSMNodeLink(self.outgoingNodes[0],
                                False,
                                self.wayIDList[0],
                                self.id,
                                "None",
                                True,
                                "None")
                if len(self.incomingNodes) == 1:
                    #predecessorNodeid, predecessorincoming, predecessorway, nodeid, successorNodeid, successorincoming, successorway, register
                    OSMNodeLink(self.incomingNodes[0],
                                True,
                                self.wayIDList[0],
                                self.id,
                                "None",
                                True,
                                "None")



           
class OSMJunction(OSMNode):
    allJunctions = {}
    
    @staticmethod
    def reset():
        OSMJunction.allJunctions = {}
        
    def __init__(self, entity, register = True, debug=False):
        super(OSMJunction,self).__init__(entity,register = False, debug = debug)
        self.wayIDList = entity.wayIDList
        self.x = entity.x
        self.y = entity.y
        self.node = entity
        self.id = entity.id
        self.tags = entity.tags
        self.incomingNodes = entity.incomingNodes
        self.incomingWays = entity.incomingWays
        self.outgoingWays = entity.outgoingWays
        self.outgoingNodes = entity.outgoingNodes
        self.isJunction = True
        if register:
            OSMJunction.allJunctions[str(entity.id)] = self
    


class OSMNodeLink:
    links = {}
    nodes = {}

    @staticmethod
    def reset():
        OSMNodeLink.links = {}
        OSMNodeLink.nodes = {}
        
    def __init__(self, predecessorNodeid, predecessorincoming, predecessorway, nodeid, successorNodeid, successorincoming, successorway, register = True, debug = False):
        self.id = str(uuid.uuid1())
        self.nodeid = str(nodeid)
        
        if register:
            OSMNodeLink.links[self.id] = self
            if str(nodeid) in OSMNodeLink.nodes:
                OSMNodeLink.nodes[nodeid].append(self.id)
            else:
                OSMNodeLink.nodes[nodeid] = [self.id]
        
        self.predecessorid = str(predecessorNodeid)
        self.successorid = str(successorNodeid)
        
        self.predecessorIsIncoming = predecessorincoming
        self.predecessorway = str(predecessorway)
        
        self.successorIsIncoming = successorincoming
        self.successorway = str(successorway)
        
        self.x = OSMNode.allOSMNodes[self.nodeid].x
        self.y = OSMNode.allOSMNodes[self.nodeid].y
        
        
        self.xstart = -1
        self.ystart = -1
        self.xend = -1
        self.yend = -1

        if self.predecessorid != 'None':
            self.xstart = (OSMNode.allOSMNodes[self.predecessorid].x + OSMNode.allOSMNodes[self.nodeid].x ) /2.0
            self.ystart = (OSMNode.allOSMNodes[self.predecessorid].y + OSMNode.allOSMNodes[self.nodeid].y ) /2.0
        if self.successorid != 'None':
            self.xend = (OSMNode.allOSMNodes[self.successorid].x + OSMNode.allOSMNodes[self.nodeid].x ) /2.0
            self.yend = (OSMNode.allOSMNodes[self.successorid].y + OSMNode.allOSMNodes[self.nodeid].y ) /2.0
        
        line1, phi, c1value, C1Heading, length, c2value, C2Heading, line2,theta = getCurves([self.xstart,self.x,self.xend],[self.ystart, self.y, self.yend], r=8)
        while phi < 0:        # bringe Heading ins positive
            phi += np.pi*2
        while theta < 0:
            theta += np.pi*2
        if phi > np.pi:
            phi = phi - np.pi*2
        if theta > np.pi:
            theta = theta - np.pi*2
        self.winkel = theta
        self.line1_xstart = line1[0][0]
        self.line1_xend = line1[0][1]
        self.line1_ystart = line1[1][0]
        self.line1_yend = line1[1][1]
        self.line1_Hdg = phi
        self.line2_Hdg = phi-theta
        self.line2_xstart = line2[0][0]
        self.line2_xend = line2[0][1]
        self.line2_ystart = line2[1][0]
        self.line2_yend = line2[1][1]
        self.c1_hdg = C1Heading
        self.c2_hdg = C2Heading
        self.clength = length
        self.c_xstart = c1value[0][0]
        self.c_ystart = c1value[0][1]
        self.c1_param = c1value[1][2]
        self.c2_param = c2value[1][2]

        if self.predecessorid == 'None': #nur road 4 wichtig
            self.line2_xstart= self.x
            self.line2_ystart = self.y
            self.winkel = 0
        if self.successorid == 'None':  #nur road 1 wichtig
            self.line1_xend = self.x
            self.line1_yend = self.y


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
        self.nodes = []
        
        for node in entity.nodes:
            if str(node) not in OSMNode.allOSMNodes:
                continue
            self.nodes.append(OSMNode.allOSMNodes[str(node)].id)
        if len(self.nodes) > 1:
            for node in entity.nodes:
                   OSMNode.allOSMNodes[str(node)].PreWayIdList.append(str(self.id))
            
    def _evaluate(self):
        startIdx = 0
        endIdx = -1
        if len(self.nodes) < 2:
            return
        for nodeId in self.nodes:
            node = OSMNode.allOSMNodes[nodeId]
            idx = self.nodes.index(nodeId)
            if len(node.PreWayIdList) > 1:    # dies wird eine Junction - Weg muss gesplittet werden
                if idx == startIdx or idx == endIdx-1:
                    continue
                else:
                    endIdx = idx+1
                    OSMWay(self.id, self.tags, self.nodes[startIdx:endIdx], self.nodes[startIdx], self.nodes[endIdx-1])
                    startIdx = idx
        if endIdx < len(self.nodes):
            endIdx = len(self.nodes)
            OSMWay(self.id, self.tags, self.nodes[startIdx:endIdx], self.nodes[startIdx], self.nodes[endIdx-1])

        
        
class OSMWay:
    allWays = {}
    
    @staticmethod
    def reset():
        OSMWay.allWays = {}
        
    def __init__(self,OSMid, tags, OSMnodes, StartNode, EndNode, register = True, debug=False):
        
        self.id = str(uuid.uuid1())
        if debug:
            if register:
                OSMWay.allWays[self.id] = self
            return
        self.OSMId = OSMid
        if register:
            OSMWay.allWays[self.id] = self
        self.tags = tags
        self.OSMNodes = OSMnodes
        previousnode = None
        previouspreviousnode = None

        for node in self.OSMNodes:
            if previousnode is not None and previouspreviousnode is not None:
                OSMNodeLink(str(previouspreviousnode), True, self.id, str(previousnode), str(node), False, self.id, register = True, debug = False)
            previouspreviousnode = copy.copy(previousnode)
            previousnode = copy.copy(node)
        
        if len(self.OSMNodes) > 1:
            for node in self.OSMNodes:
                   if self.id not in OSMNode.allOSMNodes[str(node)].wayIDList:
                       OSMNode.allOSMNodes[str(node)].wayIDList.append(str(self.id))
            OSMNode.allOSMNodes[str(self.OSMNodes[0])].outgoingWays.append(self.id)
            OSMNode.allOSMNodes[str(self.OSMNodes[0])].outgoingNodes.append(OSMNode.allOSMNodes[str(self.OSMNodes[1])].id)
            OSMNode.allOSMNodes[str(self.OSMNodes[-1])].incomingWays.append(self.id)
            OSMNode.allOSMNodes[str(self.OSMNodes[-1])].incomingNodes.append(OSMNode.allOSMNodes[str(self.OSMNodes[-2])].id)
        self.laneNumberDirection = -1
        self.laneNumberOpposite = -1     
        
        self.K1Node = EndNode   # end
        self.K2Node = StartNode   # start
        
        self.K1Links = []
        self.K2Links = []
        
        self.K1_turnLanesDirection = []
        self.K1_ConnectionsTurnLanesDirection = []
        self.K1_incomingLanesFromK1 = []
        self.K2_turnLanesOpposite = []
        self.K2_ConnectionsTurnLanesOpposite = []
        self.K2_incomingLanesFromK2 = []
        
        self.checkLanes()
        for node in self.OSMNodes:
            OSMNode.allOSMNodes[node].incomingLanes.append(self.laneNumberDirection)
            OSMNode.allOSMNodes[node].outgoingLanes.append(self.laneNumberOpposite)
            OSMNode.allOSMNodes[node].lanespecificWay.append(self.id)
        self.prepareConnections()
        
        self.K1_Angles = []
        self.K2_Angles = []
        
        self.K1_OSMLinks = []
        self.K2_OSMLinks = []
        
        self.K1_OutgoingLanes = []
        self.K2_OutgoingLanes = []
        
        self.K1_Ways = []
        self.K1_WaysDirection = []
        self.K2_Ways = []
        self.K2_WaysDirection = []

    
    def getNodePredecessor(self, nodeid):
        try:
            idx = self.OSMNodes.index(str(nodeid))
        except:
            print("not in list")
            print(nodeid)
            print(self.OSMNodes)
            print(self.id)
            print()
            return "Not in List"
        if idx > 0:
            return self.OSMNodes[idx-1]
        else:
            return 'No Predecessor'
        
    def getNodeSuccessor(self, nodeid):
        try:
            idx = self.OSMNodes.index(str(nodeid))
        except:
            return "Not in List"
        if idx < len(self.OSMNodes)-1:
            return self.OSMNodes[idx+1]
        else:
            return 'No Successor'
    
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
        laneNumberDirection = 1
        laneNumberOpposite = 0 if oneWay else 1
        if len(self.K1_turnLanesDirection) > 0 and lanes == -1:
            laneNumberDirection = len(self.K1_turnLanesDirection)
        if len(self.K2_turnLanesOpposite) > 0 and lanes == -1:
            laneNumberOpposite = len(self.K2_turnLanesOpposite)
        lanes = 1 if oneWay else 2
        
        self.laneNumberDirection = laneNumberDirection
        self.laneNumberOpposite = laneNumberOpposite
        
