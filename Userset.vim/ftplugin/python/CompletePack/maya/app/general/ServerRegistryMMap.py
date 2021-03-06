"""
Provides an interface to the commandPort mmap registry file which is used to 
keep track of commandPorts on Windows.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import mmap
import socket
import struct

def getInstance():
    """ 
    ServerRegistryMMap is a singleton class, the mmap file is opened when the instance is
    created and it is not closed until this module is removed from memory (Maya exit).
    Any instances of which start up after this one will then be able to see the contents of
    the file.
    
    Returns the ServerRegistryMMap singleton 
    """
    if ServerRegistryMMap.instance is None:
        ServerRegistryMMap.instance = ServerRegistryMMap()
    return ServerRegistryMMap.instance

def registerServer(serverName, addrFamily):
    """
    Allocate and register a server mapping for the supplied name. 
    Note: Only used on MS Windows, other platforms can use a normal socket file.
    
    serverName - ie 'commandPort1'
    addrFamily - socket.AF_*
    Returns (host,port) for the corresponding INET server
    """
    s = socket.socket(addrFamily, socket.SOCK_STREAM)
    if addrFamily is socket.AF_INET:
        host = '127.0.0.1'
    else:
        host = '::1'
    for port in range(50007,65535):
        try:
            sockAddr = (host, port)
            s.bind(sockAddr)
            s.close(); s = None; break
        except socket.error:
            continue
    if s is not None:
        raise RuntimeError(maya.stringTable['y_ServerRegistryMMap.kCouldNotFindFreePort'])
    activeServers = getInstance()
    activeServers.addServer(serverName, sockAddr[1])
    return sockAddr


class ServerRegistryMMap:
    """
    Windows only, manage the server registry mmap file.  This maps command 
    port names to port numbers. Is not intended to be used between 
    Maya instances.
    """
    # mmap file is 3808 bytes long and
    # structured as:
    # bits 0 - 31 : bit mask indicating active servers
    # 32 sockmaps: stored in network byte-order
    # struct sockmap {
    #   char unix_path[108];
    #   unsigned short port;
    # }
    # 220 bytes usused space
    #
    instance = None
    def __init__(self):
        mmap_filename = 'Maya_Unix_Socket_Share'
        self.recordStruct = struct.Struct('!108sH')
        sockmap_num_records = 34
        self.bitmapStruct = struct.Struct('I')
        mmap_bytes = self.bitmapStruct.size + sockmap_num_records * self.recordStruct.size
        self._mfile = mmap.mmap(-1, length=mmap_bytes, tagname=mmap_filename, access=mmap.ACCESS_WRITE)
    
    def offsetToRecord(self, i):
        """ returns the byte offset to the ith record """
        return self.bitmapStruct.size + i * self.recordStruct.size
        
    def getBitmap(self):
        """ Gets the active server bitmap """
        self._mfile.seek(0)
        return self.bitmapStruct.unpack(self._mfile.read(self.bitmapStruct.size))[0]
    
    def setBitmap(self,bitmap):
        """ Updates the active server bitmap """
        self._mfile.seek(0)
        self._mfile.write(self.bitmapStruct.pack(bitmap))
        self._mfile.flush(0, self.bitmapStruct.size)
    
    def getServer(self, i):
        """ Gets the ith server record, name is padded with zeros to 108 bytes """
        self._mfile.seek(self.offsetToRecord(i))
        record = self.recordStruct.unpack(self._mfile.read(self.recordStruct.size))
        return record
    
    def setServer(self, i, serverName, port):
        """ Updates the ith server record """
        offset = self.offsetToRecord(i)
        self._mfile.seek(offset)
        self._mfile.write(self.recordStruct.pack(serverName,port))
        self._mfile.flush(offset, self.recordStruct.size)
        
    def findServer(self, serverName):
        """ 
        Returns the index of the server name if it is already in the file
        otherwise return -1
        """
        for i in range(32):
            if self.getBitmap() & (0x1 << i):
                record = self.getServer(i)
                if record[0].rstrip('\x00') == serverName:
                    return i
        return -1
    
    def firstFreeSlot(self):
        """ Returns the first free slot, or None on failure """
        for i in range(32):
            if 0 == (self.getBitmap() & (0x1 << i)):
                return i
        return None
    
    def addServer(self, serverName, port):
        """ Add a new server record to the file """
        if self.findServer(serverName) >= 0:
            msg = maya.stringTable['y_ServerRegistryMMap.kCommandPortStillActive' ]
            raise RuntimeError(msg % serverName)
        i = self.firstFreeSlot()
        if i is None:
            # no free slots!
            msg = maya.stringTable['y_ServerRegistryMMap.kNoMoreCommandPortsAvailible' ]
            raise RuntimeError(msg)
        self.setBitmap(self.getBitmap() | (0x1 << i))
        self.setServer(i, serverName, port)

    def removeServer(self, serverName):
        """ 
        remove a server from the file
        Returns True on success, False otherwise 
        """
        i = self.findServer(serverName)
        if i >= 0:
            self.setBitmap(self.getBitmap() & ~(0x1 << i))
            self.setServer(i, '\x00', 0)
            return True
        return False
    
    def servers(self):
        """ Get the list of active servers """
        lst = []
        for i in range(32):
            if self.getBitmap() & (0x1 << i):
                lst.append(self.getServer(i))
        return lst
    
    def __str__(self):
        s = 'bitmap = '
        for i in range(32):
            if self.getBitmap() & (0x1 << (31-i)):
                s += '1'
            else:
                s += '0'
        s += '\n'
        lst = self.servers()
        for name,port in lst:
            s += '%s [%d]\n' %(name.rstrip('\x00'),port)
        return s
    
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
