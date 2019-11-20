#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 09:03:46 2019

@author: jhm
"""

from .OSMparsing import OSMNode, OSMJunction, OSMNodeLink, OSMWay
import numpy as np
from .OpenDriveWriting import openDriveRoad, openDriveLane, openDriveRoadMark, openDriveJunction, openDriveLaneLink, openDriveRoadLink
import copy

def convertOSM():
    creators = []
    for nodeLink in OSMNodeLink.links.values():
        creators.append(LaneAndRoadCreator(nodeLink.id))
    for creator in creators:
        creator.findRelevantCreators()
    for creator in creators:
        creator.createOpenDriveRoads()
    for creator in creators:
        creator.createOpenDriveRoadConnections()
    for creator in creators:
        try:
            creator.createMergeConnections()
        except: pass
        creator.createConnections()
    for creator in creators:
        creator.createOpenDriveJunctionConnections()
    
    
class WayLaneLink:
    def __init__(self,PredecessorWay, PredecessorIncoming,  SuccessorWay, SuccessorIncoming, OSMNodeLink, PredecessorLane, SuccessorLane ):
        self.PredecessorWay = PredecessorWay
        self.IsPredecessorIncoming = PredecessorIncoming
        self.SuccessorWay = SuccessorWay
        self.IsSuccessorIncoming = SuccessorIncoming
        self.OSMNodeLink = OSMNodeLink
        self.PredecessorLane = PredecessorLane
        self.SuccessorLane = SuccessorLane

    def giveConnection(self, PredecessorWay, SuccessorWay):
        if PredecessorWay.id == self.PredecessorWay.id or PredecessorWay.id == self.SuccessorWay.id:
            if SuccessorWay.id == self.SuccessorWay.id or SuccessorWay.id == self.PredecessorWay.id:
                predecessorlane = self.PredecessorLane
                successorlane = self.SuccessorLane
                if self.PredecessorWay.id == SuccessorWay.id:
                    predecessorlane, successorlane = successorlane, predecessorlane
                return predecessorlane, successorlane
        return None, None

class LaneAndRoadCreator(OSMNodeLink):
     allLaneAndRoadCreators = {}
     def __init__(self, OSMNodeLinkID):
        super(LaneAndRoadCreator,self).__init__(
             OSMNodeLink.links[OSMNodeLinkID].predecessorid,
             OSMNodeLink.links[OSMNodeLinkID].predecessorIsIncoming, 
             OSMNodeLink.links[OSMNodeLinkID].predecessorway, 
             OSMNodeLink.links[OSMNodeLinkID].nodeid, 
             OSMNodeLink.links[OSMNodeLinkID].successorid, 
             OSMNodeLink.links[OSMNodeLinkID].successorIsIncoming, 
             OSMNodeLink.links[OSMNodeLinkID].successorway, register = False, debug = False)
        self.id = OSMNodeLinkID
        LaneAndRoadCreator.allLaneAndRoadCreators[self.id] = self
        self.node = OSMNode.allOSMNodes[OSMNodeLink.links[OSMNodeLinkID].nodeid]
        self.OSMNodeLinkID = OSMNodeLinkID
        self.x = OSMNode.allOSMNodes[self.nodeid].x
        self.y = OSMNode.allOSMNodes[self.nodeid].y
        self.tags = OSMNode.allOSMNodes[self.nodeid].tags
        self.wayIDList = self.node.wayIDList
        try: 
            self.predecessorWAY = OSMWay.allWays[self.predecessorway]
            self.predecessorNODE= OSMNode.allOSMNodes[self.predecessorid]
        except: self.predecessorWAY = "None"
        try: 
            self.successorWAY = OSMWay.allWays[self.successorway]
            self.successorNODE = OSMNode.allOSMNodes[self.successorid]
        except: self.successorWAY = "None"
        
        self.OSMJunction = None
        self.Connections = {}
        if self.node.isJunction:
            self.OSMJunction = OSMJunction.allJunctions[self.node.id]
        self.OSMLinks = OSMNodeLink.nodes[str(self.nodeid)]
        self.createAngleTurnTagsAndTurnsForWays()
        self.r1 = None
        self.r2 = None
        self.r3 = None
        self.r4 = None
        self.predecessorCreators = []
        self.predecessorsAreIncoming = []
        self.successorCreators =  []
        self.successorsAreOutgoing = []
        self.pr4r1 = []
        self.pr1r1 = []
        self.r4sr1 = []
        self.r4sr4 = []

        self.pr4r1Lanes = []
        self.pr1r1Lanes = []
        self.r4sr1Lanes = []
        self.r4sr4Lanes = []
        
     def findRelevantCreators(self):
        predecessorCreators = []
        successorCreators =  []
        try:  predecessorCreators = OSMNodeLink.nodes[self.predecessorNODE.id]
        except: pass
        try:  successorCreators = OSMNodeLink.nodes[self.successorNODE.id]
        except: pass
        for creatorID in predecessorCreators:
            creator = LaneAndRoadCreator.allLaneAndRoadCreators[creatorID]
            try:
                if creator.successorNODE.id == self.node.id:
                    self.predecessorCreators.append(creator)
                    self.predecessorsAreIncoming.append(True)
                    if len(successorCreators) == 0:    #letzter link
                        creator.line2_xend = self.x
                        creator.line2_yend = self.y
            except: pass
            try:
                if creator.predecessorNODE.id == self.node.id:
                    self.predecessorCreators.append(creator)
                    self.predecessorsAreIncoming.append(False)
                    if len(successorCreators) == 0:    #letzter link
                        creator.line1_xstart = self.x
                        creator.line1_ystart = self.y
            except: pass
        for creatorID in successorCreators:
            creator = LaneAndRoadCreator.allLaneAndRoadCreators[creatorID]
            if creator.predecessorNODE.id == self.node.id:
                self.successorCreators.append(creator)
                self.successorsAreOutgoing.append(True)
                if len(self.predecessorCreators) == 0:    #letzter link
                    creator.line1_xstart = self.x
                    creator.line1_ystart = self.y
            elif creator.successorNODE.id == self.node.id:
                self.successorCreators.append(creator)
                self.successorsAreOutgoing.append(False)
                if len(self.predecessorCreators) == 0:    #letzter link
                    creator.line2_xend = self.x
                    creator.line2_yend = self.y

     def createOpenDriveJunctionConnections(self):
         pass

     def createOpenDriveRoads(self):
        if len(self.successorCreators) > 0 and len(self.predecessorCreators) > 0:
            l1length = ((self.line1_xstart-self.line1_xend)**2+(self.line1_ystart-self.line1_yend)**2)**0.5
            l2length = ((self.line2_xstart-self.line2_xend)**2+(self.line2_ystart-self.line2_yend)**2)**0.5
            #length, x, y, hdg, osmnodelinkid, waytags, wayIsOpposite, geoparam
            
            r1 = openDriveRoad(l1length, self.line1_xstart, self.line1_ystart, self.line1_Hdg, self.OSMNodeLinkID, self.predecessorWAY.tags, self.predecessorIsIncoming, geoparam = None)
            r2 = openDriveRoad(self.clength, self.c_xstart, self.c_ystart, self.c1_hdg, self.OSMNodeLinkID, self.predecessorWAY.tags, not self.predecessorIsIncoming, geoparam = self.c1_param)
            r3 = openDriveRoad(self.clength, self.c_xstart, self.c_ystart, self.c2_hdg, self.OSMNodeLinkID, self.successorWAY,not self.successorIsIncoming, geoparam = self.c2_param)
            r4 = openDriveRoad(l2length, self.line2_xstart, self.line2_ystart, self.line2_Hdg, self.OSMNodeLinkID, self.successorWAY, not self.successorIsIncoming, geoparam = None)
            
            #create lanes for non Junctions
            if self.OSMJunction is None:  
                    #create roads lanes
                    for laneId in range(1,self.predecessorWAY.laneNumberDirection+1):
                            r1.lanesRight.append(openDriveLane(-laneId if self.predecessorIsIncoming else laneId, r1.id, self.predecessorWAY))
                    if len(r1.lanesRight) > 0: r1.lanesRight[-1].roadmark = "solid"
                    for laneId in range(1,self.predecessorWAY.laneNumberOpposite+1):
                            r1.lanesLeft.append(openDriveLane(laneId if self.predecessorIsIncoming else laneId, r1, self.predecessorWAY))
                    if len(r1.lanesLeft) > 0: r1.lanesLeft[-1].roadmark = "solid"
                    r1.laneMiddle.append(openDriveLane(0, r1.id, self.predecessorWAY))
                    r1.laneMiddle[0].roadmark = "solid"
                    if len(r1.lanesLeft) == 1 and len(r1.lanesRight) == 1:
                        r1.laneMiddle[0].roadmark = "broken"
                    ## entgegengesetzte Kurve
                    #create roads lanes
                    for laneId in range(1,self.predecessorWAY.laneNumberDirection+1):
                            r2.lanesLeft.append(openDriveLane(laneId if self.predecessorIsIncoming else -laneId, r2.id, self.predecessorWAY))
                    if len(r2.lanesLeft) > 0: r2.lanesLeft[-1].roadmark = "solid"
                    for laneId in range(1,self.predecessorWAY.laneNumberOpposite+1):
                            r2.lanesRight.append(openDriveLane(-laneId if self.predecessorIsIncoming else laneId, r2.id, self.predecessorWAY))
                    if len(r2.lanesRight) > 0: r2.lanesRight[-1].roadmark = "solid"
                    r2.laneMiddle.append(openDriveLane(0, r2.id, self.predecessorWAY))
                    r2.laneMiddle[0].roadmark = "solid"
                    if len(r2.lanesLeft) == 1 and len(r2.lanesRight) == 1:
                        r2.laneMiddle[0].roadmark = "broken"
                    ## Kurve zum nachfolger
                    #create roads lanes
                    for laneId in range(1,self.successorWAY.laneNumberDirection+1):
                            r3.lanesRight.append(openDriveLane(-laneId if not self.successorIsIncoming else laneId, r3.id, self.successorWAY))
                    if len(r3.lanesRight) > 0: r3.lanesRight[-1].roadmark = "solid"
                    for laneId in range(1,self.successorWAY.laneNumberOpposite+1):
                            r3.lanesLeft.append(openDriveLane(laneId if not self.successorIsIncoming else -laneId, r3.id, self.successorWAY))
                    r3.laneMiddle.append(openDriveLane(0, r3.id, self.successorWAY))
                    if len(r3.lanesLeft) > 0: r3.lanesLeft[-1].roadmark = "solid"
                    r3.laneMiddle[0].roadmark = "solid"
                    if len(r3.lanesLeft) == 1 and len(r3.lanesRight) == 1:
                        r3.laneMiddle[0].roadmark = "broken"
                    ## Gerade zum nachfolger
                    #create roads lanes
                    for laneId in range(1,self.successorWAY.laneNumberDirection+1):
                            r4.lanesRight.append(openDriveLane(-laneId if not self.successorIsIncoming else laneId, r4.id, self.successorWAY))
                    if len(r4.lanesRight) > 0: r4.lanesRight[-1].roadmark = "solid"
                    for laneId in range(1,self.successorWAY.laneNumberOpposite+1):
                            r4.lanesLeft.append(openDriveLane(laneId if not self.successorIsIncoming else -laneId, r4.id, self.successorWAY))
                    r4.laneMiddle.append(openDriveLane(0, r4.id, self.successorWAY))
                    if len(r4.lanesLeft) > 0: r4.lanesLeft[-1].roadmark = "solid"
                    r4.laneMiddle[0].roadmark = "solid"
                    if len(r4.lanesLeft) == 1 and len(r4.lanesRight) == 1:
                        r4.laneMiddle[0].roadmark = "broken"

                        
            else:   #lane und Junction creation for Junction
                r1.odriveJunction  = openDriveJunction.giveJunction(self.predecessorWAY, self.node).id
                openDriveJunction.attachRoad(r1.odriveJunction,r1)
                r4.odriveJunction  = openDriveJunction.giveJunction(self.successorWAY, self.node).id
                openDriveJunction.attachRoad(r4.odriveJunction,r4)

                #create roads lanes
                for laneId in range(1,self.predecessorWAY.laneNumberDirection+1 if self.predecessorIsIncoming else self.predecessorWAY.laneNumberOpposite+1):
                        r1.lanesRight.append(openDriveLane(-laneId if self.predecessorIsIncoming else laneId, r1.id, self.predecessorWAY))
                        if len(r1.lanesRight) > 0: r1.lanesRight[-1].roadmark = "none"
                for laneId in range(1,self.predecessorWAY.laneNumberOpposite+1 if self.predecessorIsIncoming else self.predecessorWAY.laneNumberDirection+1):
                        r1.lanesLeft.append(openDriveLane(-laneId if not self.predecessorIsIncoming else laneId, r1.id, self.predecessorWAY))
                        if len(r1.lanesLeft) > 0: r1.lanesLeft[-1].roadmark = "none"
                r1.laneMiddle.append(openDriveLane(0, r1.id, self.predecessorWAY))
                r1.laneMiddle[0].roadmark = "none"
                ## entgegengesetzte Kurve
                #create roads lanes
                for laneId in range(1,self.successorWAY.laneNumberDirection+1 if not self.successorIsIncoming else self.successorWAY.laneNumberOpposite+1):
                    r2.lanesLeft.append(openDriveLane(laneId if not self.successorIsIncoming else -laneId, r2.id, self.successorWAY))
                    if len(r2.lanesLeft) > 0: r2.lanesLeft[-1].roadmark = "none"
                for laneId in range(1,self.successorWAY.laneNumberDirection+1 if self.successorIsIncoming else self.successorWAY.laneNumberOpposite+1):
                    r2.lanesRight.append(openDriveLane(laneId if self.successorIsIncoming else -laneId, r2.id, self.successorWAY))
                    if len(r2.lanesRight) > 0: r2.lanesRight[-1].roadmark = "none"
                r2.laneMiddle.append(openDriveLane(0, r2.id, self.successorWAY))
                r2.laneMiddle[0].roadmark = "none"
                ## Kurve zum nachfolger
                #create roads lanes
                for laneId in range(1,self.successorWAY.laneNumberDirection+1 if not self.successorIsIncoming else self.successorWAY.laneNumberOpposite+1):
                    r3.lanesRight.append(openDriveLane(-laneId if not self.successorIsIncoming else laneId, r3.id, self.successorWAY))
                    if len(r3.lanesRight) > 0: r3.lanesRight[-1].roadmark = "none"
                for laneId in range(1,self.successorWAY.laneNumberDirection+1 if self.successorIsIncoming else self.successorWAY.laneNumberOpposite+1):
                    r3.lanesLeft.append(openDriveLane(-laneId if self.successorIsIncoming else laneId, r3.id, self.successorWAY))
                    if len(r3.lanesLeft) > 0: r3.lanesLeft[-1].roadmark = "none"
                r3.laneMiddle.append(openDriveLane(0, r3.id, self.successorWAY))
                r3.laneMiddle[0].roadmark = "none"
                ## Gerade zum nachfolger
                #create roads lanes
                for laneId in range(1,self.successorWAY.laneNumberDirection+1 if not self.successorIsIncoming else self.successorWAY.laneNumberOpposite+1):
                    r4.lanesRight.append(openDriveLane(-laneId if not self.successorIsIncoming else laneId, r4.id, self.successorWAY))
                    if len(r4.lanesRight) > 0: r4.lanesRight[-1].roadmark = "none"
                for laneId in range(1,self.successorWAY.laneNumberDirection+1 if self.successorIsIncoming else self.successorWAY.laneNumberOpposite+1):
                    r4.lanesLeft.append(openDriveLane(-laneId if self.successorIsIncoming else laneId, r4.id, self.successorWAY))
                    if len(r4.lanesLeft) > 0: r4.lanesLeft[-1].roadmark = "none"
                r4.laneMiddle.append(openDriveLane(0, r4.id, self.successorWAY))
                r4.laneMiddle[0].roadmark = "none"
             ###################################################################################################################################################################################               
            #create internal Roadlinks   -> Roadlinks für interCreatorVerbindungen brauchen bereits bestehende Straßen
            r1r2 = openDriveRoadLink(r1, r2, 'end', 'end')
            r1.RoadLinksSuccessor.append(r1r2)
            r2.RoadLinksSuccessor.append(r1r2)
            r2r3 = openDriveRoadLink(r2, r3, 'start', 'start')
            r2.RoadLinksPredecessor.append(r2r3)
            r3.RoadLinksPredecessor.append(r2r3)
            r3r4 = openDriveRoadLink(r3, r4, 'end', 'start')
            r3.RoadLinksSuccessor.append(r3r4)
            r4.RoadLinksPredecessor.append(r3r4)
            self.r1 = r1
            self.r2 = r2
            self.r3 = r3
            self.r4 = r4
            
            self.pr4r1 = []
            self.pr1r1 = []
            self.r4sr1 = []
            self.r4sr4 = []

            self.pr4r1Lanes = []
            self.pr1r1Lanes = []
            self.r4sr1Lanes = []
            self.r4sr4Lanes = []
            
     def createOpenDriveRoadConnections(self):
         if len(self.successorCreators) > 0 and len(self.predecessorCreators) > 0:
            for  idx in range(len(self.predecessorCreators)):
                if self.predecessorsAreIncoming[idx]:
                    if self.predecessorCreators[idx].r4 is not None:
                        link = openDriveRoadLink(self.predecessorCreators[idx].r4, self.r1, 'end', 'start')
                        self.pr4r1.append(link)
                else:
                    if self.predecessorCreators[idx].r1 is not None:
                        link = openDriveRoadLink(self.predecessorCreators[idx].r1, self.r1, 'start', 'start')
                        self.pr1r1.append(link)
            for  idx in range(len(self.successorCreators)):
                if self.successorsAreOutgoing[idx]:
                    if self.successorCreators[idx].r1 is not None:
                        link = openDriveRoadLink(self.r4, self.successorCreators[idx].r1, 'end', 'start')
                        self.r4sr1.append(link)
                else:
                    if self.successorCreators[idx].r4 is not None:
                        link = openDriveRoadLink(self.r4, self.successorCreators[idx].r4, 'end', 'end')
                        self.r4sr4.append(link)
                    
              

     def createAngleTurnTagsAndTurnsForWays(self):
         if self.node.isJunction:
            for OSMWayId in self.wayIDList:
                    way = OSMWay.allWays[OSMWayId]
                #way = OSMWay.allWays[OSMWayId]
                # von diesem Weg aus geht man zur Kreuzung und sieht welche Turnmöglichkeiten es gibt -> Weg kann im link predecessor oder successor sein
                # Weg kann ausserdem als Predecessor oder Successor verkehrt herum laufen
                    link = OSMNodeLink.links[self.OSMNodeLinkID] # es kommt für Winkel nur auf predecessor/successor an
                    if link.predecessorway == OSMWayId:
                        outgoinglanes = OSMWay.allWays[link.successorway].laneNumberDirection if not link.successorIsIncoming else OSMWay.allWays[link.successorway].laneNumberOpposite
                        if outgoinglanes == 0:
                            continue
                        incominglanes = OSMWay.allWays[link.predecessorway].laneNumberDirection if link.predecessorIsIncoming else OSMWay.allWays[link.predecessorway].laneNumberOpposite
                        if incominglanes == 0:
                            continue
                        if link.predecessorIsIncoming:
                            way.K1_OutgoingLanes.append(outgoinglanes)
                            way.K1_Angles.append(link.winkel)
                            way.K1_Ways.append(link.successorway)
                            way.K1_WaysDirection.append(not link.successorIsIncoming)
                            way.K1_OSMLinks.append(link)
                            
                        else:
                            way.K2_OutgoingLanes.append(outgoinglanes)
                            way.K2_Angles.append(link.winkel)# es kommt nur auf predecessor/successor an
                            way.K2_Ways.append(link.successorway)
                            way.K2_WaysDirection.append(not link.successorIsIncoming)
                            way.K2_OSMLinks.append(link)
                                
                    if link.successorway == OSMWayId:
                        outgoinglanes = OSMWay.allWays[link.predecessorway].laneNumberDirection if not link.predecessorIsIncoming else OSMWay.allWays[link.predecessorway].laneNumberOpposite
                        if outgoinglanes == 0:
                            continue
                        incominglanes = OSMWay.allWays[link.successorway].laneNumberDirection if link.successorIsIncoming else OSMWay.allWays[link.successorway].laneNumberOpposite
                        if incominglanes == 0:
                            continue
                        if link.successorIsIncoming:
                            way.K1_OutgoingLanes.append(outgoinglanes)
                            way.K1_Angles.append(-link.winkel)
                            way.K1_Ways.append(link.predecessorway)
                            way.K1_WaysDirection.append(not link.predecessorIsIncoming)
                            way.K1_OSMLinks.append(link)
                            
                        else:
                            way.K2_OutgoingLanes.append(outgoinglanes)
                            way.K2_Angles.append(-link.winkel) # es kommt nur auf predecessor/successor an
                            way.K2_Ways.append(link.predecessorway)
                            way.K2_WaysDirection.append(not link.predecessorIsIncoming)
                            way.K2_OSMLinks.append(link)
         

     def createMergeConnections(self):
         if len(self.wayIDList) == 2:
            outgoingLaneIdx = 0
            
            outgoinglanes = [[]*self.successorWAY.laneNumberDirection] if not self.successorIsIncoming else [[]*self.successorWAY.laneNumberOpposite]
            outgoingIdx = 0
            if self.predecessorIsIncoming:
                preIncLaneIdx_ = 0
                for preIncLaneIdx in range(len(self.predecessorWAY.K1_turnLanesDirection)):
                    preIncLaneIdx_ = preIncLaneIdx
                    if 'through' in self.predecessorWAY.K1_turnLanesDirection[preIncLaneIdx] or len(self.predecessorWAY.K1_turnLanesDirection[preIncLaneIdx]) == 0:
                        link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx, outgoingIdx)
                        self.predecessorWAY.K1_ConnectionsTurnLanesDirection[preIncLaneIdx].append(link)
                        self.successorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        
                        outgoingLaneIdx += 1
                        if outgoingLaneIdx > len(outgoinglanes):
                            outgoingLaneIdx -= 1
                    if "merge_r" in self.predecessorWAY.K1_turnLanesDirection[preIncLaneIdx]:
                        link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx, outgoingIdx)
                        self.predecessorWAY.K1_ConnectionsTurnLanesDirection[preIncLaneIdx].append(link)
                        self.successorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        
                    if "merge_l" in self.predecessorWAY.K1_turnLanesDirection[preIncLaneIdx]:
                        outgoingLaneIdx -= 1
                        link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx, outgoingIdx)
                        self.predecessorWAY.K1_ConnectionsTurnLanesDirection[preIncLaneIdx].append(link)
                        self.successorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        
                    self.pr4r1Lanes.append(openDriveLaneLink(self.predecessorCreators[0].r4, self.r1, preIncLaneIdx,outgoingIdx))
                if outgoingIdx < len(outgoinglanes):
                    for additionalLaneIdx in range(outgoingIdx+1, len(outgoinglanes)):
                         link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx_, additionalLaneIdx)
                         self.predecessorWAY.K1_ConnectionsTurnLanesDirection[preIncLaneIdx_].append(link)
                         self.successorWAY.K2_incomingLanesFromK2[additionalLaneIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[additionalLaneIdx].append(link)
                         self.pr4r1Lanes.append(openDriveLaneLink(self.predecessorCreators[0].r4, self.r1, preIncLaneIdx,outgoingIdx))
            else:
                preIncLaneIdx_ = 0
                for preIncLaneIdx in range(len(self.predecessorWAY.K2_turnLanesOpposite)):
                    preIncLaneIdx_ = preIncLaneIdx
                    if 'through' in self.predecessorWAY.K2_turnLanesOpposite[preIncLaneIdx] or len(self.predecessorWAY.K2_turnLanesOpposite[preIncLaneIdx]) == 0:
                        link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx, outgoingIdx)
                        self.predecessorWAY.K2_ConnectionsTurnLanesOpposite[preIncLaneIdx].append(link)
                        self.successorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        outgoingLaneIdx += 1
                        if outgoingLaneIdx > len(outgoinglanes):
                            outgoingLaneIdx -= 1
                    
                    if "merge_r" in self.predecessorWAY.K2_turnLanesOpposite[preIncLaneIdx]:
                        link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx, outgoingIdx)
                        self.predecessorWAY.K2_ConnectionsTurnLanesOpposite[preIncLaneIdx].append(link)
                        self.successorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                    
                    if "merge_l" in self.predecessorWAY.K2_turnLanesOpposite[preIncLaneIdx]:
                        outgoingLaneIdx -= 1
                        link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx, outgoingIdx)
                        self.predecessorWAY.K2_ConnectionsTurnLanesOpposite[preIncLaneIdx].append(link)
                        self.successorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                    self.pr1r1Lanes.append(openDriveLaneLink(self.predecessorCreators[0].r1, self.r1, preIncLaneIdx,outgoingIdx))

                if outgoingIdx < len(outgoinglanes):
                    for additionalLaneIdx in range(outgoingIdx+1, len(outgoinglanes)):
                         link = WayLaneLink(self.predecessorWAY, self.predecessorIsIncoming,  self.successorWAY, self.successorIsIncoming, self.OSMNodeLinkID, preIncLaneIdx_, additionalLaneIdx)
                         self.predecessorWAY.K2_ConnectionsTurnLanesOpposite[preIncLaneIdx_].append(link)
                         self.successorWAY.K2_incomingLanesFromK2[additionalLaneIdx].append(link) if not self.successorIsIncoming else self.successorWAY.K1_incomingLanesFromK1[additionalLaneIdx].append(link)
                         self.pr1r1Lanes.append(openDriveLaneLink(self.predecessorCreators[0].r1, self.r1, preIncLaneIdx,outgoingIdx))
                         

            outgoingLaneIdx = 0
            
            outgoinglanes = [[]*self.predecessorWAY.laneNumberDirection] if not self.predecessorIsIncoming else [[]*self.predecessorWAY.laneNumberOpposite]
            outgoingIdx = 0
            if self.successorIsIncoming:
                sucIncLaneIdx_ = 0
                for sucIncLaneIdx in range(len(self.successorWAY.K1_turnLanesDirection)):
                    sucIncLaneIdx_ = sucIncLaneIdx
                    if 'through' in self.successorWAY.K1_turnLanesDirection[sucIncLaneIdx] or len(self.successorWAY.K1_turnLanesDirection[sucIncLaneIdx]) == 0:
                        link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, outgoingIdx)
                        self.successorWAY.K1_ConnectionsTurnLanesDirection[sucIncLaneIdx].append(link)
                        self.predecessorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        outgoingLaneIdx += 1
                        if outgoingLaneIdx > len(outgoinglanes):
                            outgoingLaneIdx -= 1
                    
                    if "merge_r" in self.successorWAY.K1_turnLanesDirection[sucIncLaneIdx]:
                        link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, outgoingIdx)
                        self.successorWAY.K1_ConnectionsTurnLanesDirection[sucIncLaneIdx].append(link)
                        self.predecessorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        
                    if "merge_l" in self.predecessorWAY.K1_turnLanesDirection[preIncLaneIdx]:
                        outgoingLaneIdx -= 1
                        link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, outgoingIdx)
                        self.successorWAY.K1_ConnectionsTurnLanesDirection[sucIncLaneIdx].append(link)
                        self.predecessorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                    self.r4sr4Lanes.append(openDriveLaneLink(self.r4,self.successorCreators[0].r4, preIncLaneIdx,outgoingIdx))
                if outgoingIdx < len(outgoinglanes):
                    for additionalLaneIdx in range(outgoingIdx+1, len(outgoinglanes)):
                         link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx_, additionalLaneIdx)
                         self.successorWAY.K1_ConnectionsTurnLanesDirection[sucIncLaneIdx_].append(link)
                         self.predecessorWAY.K2_incomingLanesFromK2[additionalLaneIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesFromK1[additionalLaneIdx].append(link)
                         self.r4sr4Lanes.append(openDriveLaneLink(self.r4,self.successorCreators[0].r4, preIncLaneIdx,outgoingIdx))
            else:
                sucIncLaneIdx_ = 0
                for sucIncLaneIdx in range(len(self.successorWAY.K2_turnLanesOpposite)):
                    sucIncLaneIdx_ = sucIncLaneIdx
                    if 'through' in self.successorWAY.K2_turnLanesOpposite[sucIncLaneIdx] or len(self.successorWAY.K2_turnLanesOpposite[sucIncLaneIdx]) == 0:
                        link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, outgoingIdx)
                        self.successorWAY.K2_ConnectionsTurnLanesOpposite[sucIncLaneIdx].append(link)
                        self.predecessorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        outgoingLaneIdx += 1
                        if outgoingLaneIdx > len(outgoinglanes):
                            outgoingLaneIdx -= 1
                    
                    if "merge_r" in self.successorWAY.K2_turnLanesOpposite[sucIncLaneIdx]:
                        link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, outgoingIdx)
                        self.successorWAY.K2_ConnectionsTurnLanesOpoosite[sucIncLaneIdx].append(link)
                        self.predecessorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesFromK1[outgoingIdx].append(link)
                        
                    if "merge_l" in self.successorWAY.K2_turnLanesOpposite[sucIncLaneIdx]:
                        outgoingLaneIdx -= 1
                        link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, outgoingIdx)
                        self.successorWAY.K2_ConnectionsTurnLanesOpoosite[sucIncLaneIdx].append(link)
                        self.predecessorWAY.K2_incomingLanesFromK2[outgoingIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesfromK1[outgoingIdx].append(link)
                    self.r4sr1Lanes.append(openDriveLaneLink(self.r4,self.successorCreators[0].r1,preIncLaneIdx,outgoingIdx))
                if outgoingIdx < len(outgoinglanes):
                    for additionalLaneIdx in range(outgoingIdx+1, len(outgoinglanes)):
                         link = WayLaneLink(self.successorWAY, self.successorIsIncoming,  self.predecessorWAY, self.predecessorIsIncoming, self.OSMNodeLinkID, sucIncLaneIdx, additionalLaneIdx)
                         self.successorWAY.K2_ConnectionsTurnLanesOpoosite[sucIncLaneIdx].append(link)
                         self.predecessorWAY.K2_incomingLanesFromK2[additionalLaneIdx].append(link) if not self.predecessorIsIncoming else self.predecessorWAY.K1_incomingLanesfromK1[additionalLaneIdx].append(link)
                         self.r4sr1Lanes.append(openDriveLaneLink(self.r4,self.successorCreators[0].r1,preIncLaneIdx,outgoingIdx))

     def createConnections(self):
         self._createConnections(self.predecessorWAY, self.predecessorIsIncoming, self.successorWAY, self.successorIsIncoming, self.winkel, True)
         self._createConnections(self.successorWAY, self.successorIsIncoming, self.predecessorWAY, self.predecessorIsIncoming, -self.winkel, False)
         for roadConnection in self.r4sr1:
             roadConnection.openDriveLaneLinks = self.r4sr1Lanes
         for roadConnection in self.r4sr4:
             roadConnection.openDriveLaneLinks = self.r4sr4Lanes
         for roadConnection in self.pr4r1:
             roadConnection.openDriveLaneLinks = self.pr4r1Lanes
         for roadConnection in self.pr1r1:
             roadConnection.openDriveLaneLinks = self.pr1r1Lanes


     def _createConnections(self, predecessorWay, predecessorIsIncoming, successorWay, successorIsIncoming, Angle, wahrerPredecessor):
         if len(self.wayIDList) > 2:
            incomingLanes = predecessorWay.laneNumberDirection if predecessorIsIncoming else predecessorWay.laneNumberOpposite
            outgoingLanes = predecessorWay.K1_OutgoingLanes if predecessorIsIncoming else predecessorWay.K2_OutgoingLanes
            if incomingLanes > 0 and sum(outgoingLanes) > 0:
                possibilities = []
                incomingTurnTags = predecessorWay.K1_turnLanesDirection if predecessorIsIncoming else predecessorWay.K2_turnLanesOpposite
                angles = predecessorWay.K1_Angles if predecessorIsIncoming else predecessorWay.K2_Angles

                if any(["left" in b for b in incomingTurnTags]):
                    possibilities.append("left")
                if any(["slight_l" in b for b in incomingTurnTags]):
                    possibilities.append("slight_l")
                if any(["through" in b for b in incomingTurnTags]) or any([len(b)== 0 for b in incomingTurnTags ]):
                    possibilities.append("through")
                if any(["slight_r" in b for b in incomingTurnTags]):
                    possibilities.append("slight_r")
                if any(["right" in b for b in incomingTurnTags]):
                    possibilities.append("right")
                
                sortangles = copy.copy(angles)
                sortangles.sort()
                
                lanesPerPossibility = {}
                for possibility in possibilities:
                    for laneIdx in range(len(incomingTurnTags)):
                        if possibility in incomingTurnTags[laneIdx]:
                            try:
                                lanesPerPossibility[possibility] += 1
                            except:
                                lanesPerPossibility[possibility] = 1
                
                #  # jede Möglichkeit kann mehrere Winkel haben -> erst links und rechts wegnehmen und Spuren zählen
                # Spuren müssen nicht unbedingt abbiegen    
                # Heuristik: Jede Eingehende Spur muss mindestens irgendwohin - die Rechteste nach rechts, die linkeste nach links.
                # Jede eingehende Spur kann mehrfach irgendwohin
                # Jeder Winkel muss mindestens 1 Spur haben
                # Jede Outgoinglane darf nicht mehr als Anzahl Outgoinglanes haben
                
                angleIdx = 0      # jeder Winkel muss mindestens zu einer Spur
                '''outgoingMatch = np.array([1]*len(angles))
                if outgoingMatch.sum() < incominglanes:   # es müssen noch Spuren verteilt werden -> An Outgoinglanes Orientieren
                    for idx in range(len(outgoingMatch)):
                        if outgoingLanes[idx] > outgoingMatch[idx]:
                            outgoingMatch[idx] += 1
                            if outgoingMatch.sum() == incominglanes:
                                break
                    try:
                        angleIdx = angles.index(Angle)
                    except:
                        print("Cant find Angle "+str(Angle)+" in List "+str(angles) )
                        angleIdx = angles.index(-Angle)
                    lanesum = 0
                    for i in range(sortangles.index(Angle)):     # get the lanenumber of the incoming lane
                        lanesum += outgoingMatch[angles.index(sortangles[i])]
                    for i in range(outgoingMatch[angleIdx]):
                            link = WayLaneLink(predecessorWay, predecessorIsIncoming,  successorWay, successorIsIncoming, self.OSMNodeLinkID, i+lanesum, outgoingLanes[angleIdx]-i-1)
                            predecessorWay.K1_ConnectionsTurnLanesDirection[i+lanesum].append(link) if predecessorIsIncoming else predecessorWay.K2_ConnectionsTurnLanesOpposite[i+lanesum].append(link)
                            successorWay.K2_incomingLanesFromK2[-i-1].append(link) if not successorIsIncoming else successorWay.K1_incomingLanesfromK1[-i-1].append(link)
                '''             
                if False:
                    pass


                else:   # weniger eingangs als Ausgangsspuren -> es kann doppelt abgebogen werden
                    try:
                        lanesum = 0
                        for i in range(sortangles.index(Angle)):     # get the lanenumber of the incoming lane
                            lanesum += outgoingLanes[angles.index(sortangles[i])]
                            if lanesum > incomingLanes:
                                    lanesum = incomingLanes-1      #lanes, die bisher verbraucht wurden
                        
                        # ist noch platz für die outgoinglanes?
                        if lanesum+outgoingLanes[angleIdx] > incomingLanes-1:
                            lanesum = max(0,lanesum-outgoingLanes[angleIdx]-1)
                        for i in range(outgoingLanes[angleIdx]):   #lanes, die hier outgoing sind
                                if lanesum+i > incomingLanes-1:
                                    lanesum -= 1
                                link = WayLaneLink(predecessorWay, predecessorIsIncoming,  successorWay, successorIsIncoming, self.OSMNodeLinkID, i+lanesum, outgoingLanes[angleIdx]-i-1)
                                if wahrerPredecessor:
                                    self.pr1r1Lanes.append(openDriveLaneLink(self.predecessorCreators[0].r1,self.r1,i+lanesum,outgoingLanes[angleIdx]-i-1))
                                    self.pr4r1Lanes.append(openDriveLaneLink(self.predecessorCreators[0].r4,self.r1,i+lanesum,outgoingLanes[angleIdx]-i-1))
                                else:
                                    self.r4sr4Lanes.append(openDriveLaneLink(self.r4,self.successorCreators[0].r4,i+lanesum,outgoingLanes[angleIdx]-i-1))
                                    self.r4sr1Lanes.append(openDriveLaneLink(self.r4,self.successorCreators[0].r1,i+lanesum,outgoingLanes[angleIdx]-i-1))
                                try:
                                    predecessorWay.K1_ConnectionsTurnLanesDirection[i+lanesum].append(link) if predecessorIsIncoming else predecessorWay.K2_ConnectionsTurnLanesOpposite[i+lanesum].append(link)
                                    successorWay.K2_incomingLanesFromK2[-i-1].append(link) if not successorIsIncoming else successorWay.K1_incomingLanesFromK1[-i-1].append(link)
                                except:
                                    print("index out of range")
                                    print(len(predecessorWay.K1_ConnectionsTurnLanesDirection) if predecessorIsIncoming else len(predecessorWay.K2_ConnectionsTurnLanesOpposite))
                                    print(i+lanesum)
                                    print()
                                    print(len(successorWay.K2_incomingLanesFromK2) if not successorIsIncoming else len(successorWay.K1_incomingLanesfromK1))
                                    print(-i-1)
                    except:
                        print("Cant find Angle "+str(Angle)+" in List "+str(angles) )
                        print(predecessorWay.OSMId)
                        print(successorWay.OSMId)
                        print()