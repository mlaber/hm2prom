#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""hm2prom.py: expose states and variables of the homematic home automation system for prometheus ."""

__author__      = "Markus Laber"
__copyright__   = "Copyright 2021, Markus Laber"
__license__ = "GPL"
__version__ = "0.1.33"
__email__ = "markus@relab.rocks"


import xml.etree.ElementTree as ET
import urllib.request
import time
import traceback
import importlib.util
import sys
#sys.path.append("./lib/client_python")     #provide local versions of libs if not provide by system via pip install
from prometheus_client import start_http_server, Gauge


##############DECLARATIONS#################################


# Set and initialize global variables
#global channel_ise_ids
#channel_ise_ids=None
#channel_list=[]

# Generic Variable
Homematic_CCU_URL="http://192.168.17.10"
Interval=20  #Count in seconds between fetching results
HTTP_Port=9110 #TCP port for prometheus metric exposure

# Declaration for prometheus state metrics (hm2prom_states) the labels have to be declared
# here and get filled in the main function
hm2prom_states = Gauge('hm2prom_states', 'Homematic export metrics', [
    'datapoint_ise_id',
    'datapoint_name',
    'datapoint_type',
    'datapoint_value_type',
    'datapoint_value_unit',
    'channel_iseid',
    'channel_address',
    'channel_name',
    'channel_type',
    'channel_parent_device',
    'channel_direction',
    'channel_rooms',
    'channel_functions',
    'parent_device_ise_id',
    'parent_device_address',
    'parent_device_name',
    'parent_device_type'])


# Declaration for prometheus sysvar metrics (hm2prom_sysvar) the labels have to be declared here
#  and get filled in the main function
hm2prom_sysvar = Gauge('hm2prom_sysvar', 'Homematic export sysvar', [
    'sysvar_ise_id',
    'sysvar_name',
    'sysvar_type',
    'sysvar_value_list',
    'sysvar_value_unit',
    'sysvar_value_string'])     # This field is used if a value contains alphanumerich characters. Prometheus doesn´t support non numeric values so this
                                # values get transformed to a label and are written in this field.




# Declaration for prometheus rssi RX (receive radio strength  of devices)  metrics (hm2prom_rssi_rx) the labels have to be declared
#  here and get filled in the main function
hm2prom_rssi_rx = Gauge('hm2prom_rssi_rx', 'Homematic export rssi (receive) radio strength', [
    'rssi_address',
    'rssi_devicename',
    'rssi_room',
    'rssi_direction'])

# Declaration for prometheus rssi TX (sendig radio strength  of devices)  metrics (hm2prom_rssi_tx) the labels have to be declared
#  here and get filled in the main function
hm2prom_rssi_tx = Gauge('hm2prom_rssi_tx', 'Homematic export rssi (receive) radio strength', [
    'rssi_address',
    'rssi_devicename',
    'rssi_room',
    'rssi_direction'])

# Homematic CCU URL paths as described in https://www.homematic-inside.de/software/addons/item/xmlapi
CCU_roomlist_URL="/config/xmlapi/roomlist.cgi"
CCU_devicelist_URL="/config/xmlapi/devicelist.cgi"
CCU_state_URL="/config/xmlapi/state.cgi"
CCU_statelist_URL="/config/xmlapi/statelist.cgi"
CCU_functionlist_URL="/config/xmlapi/functionlist.cgi"
CCU_sysvarlist_URL="/config/xmlapi/sysvarlist.cgi"
CCU_rssilist_URL="/config/xmlapi/rssilist.cgi"


# XML Data model of the homematic CCU:
# The XML Data model of the CCU, which is represented by the xmlapi consists of the following major elemenets
# 1. Devicess:   Physical or virtual device which is connected to the ccu - a device contais channels
# 2. Channels:   A channel is a sensor or actuator which measures or controlls a single action
# 3. States:     A state are measured values from a channel historicized by a timestamp
# 4. Rooms:      A room is ususally a physical location which groups channels
# 5. Functions:  A function groups channels which are used for the same building function group e.g.  environment, light, ..
# 6. System Variable: Variables which could be used in homematic web-ui programms and in homeamtic scripts
# 7. RSSI: Information about the signal strength of homematic wireless devices RX (receiving) TX (sending) direction

