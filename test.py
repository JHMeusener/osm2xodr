#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 14:59:36 2019

@author: jhm
"""

from OSMParser.OpenDriveWriting import  writeOdrive, openDriveRoad, openDriveLane, openDriveRoadMark,openDriveJunction,openDriveLaneLink,openDriveRoadLink 
from OSMParser.OSMparsing import parseAll, OSMNode, OSMJunction, OSMNodeLink, OSMWay
from OSMParser.OSM2XODRconv import LaneAndRoadCreator, convertOSM

parseAll('/Users/jhmeusener/Desktop/Arbeit/campusFreudenberg.osm')

convertOSM()

string = writeOdrive()
with open('/Users/jhmeusener/Desktop/Arbeit/output.xodr', 'wt', encoding='utf-8') as f:
    f.write(string)

'''
for node in OSMNode.allOSMNodes.values():
    if not node.isJunction and len(node.wayIDList)>0:
        try:
            print(len(OSMNodeLink.nodes[node.id]))
        except:
            pass
'''
    



for way in OSMWay.allWays.values():
    print("""
         Id: {0}
         laneNumberDirection {1}
         laneNumberOpposite {2}
         K1Node {3}
         K2Node {4}
         K1_turnLanesDirection {5}
         K1_ConnectionsTurnLanesDirection {6}
         K1_incomingLanesFromK1 {7}
         K2_turnLanesOpposite {8}
         K2_ConnectionturnLanesOpposite {9}
         K2_incomingLanesFromK2 {10}
         K1_Angles {11}
         K2_Angles {12}
         K1_OSMLinks {13}
         K2_OSMLinks {14}
         K1_OutgoingLanes {15}
         K2_OutgoingLanes {16}
         K1_Ways {17}
         K1_WaysDirection {18}
         K2_Ways {19}
         K2_WaysDirection {20}
          
    
    """.format(way.id,
        way.laneNumberDirection,
        way.laneNumberOpposite,     
        way.K1Node,
        way.K2Node,
        
        way.K1_turnLanesDirection,
        way.K1_ConnectionsTurnLanesDirection,
        way.K1_incomingLanesFromK1,
        way.K2_turnLanesOpposite,
        way.K2_ConnectionsTurnLanesOpposite,
        way.K2_incomingLanesFromK2,
        
        way.K1_Angles,
        way.K2_Angles,
        
        way.K1_OSMLinks,
        way.K2_OSMLinks,
        
        way.K1_OutgoingLanes,
        way.K2_OutgoingLanes,
        
        way.K1_Ways,
        way.K1_WaysDirection,
        way.K2_Ways,
        way.K2_WaysDirection))
