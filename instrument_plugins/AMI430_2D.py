# QTlab driver for American Magnetics 430 magnet power supply.
# This version controls 2 solenoids and uses two instances of AMI430_single for that.
# For a single solenoid, use AMI430_single.
# For 3D vector operation, use AMI430_3D.
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


from instrument import Instrument
import instruments
import qt
import types
import socket
import logging
import time
from math import *
from numpy import *

class AMI430_2D(Instrument):
    
    #Global parameters
    #Important:
    #Set these values in accordance with the limits of each system
    #otherwise magnet quench or damage of equipment might occur
    
    #ratio between current and magnetic field
    COILCONSTANT_X = 0.0146       #T/A
    COILCONSTANT_Y = 0.0426       #T/A
    
    #Rated operating current in A, from spec sheet. A margin of 0.03A is added so that the rated fields fit in.
    #If the magnet quenches regularly, reduce these values!!!!
    CURRENTRATING_X = 68.53      #A
    CURRENTRATING_Y = 70.45      #A
    
    #Rated magnetic field based on the two previous values
    #Note: in many cases, the vector operation is only allowed in a smaller range
    #Set the last value accordingly 
    FIELDRATING_X = COILCONSTANT_X*CURRENTRATING_X    #T
    FIELDRATING_Y = COILCONSTANT_Y*CURRENTRATING_Y    #T
    FIELDRATING_XY = 1.0                                        #T
    
    #Maximum ramp limits from datasheet
    CURRENTRAMPLIMIT_X = 0.2     #A/s
    CURRENTRAMPLIMIT_Y = 0.05     #A/s
    FIELDRAMPLIMIT_X=COILCONSTANT_X*CURRENTRAMPLIMIT_X    #T/s
    FIELDRAMPLIMIT_Y=COILCONSTANT_Y*CURRENTRAMPLIMIT_Y    #T/s
    
    #Persistent switch rated currents. 
    #These values are based on the autodetect function of the supply unit
    #typical values are ~50mA for wet systems and ~30mA for dry systems
    PSCURRENT_X=50            #mA
    PSCURRENT_Y=50            #mA
    #Heat and cooldown time for persistent switch
    PSHEATTIME_X=20       #s
    PSHEATTIME_Y=20       #s
    PSCOOLTIME_X=20       #s
    PSCOOLTIME_Y=20       #s
    
    #soft parameters
    _mode=0x01
    _alpha=0.0
    _field=0.0
    
    #soft parameters related to field offset
    _offseten=False
    _fieldoffset=0.0
    _alphaoffset=0.0
    
    #global parameter for the presence of persistent switch. Default is True.
    #Check your magnet configuration!
    PSWPRESENT_X=True
    PSWPRESENT_Y=True
            
    #operation mode
    '''
    Available modes:
    
    MODE_RAW: individual magnets can be accessed directly. 
    
    MODE_X: only X magnet is driven, Y magnet is at zero.
    
    MODE_Y: only Y magnet is driven, X magnet is at zero.
    
    MODE_XY: 2D vector operation, field amplitude and direction can be set.
    
    '''
    MODE_RAW=0x01
    MODE_X=0x02
    MODE_Y=0x04
    MODE_XY=0x08 
    
    ###Init
    ###Parameters for each axis:
    #address: IP address of magnet controller. Has to be set on front panel. 
    #port: TCP port of magnet controller. Should be 7180
    #switchPresent: determines if driver handles persistent switch or not. Check
    #                your magnet configuration! Default is yes. Has to be forwarded to
    #                global parameter PSWPRESENT
    
    def __init__(self, name, addressX='192.168.2.3', addressY='192.168.2.2', portX=7180, portY=7180, mode=MODE_RAW, switchPresent_X=True, switchPresent_Y=True):
        
        Instrument.__init__(self, name, tags=['measure'])
        
        #pass switchPresent_{X,Y} to their global parameter
        self.PSWPRESENT_X=switchPresent_X
        self.PSWPRESENT_Y=switchPresent_Y
        
        self._create_parameters(mode)
        
        self.set_mode(mode, init=True)
        
        #We create the underlying instances of AMI430_single
        
        self._channelX=qt.instruments.create(__name__ + 'X', 'AMI430_single', address=addressX, port=portX, switchPresent=switchPresent_X)
        self._channelY=qt.instruments.create(__name__ + 'Y', 'AMI430_single', address=addressY, port=portY, switchPresent=switchPresent_Y)
        
        #and override the limits for each channel
        self._channelX.set_parameter_bounds('field', -self.FIELDRATING_X, self.FIELDRATING_X)
        self._channelX.set_parameter_bounds('rampRate', 0.0, self.FIELDRAMPLIMIT_X)
        
        self._channelY.set_parameter_bounds('field', -self.FIELDRATING_Y, self.FIELDRATING_Y)
        self._channelY.set_parameter_bounds('rampRate', 0.0, self.FIELDRAMPLIMIT_Y)
        
        self.add_function('reset')
        
        self.get_all()

        if mode & (self.MODE_RAW | self.MODE_X):
            self.add_function('rampToX')
            
        if mode & (self.MODE_RAW | self.MODE_Y):
            self.add_function('rampToY')
            
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY):
            self.add_function('resetQuenchX')
            
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY):
            self.add_function('resetQuenchY')
    
    def reset(self):                                                          ###TODO
        pass
    
    def _create_parameters(self, mode):
        
        if 'mode' not in self.get_parameter_names():                #only create it once
            self.add_parameter('mode', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={self.MODE_RAW:'Raw mode',
                                       self.MODE_X:'X magnet',
                                       self.MODE_Y:'Y magnet',
                                       self.MODE_XY:'XY magnet'})
        
        if self.PSWPRESENT_X & (mode & (self.MODE_RAW | self.MODE_X)): 
            self.add_parameter('pSwitchX', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'off',True:'on'})
            
        if self.PSWPRESENT_Y & (mode & (self.MODE_RAW | self.MODE_Y)):
            self.add_parameter('pSwitchY', type=types.BooleanType,
                flags=Instrument.FLAG_GETSET,
                format_map={False:'off',True:'on'})    

        if mode & (self.MODE_RAW | self.MODE_X):
            self.add_parameter('fieldX', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=-self.FIELDRATING_X, maxval=self.FIELDRATING_X,
                format='%.6f')
        elif mode & self.MODE_XY:
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
        elif mode & self.MODE_XY:
            self.add_parameter('fieldY', type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='T',
                format='%.6f')
        
        if mode & self.MODE_XY:
            self.add_parameter('field', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T',
                minval=0.0, maxval=self.FIELDRATING_XY,
                format='%.6f')
        
        if mode & self.MODE_XY:
            self.add_parameter('alpha', type=types.FloatType,
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
        
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY):
            self.add_parameter('rampRateX', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T/s',
                minval=0.0, maxval=self.FIELDRAMPLIMIT_X, format='%.5f')         
        
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY):
            self.add_parameter('rampRateY', type=types.FloatType,
                flags=Instrument.FLAG_GETSET,
                units='T/s',
                minval=0.0, maxval=self.FIELDRAMPLIMIT_Y, format='%.5f')

        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY):
            self.add_parameter('rampStateX', type=types.IntType,
                flags=Instrument.FLAG_GET,
                format_map={1:'Ramping', 2:'Holding', 3:'Paused', 4:'Manual up',
                5:'Manual down', 6:'Ramping to zero', 7:'Quench detected', 
                8:'At zero', 9:'Heating switch', 10:'Cooling switch'}) 
            
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY):
            self.add_parameter('rampStateY', type=types.IntType,
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
        
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY):
            self.add_parameter('quenchX', type=types.BooleanType,
                flags=Instrument.FLAG_GET,
                format_map={False:'off',True:'on'})
        
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY):
            self.add_parameter('quenchY', type=types.BooleanType,
                flags=Instrument.FLAG_GET,
                format_map={False:'off',True:'on'})
            
        if mode & (self.MODE_RAW | self.MODE_X | self.MODE_XY):
            self.add_parameter('errorX', type=types.StringType,
                               flags=Instrument.FLAG_GET)
        
        if mode & (self.MODE_RAW | self.MODE_Y | self.MODE_XY):
            self.add_parameter('errorY', type=types.StringType,
                               flags=Instrument.FLAG_GET)
            
        if mode & self.MODE_XY:
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
            if self.PSWPRESENT_X:
                self._channelX.set_pSwitch(False)
            if self.PSWPRESENT_Y:
                self._channelY.set_pSwitch(False)
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
    
    def do_get_rampStateX(self):
        return self._channelX.get_rampState()
    
    def do_get_rampStateY(self):
        return self._channelY.get_rampState()
    
    def do_get_fieldX(self):
        return self._channelX.get_field()
    
    def do_set_fieldX(self, value):
        return self._channelX.set_field(value)
    
    def do_get_fieldY(self):
        return self._channelY.get_field()
    
    def do_set_fieldY(self, value):
        return self._channelY.set_field(value)
    
    def do_get_setPointX(self):
        return self._channelX.get_setPoint()
    
    def do_get_setPointY(self):
        return self._channelY.get_setPoint()

    def do_get_rampRateX(self):
        return self._channelX.get_rampRate()
    
    def do_set_rampRateX(self, value):
        return self._channelX.set_rampRate(value)
    
    def do_get_rampRateY(self):
        return self._channelY.get_rampRate()
    
    def do_set_rampRateY(self, value):
        return self._channelY.set_rampRate(value)
    
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
    
    def do_get_quenchX(self):
        return self._channelX.get_quench()
    
    def do_get_quenchY(self):
        return self._channelY.get_quench()
    
    def do_get_errorX(self):
        return self._channelX.get_error()
    
    def do_get_errorY(self):
        return self._channelY.get_error()
    
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
        
    def resetQuenchX(self):
        if self.get_mode() & (self.MODE_RAW | self.MODE_X | self.MODE_XY):
            return self._channelX.resetQuench()
        else:
            return False    

    def resetQuenchY(self):
        if self.get_mode() & (self.MODE_RAW | self.MODE_Y | self.MODE_XY):
            return self._channelY.resetQuench()
        else:
            return False    
    
    def do_get_field(self):
        if self._offseten:
            return self._field
        else:
            self._field=math.hypot(self.get_fieldX(), self.get_fieldY())
            return self._field 
    
    def do_set_field(self, value):
        a=math.radians(self._alpha)
        if self._offseten:
            ao=math.radians(self._alphaoffset)
            Bxtot=self._fieldoffset*math.cos(ao)+value*math.cos(a)
            Bytot=self._fieldoffset*math.sin(ao)+value*math.sin(a)
            if self._field_limit(Bxtot, Bytot):
                if self._sweepFields(Bxtot, Bytot):
                    self.get_totalField()
                    self.get_totalAlpha()
                    self._field=value
                    return True
                else:
                    logging.error(__name__ + ': Error while applying offset field')
                    return False                    
            else: 
                logging.error(__name__ + ': Field limit exceeded in offset mode')
                return False
        else:
            self._field=value
            return self._sweepFields(value*math.cos(a), value*math.sin(a))
    
    # Alpha is referenced to the X axis    
    # We always ramp within the safe region: always do the ramp down first,
    # and only ramp up the other axis afterwards
    # this results in some performance penalty compared to
    # a straight simultaneous ramp to the new value 
    
    def do_get_alpha(self):
        return self._alpha
    
    def do_set_alpha(self, value):
        if self._offseten:
            a=math.radians(value)
            ao=math.radians(self._alphaoffset)
            Bxtot=self._fieldoffset*math.cos(ao)+self._field*math.cos(a)
            Bytot=self._fieldoffset*math.sin(ao)+self._field*math.sin(a)
            if self._field_limit(Bxtot, Bytot):
                if self._sweepFields(Bxtot, Bytot):
                    self._alpha=value
                    self.get_totalField()
                    self.get_totalAlpha()
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
            newX=B*math.cos(a)
            newY=B*math.sin(a)
            if self._sweepFields(newX, newY):
                self._alpha=value
                return True
            else:
                logging.error(__name__ + ': Error while applying alpha')
                return False     
    
    # Offset field operations
    # If offset is enabled, an offset field of magnitude offsetField and direction offsetAlpha
    # is added to the vector field.
    # Note: magnet limit has to be checked individually if either field, alpha, offsetField or offsetAlpha
    # are changed
    
    def do_get_offsetEnabled(self):
        return self._offseten
    
    def do_set_offsetEnabled(self, value):
        if value:
            if self.get_offsetEnabled():
                return True
            else:
                self._fieldoffset=0.0
                self._alphaoffset=0.0
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
                self.add_parameter('totalField', type=types.FloatType,
                                   flags=Instrument.FLAG_GET,
                                   units='T',
                                   format='%.6f')
                self.add_parameter('totalAlpha', type=types.FloatType,
                                   flags=Instrument.FLAG_GET,
                                   units='degree',
                                   format='%.3f')
                self.get_totalField()
                self.get_totalAlpha()
                self.get_offsetField()
                self.get_offsetAlpha()
                return True
        else:
            if self.get_offsetEnabled():
                self._offseten=False
                self._fieldoffset=0.0
                self._alphaoffset=0.0
                self.set_field(self.get_totalField())
                self.set_alpha(self.get_totalAlpha())
                self.remove_parameter('offsetField')
                self.remove_parameter('offsetAlpha')
                self.remove_parameter('totalField')
                self.remove_parameter('totalAlpha')
                return True
            else:
                return True
            
    
    def do_get_offsetField(self):
        return self._fieldoffset
    
    def do_set_offsetField(self, value):
        a=math.radians(self._alpha)
        ao=math.radians(self._alphaoffset)
        Bxtot=value*math.cos(ao)+self._field*math.cos(a)
        Bytot=value*math.sin(ao)+self._field*math.sin(a)
        if self._field_limit(Bxtot, Bytot):
            if self._sweepFields(Bxtot, Bytot):
                self.get_totalField()
                self.get_totalAlpha()
                self._fieldoffset=value
                return True
            else:
                logging.error(__name__ + ': Error while applying offset field')
                return False                    
        else: 
            logging.error(__name__ + ': Field limit exceeded in offset mode')
            return False
    
    def do_get_offsetAlpha(self):
        return self._alphaoffset
    
    def do_set_offsetAlpha(self, value):
        ao=math.radians(value)
        a=math.radians(self._alpha)
        Bxtot=self._fieldoffset*math.cos(ao)+self._field*math.cos(a)
        Bytot=self._fieldoffset*math.sin(ao)+self._field*math.sin(a)
        if self._field_limit(Bxtot, Bytot):
            if self._sweepFields(Bxtot, Bytot):
                self.get_totalField()
                self.get_totalAlpha()
                self._alphaoffset=value
                return True
            else:
                logging.error(__name__ + ': Error while applying offset alpha')
                return False
        else: 
            logging.error(__name__ + ': Field limit exceeded in offset mode')
            return False    
    
    # Note: totalField is readonly in offset mode
    # and always returns the value read from the instrument
    
    def do_get_totalField(self):
        return math.hypot(self.get_fieldX(), self.get_fieldY())
    
    # This is a tricky one
    # if it gives problems, I will just put it in try catch
    
    def do_get_totalAlpha(self):
        Bxtot=self.get_fieldX()
        Bytot=self.get_fieldY()
        if Bxtot != 0.0:
            if Bytot > 0.0:
                return math.degrees(math.atan(Bytot/Bxtot))
            else:
                return 360.0-math.degrees(math.atan(Bytot/Bxtot))
        else:
            if Bytot >= 0.0:
                return 90.0
            else:
                return 270.0
    
    # checking if field is safe to apply
    # this is required only for offset XY fields
    # for now we only check field amplitude
    
    def _field_limit(self, Bx, By):
        if math.hypot(Bx, By) < self.FIELDRATING_XY:
            return True
        else:
            return False
    
    # these functions ensure that we always stay within the limit of the vectorfield
        
    def _sweep_X_then_Y(self, Bx, By):
        return self._channelX.set_field(Bx) and self._channelY.set_field(By)
    
    def _sweep_Y_then_X(self, Bx, By):
        return self._channelY.set_field(By) and self._channelX.set_field(Bx)
    
    def _sweepFields(self, Bx, By):
        oldXfield=self.get_fieldX()
        oldYfield=self.get_fieldY()    #this is just to update By value
        if math.fabs(Bx) < math.fabs(oldXfield):
            return self._sweep_X_then_Y(Bx, By)
        else:
            return self._sweep_Y_then_X(Bx, By)
           