# fetch and cache devices and rommslists from the CCU for later processing and performace optimization,
#  querys can take some time due to limited CCU ressource,
devlist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL+CCU_devicelist_URL).read())
roomlist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL+CCU_roomlist_URL).read())
statelist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL+CCU_statelist_URL).read())
functionlist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL+CCU_functionlist_URL).read())
sysvarlist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL+CCU_sysvarlist_URL).read())
rssilist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL+CCU_rssilist_URL).read())


#############FUNCTIONS#################################



def get_rooms_for_channel(channel_iseid):        # Get room for channel out of roomlist
    global channel_rooms
    channel_rooms=[]
    if channel_iseid is not None:
        try:
            for room in roomlist.iter('room'):
                    for channel in room.iter('channel'):
                        if channel.attrib.get('ise_id') == channel_iseid:  # Extract all rooms for the channel write it in a list.
                            channel_rooms.append(room.attrib.get('name'))
        except:
            print("Failed to find room for this channel")
    return (channel_rooms)


def get_functions_for_channel(channel_iseid):        # Get room for channel out of roomlist
    global channel_functions
    channel_functions=[]
    if channel_iseid is not None:
        try:
            for functions in functionlist.iter('function'):
                    for channel in functions.iter('channel'):
                        if channel.attrib.get('ise_id') == channel_iseid:  # Extract all rooms for the channel write it in a list.
                            channel_functions.append(functions.attrib.get('name'))
        except:
            print("Failed to get functions for this channel")
    return (channel_functions)


def get_channel_information(channel_iseid):  # Get relevant information for the channel and write it to dictonary "channel_information"
    global channel_information
    if channel_iseid is not None:
        try:
            for channel in devlist.iter('channel'):
                if channel.attrib.get('ise_id') == channel_iseid:

                    channel_information = {
                        'channel_ise_ids': channel.attrib.get('ise_id'),
                        'channel_address' : channel.attrib.get('address'),
                        'channel_name': channel.attrib.get('name'),
                        'channel_type': channel.attrib.get('type'),
                        'channel_parent_device': channel.attrib.get('parent_device'),
                        'channel_direction': channel.attrib.get('direction')
                    }
        except:
                print("Failed to get channel iformation for this device")
    return (channel_information)


def get_channels_ise_ids(device_ise_id):
    global channel_ise_ids
    channel_ise_ids =[]  # empty list for appending
    if device_ise_id is not None:
        try:
            for channel in devlist.iter('channel'):
                if channel.attrib.get('parent_device') == device_ise_id:  # Extract all channels which belong to the given parent device ise_id and write it in a list.
                    channel_ise_ids.append(channel.attrib.get('ise_id'))
        except:
            print("Failed to get channels for this device")
    return (channel_ise_ids)


def get_device_by_address(device_address):      # Resolve device ise_id by there hardware address, needed for mapping of RSSI strength
    global device_by_address
    device_by_address = []
    if device_address is not None:
        try:
            for address in devlist.iter('device'):
                if channel.attrib.get('address') == device_address:  # Extract matching channel from devlist
                            device_information = {
                                'device_name': device.attrib.get("name"),
                                'device_address': device.attrib.get("address"),
                                'device_ise_id': device.attrib.get("ise_id"),
                                'device_type': device.attrib.get("device_type")
                            }
        except:
            print("Failed to get device by address")
    return (device_information)


def get_channel_parent_deviceinfo(channel_iseid):        # Get parent for channel
    global channel_parent_deviceinfo
    channel_parent_deviceinfo=[]
    if channel_iseid is not None:
        try:
            for channel in devlist.iter('channel'):
                if channel.attrib.get('ise_id') == channel_iseid:  # Extract matching channel from devlist
                        channel_parent_device = channel.attrib.get('parent_device')
                        for device in devlist.iter('device'):
                            if device.attrib.get('ise_id') == channel_parent_device:
                                parent_device_information = {
                                    'parent_device_name': device.attrib.get("name"),
                                    'parent_device_address': device.attrib.get("address"),
                                    'parent_device_ise_id': device.attrib.get("ise_id"),
                                    'parent_device_type': device.attrib.get("device_type")
                                }
        except:
            print("Failed to get parent device for this channel")
    return (parent_device_information)


