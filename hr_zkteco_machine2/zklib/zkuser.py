from struct import pack, unpack
from datetime import datetime, date

from zkconst import *

def getSizeUser(self):
    """Checks a returned packet to see if it returned CMD_PREPARE_DATA,
    indicating that data packets are to be sent

    Returns the amount of bytes that are going to be sent"""
    command = unpack('HHHH', self.data_recv[:8])[0] 
    if command == CMD_PREPARE_DATA:
        size = unpack('I', self.data_recv[8:12])[0]
        return size
    else:
        return False


def zksetuser(self, uid, userid, name, password, role):
    """Start a connection with the time clock"""
    command = CMD_SET_USER
    # 4	   6       10      27    1  6    5
    #uid, role, password, name, x,userid,y = unpack('4s4s10s27ss6s5s', userdata.ljust(57)[:57] )
    #command_string = pack('sxs8s28ss7sx8s16s', chr( uid ), chr(role), password, name, chr(1), '', userid, '' )
    # de momento nos apanamos con el uid = id
    command_string = pack('4s6s10sssss', chr( uid ), chr(role), password, '','', userid, '' )
    chksum = 0
    session_id = self.session_id
    reply_id = unpack('HHHH', self.data_recv[:8])[3]

    buf = self.createHeader(command, chksum, session_id,
        reply_id, command_string)
    self.zkclient.sendto(buf, self.address)
    #print buf
    print buf.encode("hex")[15:]
    try:
        self.data_recv, addr = self.zkclient.recvfrom(1024)
        self.session_id = unpack('HHHH', self.data_recv[:8])[2]
        return self.data_recv[8:]
    except:
        return False
    
    
def zkgetuser(self):
    """Start a connection with the time clock"""
    command = CMD_USERTEMP_RRQ
    command_string = '\x05'
    chksum = 0
    session_id = self.session_id
    reply_id = unpack('HHHH', self.data_recv[:8])[3]

    buf = self.createHeader(command, chksum, session_id,
        reply_id, command_string)
    self.zkclient.sendto(buf, self.address)
    #print "buffer"
    #print buf.encode("hex")
    try:
        self.data_recv, addr = self.zkclient.recvfrom(1024)       
	#print self.data_recv.encode("hex")
        if getSizeUser(self):
            bytes = getSizeUser(self)
            while bytes > 0:
                data_recv, addr = self.zkclient.recvfrom(1032)
                self.userdata.append(data_recv)
                bytes -= 1024
            self.session_id = unpack('HHHH', self.data_recv[:8])[2]
            data_recv = self.zkclient.recvfrom(8)
        users = {}
        if len(self.userdata) > 0:
            #The first 4 bytes don't seem to be related to the user
            for x in xrange(len(self.userdata)):
                if x > 0:
                    self.userdata[x] = self.userdata[x][8:]
            userdata = ''.join( self.userdata )     
            userdata = userdata[11:]

	    userdata =  userdata.encode("hex")
            while len(userdata) > 56:	
		uid, role, password, name, x,userid,y = unpack('4s4s10s27ss6s5s', userdata.ljust(57)[:57] )
		
                #uid, role, password, name, userid = unpack( '2s2s8s28sx31s', userdata.ljust(72)[:72] )	
                #uid = int( uid.encode("hex"), 16)
		uid = int( uid, 16)
		
                # Clean up some messy characters from the user name
                password = password.split('\x00', 1)[0]
                password = unicode(password.strip('\x00|\x01\x10x'), errors='ignore')
		p=''
		for c in range(0,10,2):
			if password[c] == '3':
				#print password[c]
				p = p+str(password[c+1])

                #uid = uid.split('\x00', 1)[0]
                #userid = unicode(userid.strip('\x00|\x01\x10x'), errors='ignore')
                userid = int( userid, 16)
                name = name.split('\x00', 1)[0]
                
                if name.strip() == "":
                    name = uid
                
                #users[uid] = (userid, name, int( role.encode("hex"), 16 ), password)
                users[uid] = (userid, name, int( role, 16 ), p)
                
                #print("%d, %s, %s, %s, %s" % (uid, userid, name, int( role.encode("hex"), 16 ), p))
                userdata = userdata[56:]
                
        return users
    except:
        return False
    

def zkclearuser(self):
    """Start a connection with the time clock"""
    command = CMD_CLEAR_DATA
    command_string = ''
    chksum = 0
    session_id = self.session_id
    reply_id = unpack('HHHH', self.data_recv[:8])[3]

    buf = self.createHeader(command, chksum, session_id,
        reply_id, command_string)
    self.zkclient.sendto(buf, self.address)
    #print buf.encode("hex")
    try:
        self.data_recv, addr = self.zkclient.recvfrom(1024)
        self.session_id = unpack('HHHH', self.data_recv[:8])[2]
        return self.data_recv[8:]
    except:
        return False


def zkclearadmin(self):
    """Start a connection with the time clock"""
    command = CMD_CLEAR_ADMIN
    command_string = ''
    chksum = 0
    session_id = self.session_id
    reply_id = unpack('HHHH', self.data_recv[:8])[3]

    buf = self.createHeader(command, chksum, session_id,
        reply_id, command_string)
    self.zkclient.sendto(buf, self.address)
    #print buf.encode("hex")
    try:
        self.data_recv, addr = self.zkclient.recvfrom(1024)
        self.session_id = unpack('HHHH', self.data_recv[:8])[2]
        return self.data_recv[8:]
    except:
        return False
