"""Message decoding functions, taken from pyacaia."""
import logging

from .const import (
    HEADER1,
    HEADER2,
)

_LOGGER = logging.getLogger(__name__)

class Message(object):

    def __init__(self,msgType,payload):
        self.msgType=msgType
        self.payload=payload
        self.value=None
        self.button=None
        self.time=None

        if self.msgType==5:
            self.value=self._decode_weight(payload)

        elif self.msgType==11:
            if payload[2]==5:
                self.value=self._decode_weight(payload[3:])
            elif payload[2]==7:
                self.time=self._decode_time(payload[3:])
            _LOGGER.debug('heartbeat response (weight: '+str(self.value)+' time: '+str(self.time))

        elif self.msgType==7:
            self.time = self._decode_time(payload)
            _LOGGER.debug('timer: '+str(self.time))

        elif self.msgType==8:
            if payload[0]==0 and payload[1]==5:
                self.button='tare'
                self.value=self._decode_weight(payload[2:])
                _LOGGER.debug('tare (weight: '+str(self.value)+')')
            elif payload[0]==8 and payload[1]==5:
                self.button='start'
                self.value=self._decode_weight(payload[2:])
                _LOGGER.debug('start (weight: '+str(self.value)+')')
            elif (payload[0]==10 and payload[1]==7) or (payload[0]==10 and payload[1]==5):
                self.button='stop'
                self.time = self._decode_time(payload[2:])
                self.value = self._decode_weight(payload[6:])
                _LOGGER.debug('stop time: '+str(self.time)+' weight: '+str(self.value))
            elif payload[0]==9 and payload[1]==7:
                self.button='reset'
                self.time = self._decode_time(payload[2:])
                self.value = self._decode_weight(payload[6:])
                _LOGGER.debug('reset time: '+str(self.time)+' weight: '+str(self.value))
            else:
                self.button='unknownbutton'
                _LOGGER.debug('unknownbutton '+str(payload))


        else: 
            _LOGGER.debug('message '+str(msgType)+': %s' %payload)

    def _decode_weight(self,weight_payload):
        value= ((weight_payload[1] & 0xff) << 8) + (weight_payload[0] & 0xff)
        unit=  weight_payload[4] & 0xFF;
        if (unit == 1): value /= 10.0
        elif (unit == 2): value /= 100.0
        elif (unit == 3): value /= 1000.0
        elif (unit == 4): value /= 10000.0
        else: raise Exception('unit value not in range %d:' % unit)

        if ((weight_payload[5] & 0x02) == 0x02):
            value *= -1
        return value

    def _decode_time(self,time_payload):
        value = (time_payload[0] & 0xff) * 60
        value = value + (time_payload[1])
        value = value + (time_payload[2] / 10.0)
        return value
    
class Settings(object):
    
    def __init__(self,payload):
        # payload[0] is unknown
        self.battery = payload[1] & 0x7F
        if payload[2]==2:
            self.units = 'grams'
        elif payload[2]==5:
            self.units = 'ounces'
        else:
            self.units = None
        # payload[2 and 3] is unknown
        self.auto_off = payload[4] * 5
        # payload[5] is unknown
        self.beep_on = payload[6]==1
        # payload[7-9] unknown
        _LOGGER.debug('settings: battery='+str(self.battery)+' '+str(self.units)
                +' auto_off='+str(self.auto_off)+' beep='+str(self.beep_on))
        _LOGGER.debug('unknown settings: '+str([payload[0],payload[1]&0x80,payload[3],
                      payload[5],payload[7],payload[8], payload[9]]))
    

def decode(bytes):
    """Return a tuple - first element is the message, or None
       if one not yet found.  Second is are the remaining
       bytes, which can be empty
       Messages are encoded as the encode() function above,
       min message length is 6 bytes
       HEADER1 (0xef)
       HEADER1 (0xdd)
       command 
       length  (including this byte, excluding checksum)
       payload of length-1 bytes
       checksum byte1
       checksum byte2
       
    """
    messageStart = -1
   
    for i in range(len(bytes)-1):
        if bytes[i]==HEADER1 and bytes[i+1]==HEADER2:
            messageStart=i
            break
    if messageStart<0 or len(bytes)-messageStart<6:
        return (None,bytes)

    messageEnd  = messageStart+bytes[messageStart+3]+5

    if messageEnd>len(bytes):
        return (None,bytes)

    if messageStart>0:
        _LOGGER.debug("Ignoring "+str(i)+" bytes before header")

    cmd = bytes[messageStart+2]
    if cmd==12:
        msgType = bytes[messageStart+4]
        payloadIn = bytes[messageStart+5:messageEnd]
        return (Message(msgType,payloadIn),bytes[messageEnd:])
    if cmd==8:
        return (Settings(bytes[messageStart+3:]),bytes[messageEnd:])

    _LOGGER.debug("Non event notification message command "+str(cmd)+' '
                +str(bytes[messageStart:messageEnd]))
    return (None,bytes[messageEnd:])


def notification_handler(sender, data) -> None:
    msg = decode(data)[0]
    if isinstance(msg, Settings):
        print(f"Battery: {msg.battery}")
        print(f"Units: {msg.units}")
    elif isinstance(msg, Message):
        print(f"Weight: {msg.value}")