def get_datapoints_by_channel(channel_iseid):  # Get all the datapoints for the channel there are sensors with mutlitple values on one channel
    global datapoints_by_channel
    datapoints_by_channel=[]
    if channel_iseid is not None:
        try:
            for channel in statelist.iter('channel'):
                if channel.attrib.get('ise_id') == channel_iseid:
                    #print("channel possiton id:", channel)  # dbg
                    for datapoint in channel.iter('datapoint'):
                        #print ("datapoit possiton id:", datapoint) #dbg
                        datapoints_by_channel.append(datapoint.attrib.get('ise_id'))
        except:
                print("Failed to get channel for datapoint")
    return (datapoints_by_channel)


def get_states_by_datapoint(datapoint_iseid):  # Get state and value information (payload) for datapoints
    global states_by_datapoint
    state_by_datapoint={}
    if datapoint_iseid is not None:
        try:
            for datapoint in statelist.iter('datapoint'):
                if datapoint.attrib.get('ise_id') == datapoint_iseid:
                    #print("datapoint possiton id:", datapoint)  # dbg
                    state_by_datapoint.update({
                            'datapoint_ise_id': datapoint.attrib.get('ise_id'),
                            'datapoint_name': datapoint.attrib.get('name'),
                            'datapoint_type': datapoint.attrib.get('type'),
                            'datapoint_value': datapoint.attrib.get('value'),
                            'datapoint_value_type': datapoint.attrib.get('valuetype'),
                            'datapoint_value_unit': datapoint.attrib.get('valueunit'),
                            'datapoint_timestamp_epoch': datapoint.attrib.get('timestamp'), # Timestamp is in unix epoch and UTC
                             })
                    if state_by_datapoint.get('datapoint_value')=='false':      # Check if homeatic value is boolean
                        # "true" or "false" which is "1" and "0" by convention in prometheus
                        #print("False State") #dbg
                        state_by_datapoint["datapoint_value"] = 0
                    if state_by_datapoint.get('datapoint_value') == 'true':
                        #print("True State")  # dbg
                        state_by_datapoint["datapoint_value"] = 1
                        #print ("Matching Datapoint ISE_ID:", datapoint.attrib.get('ise_id')) #dbg

        except:
                print("Failed to get state for datapoint")
    return (state_by_datapoint)


def get_state_by_sysvar(sysvar_ise_id):  #Get state and value information (payload) for sysvars
    global state_by_sysvar
    state_by_sysvar={}
    if sysvar_ise_id is not None:
        try:
            for sysvar in sysvarlist.iter('systemVariable'):
                if sysvar.attrib.get('ise_id') == sysvar_ise_id:
                    #print("sysvar possiton id:", sysvar)  # dbg
                    state_by_sysvar.update({
                            'sysvar_ise_id': sysvar.attrib.get('ise_id'),
                            'sysvar_name': sysvar.attrib.get('name'),
                            'sysvar_type': sysvar.attrib.get('type'),
                            'sysvar_value': sysvar.attrib.get('value'),
                            'sysvar_value_type': sysvar.attrib.get('valuelist'),
                            'sysvar_value_unit': sysvar.attrib.get('unit'),
                            'sysvar_timestamp_epoch': sysvar.attrib.get('timestamp'), # Timestamp is in unix epoch and UTC
                             })
                    if state_by_sysvar.get('sysvar_value')=='false':      # Check if homeatic value is boolean "true" or "false" which is "1" and "0" by convention in prometheus
                        #print("False State") #dbg
                        state_by_sysvar["sysvar_value"] = 0
                    if state_by_sysvar.get('sysvar_value') == 'true':
                        #print("True State")  # dbg
                        state_by_sysvar["sysvar_value"] = 1
                        #print ("Matching sysvar ISE_ID:", sysvar.attrib.get('ise_id')) #dbg
        except:
                print("Failed to get state for sysvar")
    return (state_by_sysvar)


