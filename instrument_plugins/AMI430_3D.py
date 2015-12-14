# QTlab driver for American Magnetics 430 magnet power supply.
# This version controls 3 solenoids and uses three instances of AMI430_single for that.
# For a single solenoid, use AMI430_single.
# For 2D vector operation, use AMI430_2D.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

#TODO:
#implement reference coord
#implement offset field

from instrument import Instrument
import instruments
import qt
import types
import socket
import logging
import time
from math import *
from numpy import *

class AMI430_3D(Instrument):
    
    #Global parameters
    #Important:
    #Set these values in accordance with the limits of each system
    #otherwise magnet quench or damage of equipment might occur
    
    #ratio between current and magnetic field
    COILCONSTANT_X = 0.0146       #T/A
    COILCONSTANT_Y = 0.0426       #T/A
    COILCONSTANT_Z = 0.1107       #T/A
    
    #Rated operating current in A, from spec sheet. A margin of 0.03A is added so that the rated fields fit in.
    #If the magnet quenches regularly, reduce these values!!!!
    CURRENTRATING_X = 68.53      #A
    CURRENTRATING_Y = 70.45      #A
    CURRENTRATING_Z = 81.33      #A
    
    #Rated magnetic field based on the two previous values
    #Note: in many cases, the vector operation is only allowed in a smaller range
    #Set the last value accordingly 
    FIELDRATING_X = COILCONSTANT_X*CURRENTRATING_X    #T
    FIELDRATING_Y = COILCONSTANT_Y*CURRENTRATING_Y    #T
    FIELDRATING_Z = COILCONSTANT_Z*CURRENTRATING_Z    #T
    FIELDRATING_XY = 1.0                                        #T
    FIELDRATING_XZ = 1.0
    FIELDRATING_YZ = 3.0
    FIELDRATING_XYZ = 1.0
    
    #Maximum ramp limits from datasheet
    CURRENTRAMPLIMIT_X = 0.2     #A/s
    CURRENTRAMPLIMIT_Y = 0.05     #A/s
    CURRENTRAMPLIMIT_Z = 0.08     #A/s
    FIELDRAMPLIMIT_X=COILCONSTANT_X*CURRENTRAMPLIMIT_X    #T/s
    FIELDRAMPLIMIT_Y=COILCONSTANT_Y*CURRENTRAMPLIMIT_Y    #T/s
    FIELDRAMPLIMIT_Z=COILCONSTANT_Z*CURRENTRAMPLIMIT_Z    #T/s
    
    #Persistent switch rated currents. 
    #These values are based on the autodetect function of the supply unit
    #typical values are ~50mA for wet systems and ~30mA for dry systems
    PSCURRENT_X=50            #mA
    PSCURRENT_Y=50            #mA
    PSCURRENT_Z=50            #mA
    
    #Heat and cooldown time for persistent switch
    PSHEATTIME_X=20       #s
    PSHEATTIME_Y=20       #s
    PSHEATTIME_Z=20       #s
    PSCOOLTIME_X=20       #s
    PSCOOLTIME_Y=20       #s
    PSCOOLTIME_Z=20       #s
    
    #soft parameters
    _mode=0x01
    _alpha=0.0
    _phi=0.0
    
    #soft parameters related to field offset
    _offseten=False
    _fieldoffset=0.0
    _alphaoffset=0.0
    _phioffset=0.0
    _field=0.0   

    #global parameter for the presence of persistent switch. Default is True.
    #Check your magnet configuration!
    PSWPRESENT_X=True
    PSWPRESENT_Y=True
    PSWPRESENT_Z=True
    
    #operation mode
    '''
    Available modes:
    
    MODE_RAW: individual magnets can be accessed directly. 
    
    MODE_X: only X magnet is driven, Y, Z magnets are at zero.
    
    MODE_Y: only Y magnet is driven, X, Z magnets are at zero.
    
    MODE_Z: only Z magnet is driven, X, Y magnets are at zero.
    
    MODE_XY: 2D vector operation, field amplitude and alpha can be set.
    
    MODE_XZ: 2D vector operation, field amplitude and phi can be set.
    
    MODE_YZ: 2D vector operation, field amplitude and phi can be set.
    
    MODE_XYZ: 3D vector operation, field amplitude and alpha,phi can be set.
    
    '''
    MODE_RAW=0x01
    MODE_X=0x02
    MODE_Y=0x04
    MODE_Z=0x08
    MODE_XY=0x10
    MODE_XZ=0x20
    MODE_YZ=0x40
    MODE_XYZ=0x80

    ###Init
    ###Parameters for each axis:
    #address: IP address of magnet controller. Has to be set on front panel. 
    #port: TCP port of magnet controller. Should be 7180
    #switchPresent: determines if driver handles persistent switch or not. Check
    #                your magnet configuration! Default is yes. Has to be forwarded to
    #                global parameter PSWPRESENT
     
    
    def __init__(self, name, addressX='192.168.2.3', addressY='192.168.2.2', addressZ='192.168.2.1', portX=7180, portY=7180, portZ=7180, mode=MODE_RAW, switchPresent_X=True, switchPresent_Y=True, switchPresent_Z=True):
        
        Instrument.__init__(self, name, tags=['measure'])
        
        #pass switchPresent_{X,Y,Z} to their global parameter
        self.PSWPRESENT_X=switchPresent_X
        self.PSWPRESENT_Y=switchPresent_Y
        self.PSWPRESENT_Z=switchPresent_Z
        
        self._create_parameters(mode)
        
        self.set_mode(mode, init=True)
        
        #We create the underlying instances of AMI430_single
        
        self._channelX=qt.instruments.create(name + '_X', 'AMI430_single', address=addressX, port=portX, switchPresent=switchPresent_X)
        self._channelY=qt.instruments.create(name + '_Y', 'AMI430_single', address=addressY, port=portY, switchPresent=switchPresent_Y)
        self._channelZ=qt.instruments.create(name + '_Z', 'AMI430_single', address=addressZ, port=portZ, switchPresent=switchPresent_Z)
        
        #and override the limits for each channel
        self._channelX.set_parameter_bounds('field', -self.FIELDRATING_X, self.FIELDRATING_X)
        self._channelX.set_parameter_bounds('rampRate', 0.0, self.FIELDRAMPLIMIT_X)
        
        self._channelY.set_parameter_bounds('field', -self.FIELDRATING_Y, self.FIELDRATING_Y)
        self._channelY.set_parameter_bounds('rampRate', 0.0, self.FIELDRAMPLIMIT_Y)

        self._channelZ.set_parameter_bounds('field', -self.FIELDRATING_Z, self.FIELDRATING_Z)
        self._channelZ.set_parameter_bounds('rampRate', 0.0, self.FIELDRAMPLIMIT_Z)
        
        self.add_function('reset')

        if mode & (self.MODE_RAW | self.MODE_X):
            self.add_function('rampToX')
            
        if mode & (self.MODE_RAW | self.MODE_Y):
            self.add_function('rampToY')
            
        if mode & (self.MODE_RAW | self.MODE_Z):
            self.add_function('rampToZ')
            
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            self.add_function('resetQuenchX')
            
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            self.add_function('resetQuenchY')

        if mode & (self.MODE_RAW | self.MODE_Z | self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_function('resetQuenchZ')
        
        self.get_all()
    
    def reset(self):                                                          ###TODO
        pass
    
    def _create_parameters(self, mode):
        
        if 'mode' not in self.get_parameter_names():                #only create it once
            self.add_parameter('mode', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={self.MODE_RAW:'Raw mode',
                                       self.MODE_X:'X magnet',
                                       self.MODE_Y:'Y magnet',
                                       self.MODE_Z:'Z magnet',
                                       self.MODE_XY:'XY magnet',
                                       self.MODE_XZ:'XZ magnet',
                                       self.MODE_YZ:'YZ magnet',
                                       self.MODE_XYZ:'XYZ magnet'})
        
        if self.PSWPRESENT_X & (mode & (self.MODE_RAW | self.MODE_X)): 
            self.add_parameter('pSwitchX', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'off',True:'on'})
            
        if self.PSWPRESENT_Y & (mode & (self.MODE_RAW | self.MODE_Y)):
            self.add_parameter('pSwitchY', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'off',True:'on'})   
        
        if self.PSWPRESENT_Z & (mode & (self.MODE_RAW | self.MODE_Z)):
            self.add_parameter('pSwitchZ', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'off',True:'on'})   

        if mode & (self.MODE_RAW | self.MODE_X):
            self.add_parameter('fieldX', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=-self.FIELDRATING_X, maxval=self.FIELDRATING_X,
                format='%.6f')
        elif mode & (self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            self.add_parameter('fieldX', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
        
        if mode & (self.MODE_RAW | self.MODE_Y):
            self.add_parameter('fieldY', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=-self.FIELDRATING_Y, maxval=self.FIELDRATING_Y,
                format='%.6f')
        elif mode & (self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('fieldY', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
            
        if mode & (self.MODE_RAW | self.MODE_Z):
            self.add_parameter('fieldZ', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=-self.FIELDRATING_Z, maxval=self.FIELDRATING_Z,
                format='%.6f')
        elif mode & (self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('fieldZ', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
        
        if mode & self.MODE_XY:
            self.add_parameter('field', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=0.0, maxval=self.FIELDRATING_XY,
                format='%.6f')
        elif mode & self.MODE_XZ:
            self.add_parameter('field', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=0.0, maxval=self.FIELDRATING_XZ,
                format='%.6f')
        elif mode & self.MODE_YZ:
            self.add_parameter('field', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=0.0, maxval=self.FIELDRATING_YZ,
                format='%.6f')
        elif mode & self.MODE_XYZ:
            self.add_parameter('field', type=types.FloatType,
                flags=Instrument.FLAG_SET | Instrument.FLAG_GET,
                units='T',
                minval=0.0, maxval=self.FIELDRATING_XYZ,
                format='%.6f')
        
        if mode & (self.MODE_XY | self.MODE_XYZ):
            self.add_parameter('alpha', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='degree',
                minval=-180.0, maxval=180.0,
                format='%.3f')
        
        if mode & (self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('phi', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='degree',
                minval=-180.0, maxval=180.0,
                format='%.3f')
            
        if mode & (self.MODE_RAW | self.MODE_X):
            self.add_parameter('setPointX', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
            
        if mode & (self.MODE_RAW | self.MODE_Y):
            self.add_parameter('setPointY', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
        
        if mode & (self.MODE_RAW | self.MODE_Z):
            self.add_parameter('setPointZ', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
        
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            self.add_parameter('rampRateX', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T/s',
                minval=0.0, maxval=self.FIELDRAMPLIMIT_X, format='%.5f')         
        
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('rampRateY', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T/s',
                minval=0.0, maxval=self.FIELDRAMPLIMIT_Y, format='%.5f')

        if mode & (self.MODE_RAW | self.MODE_Z | self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('rampRateZ', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T/s',
                minval=0.0, maxval=self.FIELDRAMPLIMIT_Z, format='%.5f')

        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            self.add_parameter('rampStateX', type=types.IntType,
                flags=Instrument.FLAG_GET,
                format_map={1:'Ramping', 2:'Holding', 3:'Paused', 4:'Manual up',
                5:'Manual down', 6:'Ramping to zero', 7:'Quench detected', 
                8:'At zero', 9:'Heating switch', 10:'Cooling switch'}) 
            
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('rampStateY', type=types.IntType,
                flags=Instrument.FLAG_GET,
                format_map={1:'Ramping', 2:'Holding', 3:'Paused', 4:'Manual up',
                5:'Manual down', 6:'Ramping to zero', 7:'Quench detected', 
                8:'At zero', 9:'Heating switch', 10:'Cooling switch'})

        if mode & (self.MODE_RAW | self.MODE_Z | self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('rampStateZ', type=types.IntType,
                flags=Instrument.FLAG_GET,
                format_map={1:'Ramping', 2:'Holding', 3:'Paused', 4:'Manual up',
                5:'Manual down', 6:'Ramping to zero', 7:'Quench detected', 
                8:'At zero', 9:'Heating switch', 10:'Cooling switch'})

        if self.PSWPRESENT_X & (mode & (self.MODE_RAW | self.MODE_X)):
            self.add_parameter('persistentX', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'driven mode',True:'persistent mode'})
        
        if self.PSWPRESENT_Y & (mode & (self.MODE_RAW | self.MODE_Y)):
            self.add_parameter('persistentY', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'driven mode',True:'persistent mode'})
            
        if self.PSWPRESENT_Z & (mode & (self.MODE_RAW | self.MODE_Z)):
            self.add_parameter('persistentZ', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'driven mode',True:'persistent mode'})
        
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            self.add_parameter('quenchX', type=types.BooleanType,
                flags=Instrument.FLAG_GET,
                format_map={False:'off',True:'on'})
        
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('quenchY', type=types.BooleanType,
                flags=Instrument.FLAG_GET,
                format_map={False:'off',True:'on'})
        
        if mode & (self.MODE_RAW | self.MODE_Z | self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('quenchZ', type=types.BooleanType,
                flags=Instrument.FLAG_GET,
                format_map={False:'off',True:'on'})

        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            self.add_parameter('errorX', type=types.StringType,
                               flags=Instrument.FLAG_GET)
        
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('errorY', type=types.StringType,
                               flags=Instrument.FLAG_GET)
            
        if mode & (self.MODE_RAW | self.MODE_Z | self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            self.add_parameter('errorZ', type=types.StringType,
                               flags=Instrument.FLAG_GET)
        
        if mode & self.MODE_XYZ:
            self.add_parameter('offsetEnabled', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'off',True:'on'}) 
    
    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)

    #mode of operation    
    
    def do_get_mode(self):
        return self._mode

    #if the new mode is the same as earlier, then nothing happens
    #otherwise we ramp the magnets to zero
    #and add & remove parameters as needed
    
    def do_set_mode(self, mode, init=False):
        if init or (self.get_mode() == mode):
            return True
        else:
            self._channelX.set_field(0.0)
            self._channelY.set_field(0.0)
            self._channelZ.set_field(0.0)
            if self.PSWPRESENT_X:
                self._channelX.set_pSwitch(False)
            if self.PSWPRESENT_Y:
                self._channelY.set_pSwitch(False)
            if self.PSWPRESENT_Z:
                self._channelZ.set_pSwitch(False)
            self._mode=mode
        for p in self.get_parameter_names():        #it is probably not safe to remove the parameter in set_parameter
            if p != 'mode':
                self.remove_parameter(p)
        self._create_parameters(mode)
        self.get_all()   
        return True

    #Actual parameters implemented
    #First, we define the wrapper functions to access the individual magnets
        
    def do_get_pSwitchX(self):
        if not self.PSWPRESENT_X:
            return False
        return self._channelX.get_pSwitch()
    
    def do_get_pSwitchY(self):
        if not self.PSWPRESENT_Y:
            return False
        return self._channelY.get_pSwitch()

    def do_get_pSwitchZ(self):
        if not self.PSWPRESENT_Z:
            return False
        return self._channelZ.get_pSwitch()
    
    def do_set_pSwitchX(self, value):
        if not self.PSWPRESENT_X:
            logging.error(__name__ +': No persistent switch present on X magnet')
            return False
        return self._channelX.set_pSwitch(value)
        
    def do_set_pSwitchY(self, value):
        if not self.PSWPRESENT_Y:
            logging.error(__name__ +': No persistent switch present on Y magnet')
            return False
        return self._channelY.set_pSwitch(value)

    def do_set_pSwitchZ(self, value):
        if not self.PSWPRESENT_Z:
            logging.error(__name__ +': No persistent switch present on Z magnet')
            return False
        return self._channelZ.set_pSwitch(value)
    
    def do_get_rampStateX(self):
        return self._channelX.get_rampState()
    
    def do_get_rampStateY(self):
        return self._channelY.get_rampState()

    def do_get_rampStateZ(self):
        return self._channelZ.get_rampState()
    
    def do_get_fieldX(self):
        return self._channelX.get_field()
    
    def do_set_fieldX(self, value):
        return self._channelX.set_field(value)
    
    def do_get_fieldY(self):
        return self._channelY.get_field()
    
    def do_set_fieldY(self, value):
        return self._channelY.set_field(value)

    def do_get_fieldZ(self):
        return self._channelZ.get_field()
    
    def do_set_fieldZ(self, value):
        return self._channelZ.set_field(value)
        
    def do_get_setPointX(self):
        return self._channelX.get_setPoint()
    
    def do_get_setPointY(self):
        return self._channelY.get_setPoint()

    def do_get_setPointZ(self):
        return self._channelZ.get_setPoint()

    def do_get_rampRateX(self):
        return self._channelX.get_rampRate()
    
    def do_set_rampRateX(self, value):
        return self._channelX.set_rampRate(value)
    
    def do_get_rampRateY(self):
        return self._channelY.get_rampRate()
    
    def do_set_rampRateY(self, value):
        return self._channelY.set_rampRate(value)

    def do_get_rampRateZ(self):
        return self._channelZ.get_rampRate()
    
    def do_set_rampRateZ(self, value):
        return self._channelZ.set_rampRate(value)
    
    def do_get_persistentX(self):
        if not self.PSWPRESENT_X:
            return False
        return self._channelX.get_persistent()
    
    def do_set_persistentX(self, value):
        if not self.PSWPRESENT_X:
            logging.error(__name__ + ': No persistent switch present, cannot alter persistent mode of X magnet')
            return False
        return self._channelX.set_persistent(value)

    def do_get_persistentY(self):
        if not self.PSWPRESENT_Y:
            return False
        return self._channelY.get_persistent()
    
    def do_set_persistentY(self, value):
        if not self.PSWPRESENT_Y:
            logging.error(__name__ + ': No persistent switch present, cannot alter persistent mode of Y magnet')
            return False
        return self._channelY.set_persistent(value)

    def do_get_persistentZ(self):
        if not self.PSWPRESENT_Z:
            return False
        return self._channelZ.get_persistent()
    
    def do_set_persistentZ(self, value):
        if not self.PSWPRESENT_Z:
            logging.error(__name__ + ': No persistent switch present, cannot alter persistent mode of Z magnet')
            return False
        return self._channelZ.set_persistent(value)
    
    def do_get_quenchX(self):
        return self._channelX.get_quench()
    
    def do_get_quenchY(self):
        return self._channelY.get_quench()

    def do_get_quenchZ(self):
        return self._channelZ.get_quench()

    def do_get_errorX(self):
        return self._channelX.get_error()
    
    def do_get_errorY(self):
        return self._channelY.get_error()

    def do_get_errorZ(self):
        return self._channelZ.get_error()
    
    def rampToX(self, value):
        if self.get_mode() & (self.MODE_RAW |self.MODE_X):
            return self._channelX.rampTo(value)
        else:
            return False
    
    def rampToY(self, value):
        if self.get_mode() & (self.MODE_RAW |self.MODE_Y):
            return self._channelY.rampTo(value)
        else:
            return False

    def rampToZ(self, value):
        if self.get_mode() & (self.MODE_RAW |self.MODE_Z):
            return self._channelZ.rampTo(value)
        else:
            return False
    
    def resetQuenchX(self):
        if self.get_mode() & (self.MODE_RAW | self.MODE_X | self.MODE_XY | self.MODE_XZ | self.MODE_XYZ):
            return self._channelX.resetQuench()
        else:
            return False    

    def resetQuenchY(self):
        if self.get_mode() & (self.MODE_RAW | self.MODE_Y | self.MODE_XY | self.MODE_YZ | self.MODE_XYZ):
            return self._channelY.resetQuench()
        else:
            return False    
   
    def resetQuenchZ(self):
        if self.get_mode() & (self.MODE_RAW | self.MODE_Z | self.MODE_XZ | self.MODE_YZ | self.MODE_XYZ):
            return self._channelY.resetQuench()
        else:
            return False
    
    def do_get_field(self):
        if self.get_mode() == self.MODE_XY:
            return math.hypot(self.get_fieldX(), self.get_fieldY())
        elif self.get_mode() == self.MODE_XZ:
            return math.hypot(self.get_fieldX(), self.get_fieldZ())
        elif self.get_mode() == self.MODE_YZ:
            return math.hypot(self.get_fieldY(), self.get_fieldZ())
        elif self.get_mode() == self.MODE_XYZ:
            if self._offseten:
                return self._field
            else:
                self._field=math.hypot(math.hypot(self.get_fieldX(), self.get_fieldY()),self.get_fieldZ())
                return self._field
        else:
            return False
    
    def do_set_field(self, value):
        if self.get_mode() == self.MODE_XY:
            a=math.radians(self.get_alpha())
            return self._channelX.set_field(value*math.cos(a)) and self._channelY.set_field(value*math.sin(a))
        elif self.get_mode() == self.MODE_XZ:
            f=math.radians(self.get_phi())
            return self._channelX.set_field(value*math.sin(f)) and self._channelZ.set_field(value*math.cos(f))
        elif self.get_mode() == self.MODE_YZ:
            f=math.radians(self.get_phi())
            return self._channelY.set_field(value*math.sin(f)) and self._channelZ.set_field(value*math.cos(f))
        elif self.get_mode() == self.MODE_XYZ:
            if self._offseten:
                a=math.radians(self._alpha)
                ao=math.radians(self._alphaoffset)
                f=math.radians(self._phi)
                fo=math.radians(self._phioffset)
                Bxtot=self._fieldoffset*math.cos(ao)*math.sin(fo)+value*math.cos(a)*math.sin(f)
                Bytot=self._fieldoffset*math.sin(ao)*math.sin(fo)+value*math.sin(a)*math.sin(f)
                Bztot=self._fieldoffset*math.cos(fo)+value*math.cos(f)
                if self._field_limit(Bxtot, Bytot, Bztot):
                    if self._sweepFieldsXYZ(Bxtot, Bytot, Bztot):
                        self._field=value
                        self.get_totalField()
                        self.get_totalAlpha()
                        self.get_totalPhi()
                        return True
                    else:
                        logging.error(__name__ + ': Error while applying field in offset mode')
                        return False
                else: 
                    logging.error(__name__ + ': Field limit exceeded in offset mode')
                    return False    
            else:
                f=math.radians(self._phi)
                a=math.radians(self._alpha)
                Bx=value*math.sin(f)*math.cos(a)
                By=value*math.sin(f)*math.sin(a)
                Bz=value*math.cos(f)
                self._field=value
                return self._sweepFieldsXYZ(Bx, By, Bz)
        else: 
            return False
    
    # We do it in the safe way: always do the ramp down first,
    # and only ramp up the other axis afterwards
    # this results in some performance penalty compared to
    # a straight simultaneous ramp to the new value 
    
    def do_get_alpha(self):
        return self._alpha
    
    def do_set_alpha(self, value):
        if self.get_mode() == self.MODE_XY:
            B=self.get_field()
            a=math.radians(value)
            oldX=self.get_fieldX()
            newX=B*math.cos(a)
            newY=B*math.sin(a)
            self._alpha=value       
            if math.fabs(newX) < math.fabs(oldX):
                return self._channelX.set_field(newX) and self._channelY.set_field(newY)
            else:
                return self._channelY.set_field(newY) and self._channelX.set_field(newX)
        elif self.get_mode() == self.MODE_XYZ:
            if self._offseten:
                a=math.radians(value)
                ao=math.radians(self._alphaoffset)
                f=math.radians(self._phi)
                fo=math.radians(self._phioffset)
                Bxtot=self._fieldoffset*math.cos(ao)*math.sin(fo)+self._field*math.cos(a)*math.sin(f)
                Bytot=self._fieldoffset*math.sin(ao)*math.sin(fo)+self._field*math.sin(a)*math.sin(f)
                Bztot=self._fieldoffset*math.cos(fo)+self._field*math.cos(f)
                if self._field_limit(Bxtot, Bytot, Bztot):
                    if self._sweepFieldsXY(Bxtot, Bytot):
                        self._alpha=value
                        self.get_totalField()
                        self.get_totalAlpha()
                        self.get_totalPhi()
                        return True
                    else:
                        logging.error(__name__ + ': Error while applying alpha in offset mode')
                        return False
                else: 
                    logging.error(__name__ + ': Field limit exceeded in offset mode')
                    return False             
            else:
                B=self.get_field()
                a=math.radians(value)
                f=math.radians(self._phi)
                newX=B*math.cos(a)*sin(f)
                newY=B*math.sin(a)*sin(f)
                if self._sweepFieldsXY(newX, newY):
                    self._alpha=value
                    return True
                else:
                    logging.error(__name__ + ': Error while applying alpha')
                    return False   
        else:
            return False
        
    def do_get_phi(self):
        return self._phi
    
    def do_set_phi(self, value):
        if self.get_mode() == self.MODE_XZ:
            B=self.get_field()
            f=math.radians(value)
            oldX=self.get_fieldX()
            newX=B*math.sin(f)
            newZ=B*math.cos(f)
            self._phi=value
            if math.fabs(newX) < math.fabs(oldX):
                return self._channelX.set_field(newX) and self._channelZ.set_field(newZ)
            else:
                return self._channelZ.set_field(newZ) and self._channelX.set_field(newX) 
        elif self.get_mode() == self.MODE_YZ:
            B=self.get_field()
            f=math.radians(value)
            oldY=self.get_fieldY()
            newY=B*math.sin(f)
            newZ=B*math.cos(f)
            self._phi=value
            if math.fabs(newY) < math.fabs(oldY):
                return self._channelY.set_field(newY) and self._channelZ.set_field(newZ)
            else:
                return self._channelZ.set_field(newZ) and self._channelY.set_field(newY) 
        elif self.get_mode() == self.MODE_XYZ:
            if self._offseten:
                a=math.radians(self._alpha)
                ao=math.radians(self._alphaoffset)
                f=math.radians(value)
                fo=math.radians(self._phioffset)
                Bxtot=self._fieldoffset*math.cos(ao)*math.sin(fo)+self._field*math.cos(a)*math.sin(f)
                Bytot=self._fieldoffset*math.sin(ao)*math.sin(fo)+self._field*math.sin(a)*math.sin(f)
                Bztot=self._fieldoffset*math.cos(fo)+self._field*math.cos(f)
                if self._field_limit(Bxtot, Bytot, Bztot):
                    if self._sweepFieldsXYZ(Bxtot, Bytot, Bztot):
                        self._phi=value
                        self.get_totalField()
                        self.get_totalAlpha()
                        self.get_totalPhi()
                        return True
                    else:
                        logging.error(__name__ + ': Error while applying phi in offset mode')
                        return False
                else: 
                    logging.error(__name__ + ': Field limit exceeded in offset mode')
                    return False       
            else:
                B=self.get_field()
                a=math.radians(self._alpha)
                f=math.radians(value)
                newZ=B*math.cos(f)
                newX=B*math.cos(a)*math.sin(f)
                newY=B*math.sin(a)*math.sin(f)
                if self._sweepFieldsXYZ(newX, newY, newZ):
                    self._phi=value
                    return True
                else:
                    logging.error(__name__ + ': Error while applying phi')
                    return False
        else:
            return False
        
    def do_get_offsetEnabled(self):
        return self._offseten
    
    def do_set_offsetEnabled(self, value):
        if value:
            if self.get_offsetEnabled():
                return True
            else:
                self._fieldoffset=0.0
                self._alphaoffset=0.0
                self._phioffset=0.0
                self._offseten=True
                self.add_parameter('offsetField', type=types.FloatType,
                                   flags=Instrument.FLAG_GETSET,
                                   units='T',
                                   format='%.6f')
                self.add_parameter('offsetAlpha', type=types.FloatType,
                                   flags=Instrument.FLAG_GETSET,
                                   units='degree',
                                   minval=-180.0, maxval=180.0,
                                   format='%.3f')
                self.add_parameter('offsetPhi', type=types.FloatType,
                                   flags=Instrument.FLAG_GETSET,
                                   units='degree',
                                   minval=-180.0, maxval=180.0,
                                   format='%.3f')
                self.add_parameter('totalField', type=types.FloatType,
                                   flags=Instrument.FLAG_GET,
                                   units='T',
                                   format='%.6f')
                self.add_parameter('totalAlpha', type=types.FloatType,
                                   flags=Instrument.FLAG_GET,
                                   units='degree',
                                   format='%.3f')
                self.add_parameter('totalPhi', type=types.FloatType,
                                   flags=Instrument.FLAG_GET,
                                   units='degree',
                                   format='%.3f')
                self.get_totalField()
                self.get_totalAlpha()
                self.get_totalPhi()
                self.get_offsetField()
                self.get_offsetAlpha()
                self.get_offsetPhi()
                return True
        else:
            if self.get_offsetEnabled():
                self._offseten=False
                self._fieldoffset=0.0
                self._alphaoffset=0.0
                self._phioffset=0.0
                self.set_field(self.get_totalField())
                self.set_alpha(self.get_totalAlpha())
                self.remove_parameter('offsetField')
                self.remove_parameter('offsetAlpha')
                self.remove_parameter('offsetPhi')
                self.remove_parameter('totalField')
                self.remove_parameter('totalAlpha')
                self.remove_parameter('totalPhi')
                return True
            else:
                return True
            
    def do_get_offsetField(self):
        return self._fieldoffset
    
    def do_set_offsetField(self, value):
        a=math.radians(self._alpha)
        ao=math.radians(self._alphaoffset)
        f=math.radians(self._phi)
        fo=math.radians(self._phioffset)
        Bxtot=value*math.cos(ao)*math.sin(fo)+self._field*math.cos(a)*math.sin(f)
        Bytot=value*math.sin(ao)*math.sin(fo)+self._field*math.sin(a)*math.sin(f)
        Bztot=value*math.cos(fo)+self._field*math.cos(f)
        if self._field_limit(Bxtot, Bytot, Bztot):
            if self._sweepFieldsXYZ(Bxtot, Bytot, Bztot):
                self._offsetfield=value
                self.get_totalField()
                self.get_totalAlpha()
                self.get_totalPhi()
                return True
            else:
                logging.error(__name__ + ': Error while applying offset field')
                return False
        else: 
            logging.error(__name__ + ': Field limit exceeded in offset mode')
            return False    
    
    def do_set_offsetAlpha(self, value):
        a=math.radians(self._alpha)
        ao=math.radians(value)
        f=math.radians(self._phi)
        fo=math.radians(self._phioffset)
        Bxtot=self._fieldoffset*math.cos(ao)*math.sin(fo)+self._field*math.cos(a)*math.sin(f)
        Bytot=self._fieldoffset*math.sin(ao)*math.sin(fo)+self._field*math.sin(a)*math.sin(f)
        Bztot=self._fieldoffset*math.cos(fo)+self._field*math.cos(f)
        if self._field_limit(Bxtot, Bytot, Bztot):
            if self._sweepFieldsXY(Bxtot, Bytot):
                self._alphaoffset=value
                self.get_totalField()
                self.get_totalAlpha()
                self.get_totalPhi()
                return True
            else:
                logging.error(__name__ + ': Error while applying offset alpha')
                return False
        else: 
            logging.error(__name__ + ': Field limit exceeded in offset mode')
            return False     

    def do_set_offsetPhi(self, value):
        a=math.radians(self._alpha)
        ao=math.radians(self._alphaoffset)
        f=math.radians(self._phi)
        fo=math.radians(value)
        Bxtot=self._fieldoffset*math.cos(ao)*math.sin(fo)+self._field*math.cos(a)*math.sin(f)
        Bytot=self._fieldoffset*math.sin(ao)*math.sin(fo)+self._field*math.sin(a)*math.sin(f)
        Bztot=self._fieldoffset*math.cos(fo)+self._field*math.cos(f)
        if self._field_limit(Bxtot, Bytot, Bztot):
            if self._sweepFieldsXYZ(Bxtot, Bytot, Bztot):
                self._phioffset=value
                self.get_totalField()
                self.get_totalAlpha()
                self.get_totalPhi()
                return True
            else:
                logging.error(__name__ + ': Error while applying offset phi')
                return False
        else: 
            logging.error(__name__ + ': Field limit exceeded in offset mode')
            return False           
    
    # Note: totalField is readonly in offset mode
    # and always returns the value read from the instrument
    
    def do_get_totalField(self):
        return math.hypot(math.hypot(self.get_fieldX(), self.get_fieldY()),self.get_fieldZ())
    
    # This is a tricky one
    # if it gives problems, I will just put it in try catch
    
    def do_get_totalAlpha(self):
        Bxtot=self.get_fieldX()
        Bytot=self.get_fieldY()
        Bztot=self.get_fieldZ()
        if Bztot != 0.0:
            if Bxtot != 0.0:
                return math.degrees(math.atan2(Bytot,Bxtot))
            else:
                if Bytot < 0.0:
                    return 270.0
                else:
                    return 90.0
        else:
            return 0.0
    
    # Same applies to this one
    
    def do_get_totalPhi(self):
        Bxtot=self.get_fieldX()
        Bytot=self.get_fieldY()
        Bztot=self.get_fieldZ()
        if Bztot != 0.0:
            return math.degrees(math.atan2(math.hypot(Bxtot, Bytot),Bztot))
        else:
            return 90.0    
    
    # checking if field is safe to apply
    # this is required only for offset XYZ fields
    # for now we only check field amplitude
    
    def _field_limit(self, Bx, By, Bz):
        if math.hypot(math.hypot(Bx, By),Bz) < self.FIELDRATING_XYZ:
            return True
        else:
            return False
    
    # these functions ensure that we always stay within the limit of the vectorfield
            
    def _sweep_X_then_Y(self, Bx, By):
        return self._channelX.set_field(Bx) and self._channelY.set_field(By)
    
    def _sweep_Y_then_X(self, Bx, By):
        return self._channelY.set_field(By) and self._channelX.set_field(Bx)

    def _sweep_XY_then_Z(self, Bx, By, Bz):
        return self._channelX.set_field(Bx) and self._channelY.set_field(By) and self._channelY.set_field(Bz)
    
    def _sweep_Z_then_XY(self, Bx, By, Bz):
        return self._channelX.set_field(Bz) and self._channelY.set_field(Bx) and self._channelY.set_field(By)    
    
    def _sweepFieldsXY(self, Bx, By):
        oldXfield=self.get_fieldX()
        oldYfield=self.get_fieldY()    #this is just to update By value
        if math.fabs(Bx) < math.fabs(oldXfield):
            return self._sweep_X_then_Y(Bx, By)
        else:
            return self._sweep_Y_then_X(Bx, By)

    def _sweepFieldsXYZ(self, Bx, By, Bz):
        oldXfield=self.get_fieldX()    #this is just to update Bx value
        oldYfield=self.get_fieldY()    #this is just to update By value
        oldZfield=self.get_fieldZ()    
        if math.fabs(Bz) < math.fabs(oldZfield):
            return self._sweep_Z_then_XY(Bx, By, Bz)
        else:
            return self._sweep_XY_then_Z(Bx, By, Bz)


          