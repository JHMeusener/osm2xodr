#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 14:14:34 2019

@author: jhm
"""

from .OSMparsing import OSMNode, OSMJunction, OSMNodeLink, OSMWay
import numpy as np

def writeOdrive():
    string= '''<?xml version="1.0" standalone="yes"?>
<OpenDRIVE>
    <header revMajor="1" revMinor="1" name="" version="1.00" date="Tue Mar 11 08:53:30 2014" north="0.0000000000000000e+00" south="0.0000000000000000e+00" east="0.0000000000000000e+00" west="0.0000000000000000e+00" maxRoad="3" maxJunc="0" maxPrg="0">
    </header>
    '''
    for road in openDriveRoad.roaddictionary.values():
        string += road.giveODriveString()
    string += '''
</OpenDRIVE>
    '''
    return string




class openDriveRoad:
    roadids = 1
    roaddictionary = {}
    OSMlinkToRoads = {}
    
    @staticmethod
    def reset():
        openDriveRoad.roadids = 1
        openDriveRoad.roaddictionary = {}
        openDriveRoad.OSMlinkToRoads = {}

    @staticmethod
    def giveId(road):
        openDriveRoad.roaddictionary[str(openDriveRoad.roadids)] = road
        openDriveRoad.roadids += 1
        return str(openDriveRoad.roadids-1)
    
    def __init__(self, length, x, y, hdg, osmnodelinkid, waytags, wayIsOpposite, geoparam = None):
        try:
            openDriveRoad.OSMlinkToRoads[osmnodelinkid].append(self)
        except:
            openDriveRoad.OSMlinkToRoads[osmnodelinkid] = [self]
        self.id = openDriveRoad.giveId(self)
        self.geometrietyp = 'line' if geoparam is None else 'poly3'
        self.geoparam = geoparam
        self.length = length
        self.x = x
        self.y = y
        self.hdg = hdg
        self.lanesLeft = []
        self.laneMiddle = []
        self.lanesRight = []
        self.RoadLinksPredecessor = []
        self.RoadLinksSuccessor = []
        openDriveRoad.roaddictionary[self.id] = self
        self.OSMWay = None
        self.osmnodelink = OSMNodeLink.links[str(osmnodelinkid)]
        self.OSMnodeid = str(OSMNodeLink.links[str(osmnodelinkid)].nodeid)
        self.OSMJunctionId = OSMNode.allOSMNodes[str(self.OSMnodeid)].idJunction
        self.odriveJunction = '-1'   ## nur die geraden sind die junctions - die Kurven sind einzellanes
    
    def giveODriveJunctionString(self, idx):
        string = ""
        for link in self.RoadLinksPredecessor:
            _, predecessor,  contactPoint = link.giveODriveJunction(self)
            string += '''
            <connection id="{0}" incomingRoad="{1}" connectingRoad="{2}" contactPoint="{3}">
            '''.format(str(idx), predecessor, self.id, contactPoint)
            for laneLink in link.openDriveLaneLinks:
                string += laneLink.giveOdriveJunctionString(self)
            string += '''
            </connection>
            '''

        if len(self.RoadLinksPredecessor) > 1:  # 
            
                string += link.giveODriveJunction(self)
        if len(self.RoadLinksSuccessor) > 1:  # 
            for link in self.RoadLinksSuccessor:
                string += link.giveODriveJunction(self)
        return string


    def giveODriveString(self):
        roadlinksPre = ""
        if len(self.RoadLinksPredecessor) > 0:
            roadlinksPre = self.RoadLinksPredecessor[0].giveODriveString(self)

        roadlinksSuc = ""
        if len(self.RoadLinksSuccessor) > 0:
            roadlinksSuc = self.RoadLinksSuccessor[0].giveODriveString(self)

        if self.geometrietyp == 'poly3':
            geo = '''
                <poly3 a="0" b="0" c="{0}" d="0"/>'''.format(self.geoparam)
        else:
            geo = '''
                <line/>'''

        leftlanes = ""
        for lane in self.lanesLeft:
            leftlanes += lane.giveODriveString()
        centerlanes = ""
        for lane in self.laneMiddle:
            centerlanes += lane.giveODriveString()
        rightlanes = ""
        for lane in self.lanesRight:
            rightlanes += lane.giveODriveString()

        string =  '''    
        <road name="" length="{0}" id="{1}" junction="{2}">
            <link>
                '''.format(self.length, self.id, self.odriveJunction) + '''
                {0}
                {1}'''.format(roadlinksPre,roadlinksSuc) + '''
            </link>
             <planView>
                <geometry s="0.0" x="{0}" y="{1}" hdg="{2}" length="{3}">
                '''.format(self.x, self.y, self.hdg, self.length) + geo + '''
                </geometry>
             </planView>
             <lanes>
                <laneSection s="0.0">
                    <left>{0}
                    </left>
                    <center>{1}
                    </center>
                    <right>{2}
                    </right>
                </laneSection>
            </lanes>
        </road>
        '''.format(leftlanes, centerlanes, rightlanes)
        return string

        
class openDriveLane:
    def __init__(self, laneid, OpendriveRoad, OSMWay):
        self.id = laneid
        self.road = OpendriveRoad
        self.OSMway = OSMWay
        self.type = 'driving'
        self.width = "2.75e+00"
        self.roadmark = "broken"
        if self.id == 0:
            self.width = "0.0"
            #self.roadmark
            self.type = 'none'

    def giveODriveString(self):
        predecessor = ""
        successor = ""
        #predecessor = '''<predecessor id="{0}"/>'''.format(self.OSMway.)

        return '''
                        <lane id="{0}" type="driving" level= "0">
                            <link>{1}{2}
                            </link>
                            <width sOffset="0.0" a="{3}" b="0.0" c="0.00" d="0.00"/>
                            <roadMark sOffset="0.00" type="{4}" weight="standard" color="standard" width="1.30e-01"/>
                        </lane>'''.format(self.id,predecessor, successor,self.width, self.roadmark)


class openDriveRoadMark:
    def __init__(self):
        self.type = 'broken'

class openDriveJunction:
    junctionids = 1
    junctiondictionary = {}
    junctions = {}
    roads = {}
    connections = {}
    
    @staticmethod
    def giveJunction(OSMWay, OSMNode):
        if str(OSMWay.id + OSMNode.id) in openDriveJunction.junctiondictionary:
            return openDriveJunction.junctiondictionary[OSMWay.id + OSMNode.id]
        else:
            j = openDriveJunction(OSMWay, OSMNode)
            return j

    @staticmethod
    def attachRoad(junctionID, ODriveRoad):
        try:
            openDriveJunction.roads[str(junctionID)].append(ODriveRoad)
        except:
            openDriveJunction.roads[str(junctionID)] = [ODriveRoad]
    
    @staticmethod
    def reset():
        openDriveJunction.junctionids = 1
        openDriveJunction.junctiondictionary = {}
    
    def __init__(self, OSMWay, OSMNode):
        self.id = str(openDriveJunction.junctionids)
        openDriveJunction.junctionids += 1
        self.OSMJunction = OSMJunction.allJunctions[OSMNode.id]
        self.OSMWay = OSMWay
        self.openDriveRoads = []
        self.openDriveRoadLinks = []
        
        self.incomingOSMWays = self.OSMJunction.incomingWays
        self.incomingOSMNodes = self.OSMJunction.incomingNodes
        self.outgoingOSMWays = self.OSMJunction.outgoingWays
        self.outgoingOSMNodes = self.OSMJunction.outgoingNodes
        self.OSMLinks = OSMNodeLink.nodes[OSMNode.id]
        
        openDriveJunction.junctions[str(self.id)] = self
        
        def giveODriveString(self):
            connections = openDriveJunction.roads[str(self.id)]
            connString = ""
            idx = 0
            for connection in connections:
                connString += connection.giveODriveJunctionString(idx)
                idx +=1

            string = '''
            <junction name="" id="{0}">'''.format(self.id)

        
                 
            
class openDriveLaneLink:
    def __init__(self, PredecessorRoad, SuccessorRoad, PredecessorLane, SuccessorLane):
        self.predecessor = PredecessorRoad
        self.successor = SuccessorRoad
        self.predecessorLane = PredecessorLane
        self.successorLane = SuccessorLane

    def giveOdriveJunctionString(self, oDriveRoad):
        if oDriveRoad.id == self.predecessor:
            return '\t\t\t<laneLink from="{0}" to="{1}"/>'.format(str(self.predecessorLane),str(self.successorLane))
        if oDriveRoad.id == self.successor:
            return '\t\t\t<laneLink from="{0}" to="{1}"/>'.format(str(self.successorLane),str(self.predecessorLane))
        return ""
    
class openDriveRoadLink:
    def __init__(self, oDriveRoadPredecessor, oDriveRoad, contactPointRoad, contactPointPredecessor):
        self.oDriveRoadPredecessor = oDriveRoadPredecessor
        self.oDriveRoad = oDriveRoad
        self.contactPointRoad = contactPointRoad
        self.contactPointPredecessor = contactPointPredecessor
        self.openDriveLaneLinks = []
        #oDriveRoadPredecessor.RoadLinksSuccessor.append(self)
        #oDriveRoad.RoadLinksPredecessor.append(self)

    def giveODriveJunction(self, oDriveRoadQuestion):
        if oDriveRoadQuestion.id == self.oDriveRoadPredecessor.id:
            return 'successorIs', self.oDriveRoad,  self.contactPointRoad
        if oDriveRoadQuestion.id == self.oDriveRoad.id:
            return 'predecessorIs', self.oDriveRoadPredecessor.id,  self.contactPointPredecessor

    def giveODriveString(self, oDriveRoadQuestion):
        if oDriveRoadQuestion.id == self.oDriveRoadPredecessor.id or oDriveRoadQuestion.id == self.oDriveRoad.id:
            order = "successor"
            roadOrJunction = "road" if self.oDriveRoad.odriveJunction == "-1" else "junction"
            contactpoint = self.contactPointRoad
            orderID = str(self.oDriveRoad.id) if self.oDriveRoad.odriveJunction == "-1" else str(self.oDriveRoad.odriveJunction)

            if oDriveRoadQuestion.id == self.oDriveRoad.id:
                order = "predecessor"
                contactpoint = self.contactPointPredecessor
                roadOrJunction = "road" if self.oDriveRoadPredecessor.odriveJunction == "-1" else "junction"
                orderID = str(self.oDriveRoadPredecessor.id) if self.oDriveRoadPredecessor.odriveJunction else str(self.oDriveRoadPredecessor.odriveJunction)
            if roadOrJunction == "road":
                dic =  {'string':'\t\t<{0} elementType="road" elementId="{1}" contactPoint="{2}" />'.format(order, orderID, contactpoint),
                        'contact':contactpoint,
                        'order':order,
                        'id':orderID,
                        'isJunction':roadOrJunction}
                return dic['string']
            else:
                dic =  {'string':'\t\t<{0} elementType="road" elementId="{1}" />'.format(order, orderID),
                        'contact':contactpoint,
                        'order':order,
                        'id':orderID,
                        'isJunction':roadOrJunction}
                return dic['string']
        else: return ""