def get_rssi_by_address(device_address):  #Get state and value information (payload) for sysvars
    global rssi_by_address
    state_by_sysvar={}
    if device_address is not None:
        try:
            for rssi in rssilist.iter('rssi'):
                if rssi.attrib.get('device') == device_address:
                    rssi_by_address.update({
                            'rssi_address': rssi.attrib.get('device'),
                            'rssi_rx_value': rssi.attrib.get('rx'),
                            'rssi_tx_value': rssi.attrib.get('tx'),
                            'rssi_ise_id': get_device_by_address(rssi),
                             })
        except:
                print("Failed to get rssi information for address")
    return (rssi_by_address)

#ToDo Get Device RSSI by address fetch rrsi data from the parent function and store them with the parent information

#########################MAIN##############################################################

start_http_server(HTTP_Port)    # Start prometheus HTTP server for metric exposure


# Generate a list with all channels of all devices registered in the CCU. This chhannelist ist the base information for
#  the upcoming querries.
global channel_list
channel_list=[]
for device in devlist.iter('device'):
    if device is not None: # Test for None addresses
        device_ise_id = device.attrib.get("ise_id")
        device_channels = get_channels_ise_ids(device_ise_id)
        channel_list.extend(device_channels)
print ("channel_list:", channel_list) #dbg might be helfull to identify consistence issues between ccu and script
print("Number of registered channels: %s" % len(channel_list)) #dbg
print("\n")


#Generate a list with all system variables registered in the CCU..
global sysvar_list
sysvar_list=[]
for sysvar in sysvarlist.iter('systemVariable'):
    if sysvar is not None: # Test for None addresses
        sysvar_ise_id = sysvar.attrib.get("ise_id")
        sysvar_list.append(sysvar_ise_id)
print ("sysvar_list:", sysvar_list) # dbg might be helfull to identify consistence issues between ccu and script
print("Number of registered system variables: %s" % len(sysvar_list)) #dbg
print("\n")


#Generate a list with addresses for devices with RSSI radio strenght parameters.
global rssi_list
rssi_list=[]
for rssi in rssilist.iter('rssi'):
    if rssi is not None: # Test for None addresses
        rss = sysvar.attrib.get("device")
        rssi_list.append(sysvar_ise_id)
print ("rssi_list:", rssi_list) # dbg might be helfull to identify consistence issues between ccu and script
print("Number of wireless devices: %s" % len(rssi_list)) #dbg
print("\n")


# Iterate every n seconds over channels in channel_list and build a dictionary for each channel
while True:
    time.sleep(Interval)
    try:
        statelist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL + CCU_statelist_URL).read())
        sysvarlist = ET.fromstring(urllib.request.urlopen(Homematic_CCU_URL + CCU_sysvarlist_URL).read())

        for channel in channel_list:  # Refetch actual states every loop
            channel_roomname = get_rooms_for_channel(channel)
            channel_functions = get_functions_for_channel(channel)
            channel_parent = get_channel_parent_deviceinfo(channel)
            channel_information = get_channel_information(channel)
            channel_datapoints = get_datapoints_by_channel(channel)


            try:                  
                for datapoint in channel_datapoints:  # Has to be called for every datapoint all labels have to be provided
                    current_datapoint=get_states_by_datapoint(datapoint)  # get the current datapoint dict
                    if current_datapoint is not None and str(current_datapoint.get('datapoint_value')) !='':
                        try:
                            float(current_datapoint.get('datapoint_value') )
                            hm2prom_states.labels(
                            datapoint_ise_id=current_datapoint.get('datapoint_ise_id'),
                            datapoint_name= current_datapoint.get('datapoint_name'),
                            datapoint_type=current_datapoint.get('datapoint_type'),
                            datapoint_value_type=current_datapoint.get('datapoint_value_type'),
                            datapoint_value_unit=current_datapoint.get('datapoint_value_unit'),
                            channel_iseid=channel,
                            channel_address=channel_information.get('channel_address'),
                            channel_name=channel_information.get('channel_name'),
                            channel_type=channel_information.get('channel_type'),
                            channel_parent_device=channel_information.get('channel_parent_device'),
                            channel_direction=channel_information.get('channel_direction'),
                            channel_rooms=channel_roomname,
                            channel_functions=channel_functions,
                            parent_device_ise_id=channel_parent.get('parent_device_ise_id'),
                            parent_device_address=channel_parent.get('parent_device_address'),
                            parent_device_name=channel_parent.get('parent_device_name'),
                            parent_device_type=channel_parent.get('parent_device_type')).set(current_datapoint.get('datapoint_value'))

                        except ValueError:
                            print ("datapoint_value could not be converted to a float")
                            print(current_datapoint)


                for sysvar in sysvar_list:  # Has to be called for every sysvar all labels have to be provided
                    current_sysvar=get_state_by_sysvar(sysvar)  # get the current sysvar dict
                    if current_sysvar is not None and current_sysvar.get('sysvar_value') is not None:
                        try:
                            if isinstance(current_sysvar.get('sysvar_value'), (int,float,complex)):  # Test if value is a number
                                hm2prom_sysvar.labels(
                                sysvar_ise_id=current_sysvar.get('sysvar_ise_id'),
                                sysvar_name= current_sysvar.get('sysvar_name'),
                                sysvar_type=current_sysvar.get('sysvar_type'),
                                sysvar_value_list=current_sysvar.get('sysvar_value_type'),
                                sysvar_value_string="",
                                sysvar_value_unit=current_sysvar.get('sysvar_value_unit')).set(current_sysvar.get('sysvar_value'))

                            if isinstance(current_sysvar.get('sysvar_value'), (str)):  # Test if variable is a string
                                    #print ("IS A STRING VARIABLE") #DBG
                                    if current_sysvar.get('sysvar_value').isnumeric() :  # Test if the string contains numeric values
                                        hm2prom_sysvar.labels(
                                        sysvar_ise_id=current_sysvar.get('sysvar_ise_id'),
                                        sysvar_name= current_sysvar.get('sysvar_name'),
                                        sysvar_type=current_sysvar.get('sysvar_type'),
                                        sysvar_value_list=current_sysvar.get('sysvar_value_type'),
                                        sysvar_value_string="",
                                        sysvar_value_unit=current_sysvar.get('sysvar_value_unit')).set(current_sysvar.get('sysvar_value'))

                                    else:
                                        try:
                                            float(current_sysvar.get('sysvar_value') )
                                            hm2prom_sysvar.labels(
                                            sysvar_ise_id=current_sysvar.get('sysvar_ise_id'),
                                            sysvar_name= current_sysvar.get('sysvar_name'),
                                            sysvar_type=current_sysvar.get('sysvar_type'),
                                            sysvar_value_list=current_sysvar.get('sysvar_value_type'),
                                            sysvar_value_string="",
                                            sysvar_value_unit=current_sysvar.get('sysvar_value_unit')).set(current_sysvar.get('sysvar_value'))
                                            
                                        except ValueError:
                                            hm2prom_sysvar.labels(
                                            sysvar_ise_id=current_sysvar.get('sysvar_ise_id'),
                                            sysvar_name= current_sysvar.get('sysvar_name'),
                                            sysvar_type=current_sysvar.get('sysvar_type'),
                                            sysvar_value_list=current_sysvar.get('sysvar_value_type'),
                                            sysvar_value_unit=current_sysvar.get('sysvar_value_unit'),
                                            sysvar_value_string=current_sysvar.get('sysvar_value'))
                                         
                                        else:
                                            def f():        # Python style NoOp 
                                                pass
                                    
                                   

                        except ValueError:  
                            print ("sysvar_value has unexpected type:")
                            print(current_sysvar)
                            print ("\n") #db
                            print ("Sysvar Value:")
                            print (current_sysvar.get('sysvar_value') )
                            print ("\n") #db
                            print ("is type:", type(current_sysvar.get('sysvar_value'))) 
                            print ("------- \n")
                           

            except:
                print("Error in processing results")  # dbg
                traceback.print_exc()
    except:
        print("XML parsing error or invalid XML received from CCU")  # Under some circumstances load? the CCU produces invalid XML output
        traceback.print_exc()



print ("exitpoint reached") #dbg
