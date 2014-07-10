# rigol_dg_counter.py driver for Rigol DG series waveform generators.
# This driver defines the functions to handle the waveform generator modul of the instrument.
# 
# Attila Geresdi (attila.geresdi@gmail.com) 2014
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
#


from instrument import Instrument
import visa
import types
import logging
import string

import qt

class rigol_dg_wavegen(Instrument):
    '''
    This is the driver for the waveform generator modul of the Rigol DG series waveform generators
    Usually this modul is invoked by the rigol_dg* driver. 
    For list of supported devices, refer to those drivers.
    '''
    
    def __init__(self, name, type, phy, channel):
        
        logging.info("Initializing the wavegen modul of Rigol")
        Instrument.__init__(self, name, tags=['virtual'])
    
        #Pass init parameters to global constants

        self._type=type
        self._phy=phy
        self._ch=str(channel)

        #Set type-dependent parameters
        if self._type=="DG4062":
            maxfreq=6e7
        elif self._type=="DG4102":
            maxfreq=1e8
        elif self._type=="DG4162":
            maxfreq=1.6e8
        else:
            logging.error("Rigol_dg_wavegen: Invalid instrument type received")
            return False

        self.add_parameter('enabled', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'disabled',True:'enabled'})
        
        self.add_parameter('polarity', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'inverted',True:'normal'})
        
        self.add_parameter('load_impedance', type=types.StringType,
                           flags=Instrument.FLAG_GETSET)

        self.add_parameter('sync_out', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'disabled',True:'enabled'})

        self.add_parameter('sync_polarity', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'inverted',True:'normal'})

        self.add_parameter('add_noise_enabled', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'disabled',True:'enabled'})
        
        self.add_parameter('add_noise_level', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='%',
                           minval=0.0, maxval=50.0)
        
        self.add_parameter('waveform', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'Sine',
                                       1:'Square',
                                       2:'Ramp',
                                       3:'Pulse',
                                       4:'Noise',
                                       5:'Harmonic',
                                       6:'Custom',
                                       7:'DC' })
        
        self.add_parameter('ramp_symmetry', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='%',
                           minval=0.0, maxval=100.0)
        
        self.add_parameter('square_duty_cycle', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
                           units='%',
                           minval=20.0, maxval=80.0)        

        self.add_parameter('marker_enabled', type=types.BooleanType,
                            flags=Instrument.FLAG_GETSET,
                            format_map={False:'disabled', True:'enabled'})        
        
        #Max. frequency depends on the type of the instrument
        self.add_parameter('frequency', type=types.FloatType,
                            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
                            units='Hz',
                            minval=1e-6, maxval=maxfreq)

        self.add_parameter('frequency_sweep_start', type=types.FloatType,
                            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
                            units='Hz',
                            minval=1e-6, maxval=maxfreq)        

        self.add_parameter('frequency_sweep_stop', type=types.FloatType,
                            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
                            units='Hz',
                            minval=1e-6, maxval=maxfreq)    
        
        self.add_parameter('marker_frequency', type=types.FloatType,
                            flags=Instrument.FLAG_GETSET | Instrument.FLAG_GET_AFTER_SET,
                            units='Hz',
                            minval=1e-6, maxval=maxfreq)        
                
        self.add_parameter('amplitude', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='Vpp',
                           minval=1e-3, maxval=10.0)
              
        self.add_parameter('offset', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='V',
                           minval=-5.0, maxval=5.0)
        
        self.add_parameter('phase', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='deg',
                           minval=0.0, maxval=360.0)
        
        self.add_parameter('pulse_delay', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0, maxval=1e6)
        
        self.add_parameter('pulse_width', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=4e-9)
        
        self.add_parameter('pulse_duty_cycle', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='%',
                           minval=0.0, maxval=100.0, format='%.2f')
        
        self.add_parameter('pulse_leading_edge', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0)

        self.add_parameter('pulse_trailing_edge', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0)
        
        self.add_parameter('pulse_hold_parameter', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={True:'Width', False:'Duty'})
        
        self.add_parameter('harmonic_order', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           minval=2, maxval=16)
        
        self.add_parameter('harmonic_amplitudes', type=types.TupleType,
                           flags=Instrument.FLAG_GETSET,
                           units='V',
                           minval=0.0, maxval=10.0, format='%.4f')

        self.add_parameter('harmonic_phases', type=types.TupleType,
                           flags=Instrument.FLAG_GETSET,
                           units='deg',
                           minval=0.0, maxval=360.0, format='%.2f')
    
        self.add_parameter('harmonic_type', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'Even',
                                       1:'Odd',
                                       2:'All',
                                       3:'User'})
                
        self.add_parameter('delay', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0, maxval=85.0)
        
        self.add_parameter('mode', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'normal',1:'burst', 2:'sweep', 3:'mod'})
        
        self.add_parameter('burst_mode', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'triggered', 1:'gated', 2:'infinity'})
        
        self.add_parameter('burst_cycles', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           minval=1, maxval=1000000)
        
        self.add_parameter('burst_period', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=1e-6)
    
        self.add_parameter('burst_phase', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='deg',
                           minval=0.0, maxval=360.0, format='%.2f') 
        
        self.add_parameter('sweep_holdtime_start', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0, maxval=300.0, format='%.2f')

        self.add_parameter('sweep_holdtime_stop', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0, maxval=300.0, format='%.2f')

        self.add_parameter('sweep_returntime', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=0.0, maxval=300.0, format='%.2f')

        self.add_parameter('sweep_time', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='s',
                           minval=1.0e-2, maxval=300.0, format='%.2f')

        self.add_parameter('sweep_spacing', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'linear',
                                       1:'log',
                                       2:'step'})   
        
        self.add_parameter('sweep_steps', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           minval=2, maxval=2048)     

        self.add_parameter('trigger_source', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'internal', 1: 'external', 2: 'manual'})
        
        self.add_parameter('trigger_edge', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'falling edge', True:'rising edge'})
        
        self.add_parameter('gate_polarity', type=types.BooleanType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={False:'inverted', True:'normal'})
        
        self.add_parameter('trigger_out', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           format_map={0:'disabled', 1:'positive', 2:'negative'})
        
        self.get_all()
         
#Common functions

    def get_all(self):
        for p in self.get_parameter_names():
            self.get(p)
    
#Device specific functions
        
    #OUTP
    #queries, enables or disables the output
    def do_get_enabled(self):
        return self._phy.ask(":OUTP"+self._ch+"?\n").strip() == "ON"
    
    def do_set_enabled(self, value):
        if value:
            self._phy.write(":OUTP"+self._ch+" ON\n")
        else:
            self._phy.write(":OUTP"+self._ch+" OFF\n")
    
    #OUTP:POL
    #queries or sets the polarity of the output (normal or inverted)
    def do_get_polarity(self):
        return self._phy.ask(":OUTP"+self._ch+":POL?\n").strip() == "NORMAL"
    
    def do_set_polarity(self, value):
        if value:
            self._phy.write(":OUTP"+self._ch+":POL NORM\n")
        else:
            self._phy.write(":OUTP"+self._ch+":POL INV\n")
    
    #OUTP:LOAD
    #queries or sets the load impedance on the output.
    #Note that it can be either 1 Ohm ... 10kOhm or infinity.
    #Hence StringType is used. Also range check has to be performed.
    def do_get_load_impedance(self):
        temp=self._phy.ask(":OUTP"+self._ch+":LOAD?\n").strip()
        if temp == "INFINITY":
            return "HighZ"
        else:
            return temp + " Ohm"
    
    def do_set_load_impedance(self, value):
        if string.lower(value) == "highz":
            self._phy.write(":OUTP"+self._ch+":LOAD INF\n")
        else:
            res=float(value)
            if res >= 1.0 and res <=10000.0:
                self._phy.write(":OUTP"+self._ch+":LOAD "+str(res)+"\n")
            else:
                return False
    
    #OUTP:SYNC
    #queries or enables/disables the sync output.
    def do_get_sync_out(self):
        return self._phy.ask(":OUTP"+self._ch+":SYNC?\n").strip() == "ON"
    
    def do_set_sync_out(self, value):
        if value:
            self._phy.write(":OUTP"+self._ch+":SYNC ON\n")
        else:
            self._phy.write(":OUTP"+self._ch+":SYNC OFF\n")
    
    #OUTP:SYNC:POL
    #queries or sets the polarity of the sync output.
    def do_get_sync_polarity(self):
        return self._phy.ask(":OUTP"+self._ch+":SYNC:POL?\n").strip() == "POS"
    
    def do_set_sync_polarity(self, value):
        if value:
            self._phy.write(":OUTP"+self._ch+":SYNC:POL POS\n")
        else:
            self._phy.write(":OUTP"+self._ch+":SYNC:POL NEG\n")
            
    #OUTP:NOIS
    #queries or enables/disables added noise on the output
    def do_get_add_noise_enabled(self):
        return self._phy.ask(":OUTP"+self._ch+":NOIS?\n").strip() == "ON"
    
    def do_set_add_noise_enabled(self, value):
        if value:
            self._phy.write(":OUTP"+self._ch+":NOIS ON\n")
        else:
            self._phy.write(":OUTP"+self._ch+":NOIS OFF\n")
            
    #OUTP:NOIS:SCAL
    #queries or sets the noise level on output if enabled
    def do_get_add_noise_level(self):
        return float(self._phy.ask(":OUTP"+self._ch+":NOIS:SCAL?\n"))
    
    def do_set_add_noise_level(self, value):
        self._phy.write(":OUTP"+self._ch+":NOIS:SCAL"+str(value)+"\n")
        
    #SOUR:FUNC
    #queries or sets the output waveform
    def do_get_waveform(self):
        temp=self._phy.ask(":SOUR"+self._ch+":FUNC?\n").strip()
        if temp=="SIN":
            return 0
        elif temp=="SQU":
            return 1
        elif temp=="RAMP":
            return 2
        elif temp=="PULS":
            return 3
        elif temp=="NOIS":
            return 4
        elif temp=="USER":
            return 5
        elif temp=="HARM":
            return 6
        elif temp=="CUST":
            return 7
        elif temp=="DC":
            return 8
        else:
            return None
    
    def do_set_waveform(self,value):
        if value==0:
            val="SIN"
        elif value==1:
            val="SQU"
        elif value==2:
            val="RAMP"
        elif value==3:
            val="PULS"
        elif value==4:
            val="NOIS"
        elif value==5:
            val="USER"
        elif value==6:
            val="HARM"
        elif value==7:
            val="CUST"
        elif value==8:
            val="DC"
        else:
            return False
        self._phy.write(":SOUR"+self._ch+":FUNC "+val+"\n")
    
    #SOUR:FUNC:RAMP:SYMM
    #queries or sets the symmetry of the ramp waveform
    def do_get_ramp_symmetry(self):
        return float(self._phy.ask(":SOUR"+self._ch+":FUNC:RAMP:SYMM?\n"))
    
    def do_set_ramp_symmetry(self,value):
        self._phy.write(":SOUR"+self._ch+":FUNC:RAMP:SYMM "+str(value)+"\n")    

    #SOUR:FUNC:SQU:DCYC
    #queries or sets the duty cycle of the square waveform
    #Note that range depends on frequency (see manual)
    def do_get_square_duty_cycle(self):
        return float(self._phy.ask(":SOUR"+self._ch+":FUNC:SQU:DCYC?\n"))
    
    def do_set_square_duty_cycle(self,value):
        self._phy.write(":SOUR"+self._ch+":FUNC:SQU:DCYC "+str(value)+"\n")   
     
    #SOUR:MARK
    #queries or enables/disables marker for frequency sweeps
    def do_get_marker_enabled(self):
        return self._phy.ask(":SOUR"+self._ch+":MARK?\n").strip() == "ON"
    
    def do_set_marker_enabled(self, value):
        if value:
            self._phy.write(":SOUR"+self._ch+":MARK ON\n")
        else:
            self._phy.write(":SOUR"+self._ch+":MARK OFF\n")
            
    #SOUR:MARK:FREQ
    #queries or sets marker frequency for FM sweeps
    def do_get_marker_frequency(self):
        return float(self._phy.ask(":SOUR"+self._ch+":MARK:FREQ?\n"))
    
    def do_set_marker_frequency(self, value):
        self._phy.write(":SOUR"+self._ch+":MARK:FREQ " + str(value) + "\n")

    #SOUR:FREQ
    #queries or sets the frequency of the waveform
    #note that the highest frequency depends on the waveform
    def do_get_frequency(self):
        return float(self._phy.ask(":SOUR"+self._ch+":FREQ?\n"))
    
    def do_set_frequency(self,value):
        self._phy.write(":SOUR"+self._ch+":FREQ "+str(value)+"\n")
        
    #SOUR:FREQ:STAR|STOP
    #queries or sets the start/stop frequency for FM sweeps, respectively
    def do_get_frequency_sweep_start(self):
        return float(self._phy.ask(":SOUR"+self._ch+":FREQ:STAR?\n"))

    def do_set_frequency_sweep_start(self,value):
        self._phy.write(":SOUR"+self._ch+":FREQ:STAR "+str(value)+"\n") 

    def do_get_frequency_sweep_stop(self):
        return float(self._phy.ask(":SOUR"+self._ch+":FREQ:STOP?\n"))

    def do_set_frequency_sweep_stop(self,value):
        self._phy.write(":SOUR"+self._ch+":FREQ:STOP "+str(value)+"\n") 
        
    #SOUR:VOLT
    #queries or sets the output amplitude. Note: Vpp
    def do_get_amplitude(self):
        return float(self._phy.ask(":SOUR"+self._ch+":VOLT?\n"))
    
    def do_set_amplitude(self,value):
        self._phy.write(":SOUR"+self._ch+":VOLT "+str(value)+"\n")

    #SOUR:VOLT:OFFS
    #queries or sets the output offset.
    def do_get_offset(self):
        return float(self._phy.ask(":SOUR"+self._ch+":VOLT:OFFS?\n"))
    
    def do_set_offset(self,value):
        self._phy.write(":SOUR"+self._ch+":VOLT:OFFS "+str(value)+"\n")
        
    #SOUR:PHAS
    #queries or sets the initial phase of the waveform
    #not applicable to pulse waveform
    def do_get_phase(self):
        return float(self._phy.ask(":SOUR"+self._ch+":PHAS?\n"))
    
    def do_set_phase(self,value):
        self._phy.write(":SOUR"+self._ch+":PHAS "+str(value)+"\n")                
       
    #SOUR:PULS:DEL
    #queries or sets the delay of the pulse
    def do_get_pulse_delay(self):
        return float(self._phy.ask(":SOUR"+self._ch+":PULS:DEL?\n"))
    
    def do_set_pulse_delay(self,value):
        self._phy.write(":SOUR"+self._ch+":PULS:DEL "+str(value)+"\n")
    
    #SOUR:PULS:WIDT
    #queries or sets the pulse width
    def do_get_pulse_width(self):
        return float(self._phy.ask(":SOUR"+self._ch+":PULS:WIDT?\n"))
    
    def do_set_pulse_width(self,value):
        self._phy.write(":SOUR"+self._ch+":PULS:WIDT "+str(value)+"\n")    
        
    #SOUR:PULS:DCYC
    #queries or sets the pulse duty cycle
    def do_get_pulse_duty_cycle(self):
        return float(self._phy.ask(":SOUR"+self._ch+":PULS:DCYC?\n"))
    
    def do_set_pulse_duty_cycle(self,value):
        self._phy.write(":SOUR"+self._ch+":PULS:DCYC "+str(value)+"\n")  

    #SOUR:PULS:TRAN
    #queries or sets the pulse leading edge width
    def do_get_pulse_leading_edge(self):
        return float(self._phy.ask(":SOUR"+self._ch+":PULS:TRAN?\n"))
    
    def do_set_pulse_leading_edge(self,value):
        self._phy.write(":SOUR"+self._ch+":PULS:TRAN "+str(value)+"\n")  

    #SOUR:PULS:TRAN:TRA
    #queries or sets the pulse leading edge width
    def do_get_pulse_trailing_edge(self):
        return float(self._phy.ask(":SOUR"+self._ch+":PULS:TRAN:TRA?\n"))
    
    def do_set_pulse_trailing_edge(self,value):
        self._phy.write(":SOUR"+self._ch+":PULS:TRAN:TRA "+str(value)+"\n")  

    #SOUR:PULS:HOLD
    #sets or queries if pulse width or duty cycle is preserved when other parameters change
    def do_get_pulse_hold_parameter(self):
        return self._phy.ask(":SOUR"+self._ch+":PULS:HOLD?\n").strip() == "WIDT"
    
    def do_set_pulse_hold_parameter(self,value):
        if value:
            self._phy.write(":SOUR"+self._ch+":PULS:HOLD WIDT\n")
        else:
            self._phy.write(":SOUR"+self._ch+":PULS:HOLD DUTY\n")
    
    #SOUR:HARM:ORDE
    #sets or queries the maximum order for harmonic waveform
    def do_get_harmonic_order(self):
        return int(float(self._phy.ask(":SOUR"+self._ch+":HARM:ORDE?\n")))
    
    def do_set_harmonic_order(self,value):
        self._phy.write(":SOUR"+self._ch+":HARM:ORDE "+str(value)+"\n")
        
    #SOUR:HARM:AMPL
    #sets or queries the amplitude for harmonic overtones
    #input list is a tuple
    def do_get_harmonic_amplitudes(self):
        max_order=self.get_harmonic_order()
        ret=()
        for i in range(2,max_order):
            val=float(self._phy.ask("SOUR"+self._ch+":HARM:AMP? "+str(i)+"\n"))
            ret=ret+(val,)
        return ret

    def do_set_harmonic_amplitudes(self,value):
        max_order=self.get_harmonic_order()
        if max_order != len(value)+1:
            logging.error("Rigol_dg_wavegen: invalid number of parameters for harmonic_amplitudes")
            return False
        for i in range(2,max_order):
            self._phy.write("SOUR"+self._ch+":HARM:AMP "+str(i)+","+str(value[i-2])+"\n")
        
    #SOUR:HARM:PHAS
    #sets or queries the phase for harmonic overtones
    #input list is a tuple
    def do_get_harmonic_phases(self):
        max_order=self.get_harmonic_order()
        ret=()
        for i in range(2,max_order):
            val=float(self._phy.ask("SOUR"+self._ch+":HARM:PHAS? "+str(i)+"\n"))
            ret=ret+(val,)
        return ret

    def do_set_harmonic_phases(self,value):
        max_order=self.get_harmonic_order()
        if max_order != len(value)+1:
            logging.error("Rigol_dg_wavegen: invalid number of parameters for harmonic_phases")
            return False
        for i in range(2,max_order):
            self._phy.write("SOUR"+self._ch+":HARM:PHAS "+str(i)+","+str(value[i-2])+"\n")
    
    #SOUR:HARM:TYP
    #sets or queries the available harmonics: EVEN,ODD,ALL,USER(?)
    def do_get_harmonic_type(self):
        temp=self._phy.ask(":SOUR"+self._ch+":HARM:TYP?\n").strip()
        if temp == "EVEN":
            return 0
        elif temp == "ODD":
            return 1
        elif temp == "ALL":
            return 2
        elif temp == "USER":
            return 3
        else:
            return None
    
    def do_set_harmonic_type(self,value):
        if value == 0:
            temp="EVEN"
        elif value == 1:
            temp="ODD"
        elif value == 2:
            temp="ALL"
        elif value == 3:
            temp="USER"
        else:
            return False
        self._phy.write(":SOUR"+self._ch+":HARM:TYP "+temp+"\n")
    
    #SOUR:BURS:TDEL
    #sets or queries the delay of the waveform after trigger
    #only applies to burst mode
    def do_get_delay(self):
        return float(self._phy.ask(":SOUR"+self._ch+":BURS:TDEL?\n"))
    
    def do_set_delay(self,value):
        self._phy.write(":SOUR"+self._ch+":BURS:TDEL "+str(value)+"\n")
    
    #mode selection:
    #for mode 0 (normal), burst, sweep and mod has to be turned off
    #for the rest, the corresponding mode has to be enabled
    #format_map={0:'normal',1:'burst', 2:'sweep', 3:'mod'})     
    def do_get_mode(self):
        if self._phy.ask(":SOUR"+self._ch+":BURS?\n").strip()=="ON":
            return 1
        elif self._phy.ask(":SOUR"+self._ch+":SWE:STAT?\n").strip()=="ON":
            return 2
        elif self._phy.ask(":SOUR"+self._ch+":MOD?\n").strip()=="ON":
            return 3
        else:
            return 0
    
    def do_set_mode(self,value):
        if value == 0:
            self._phy.write(":SOUR"+self._ch+":BURS OFF\n")
            self._phy.write(":SOUR"+self._ch+":SWE:STAT OFF\n")
            self._phy.write(":SOUR"+self._ch+":MOD OFF\n")
        elif value == 1:
            self._phy.write(":SOUR"+self._ch+":BURS ON\n")
        elif value == 2:
            self._phy.write(":SOUR"+self._ch+":SWE:STAT ON\n")
        elif value == 3:
            self._phy.write(":SOUR"+self._ch+":MOD ON\n")
    
    #SOUR:BURS:MODE
    #queries or sets burst mode: triggered, gated or infinity
    def do_get_burst_mode(self):
        temp=self._phy.ask(":SOUR"+self._ch+":BURS:MODE?\n").strip()
        if temp == "TRIG":
            return 0
        elif temp == "GAT":
            return 1
        elif temp == "INF":
            return 2
        else:
            return None
        
    def do_set_burst_mode(self,value):
        if value == 0:
            self._phy.write(":SOUR"+self._ch+":BURS:MODE TRIG\n")
        elif value == 1:
            self._phy.write(":SOUR"+self._ch+":BURS:MODE GAT\n")
        elif value == 2:
            self._phy.write(":SOUR"+self._ch+":BURS:MODE INF\n")
   
    #SOUR:BURS:NCYC
    #queries or sets the number of output cycles after each trigger
    def do_get_burst_cycles(self):
        return int(self._phy.ask(":SOUR"+self._ch+":BURS:NCYC?\n"))
    
    def do_set_burst_cycles(self,value):
        self._phy.write(":SOUR"+self._ch+":BURS:NCYC "+str(value)+"\n")
         
    #SOUR:BURS:INT:PER
    #queries or sets the period of the internal trigger for burst mode
    #minimum value = 1us + length of waveform
    def do_get_burst_period(self):
        return float(self._phy.ask(":SOUR"+self._ch+":BURS:INT:PER?\n"))
    
    def do_set_burst_period(self,value):
        self._phy.write(":SOUR"+self._ch+":BURS:INT:PER "+str(value)+"\n")

    #SOUR:BURS:PHAS
    #queries or sets the phase of waveform with respect to burst trigger
    #used for burst operation
    def do_get_burst_phase(self):
        return float(self._phy.ask(":SOUR"+self._ch+":BURS:PHAS?\n"))
    
    def do_set_burst_phase(self,value):
        self._phy.write(":SOUR"+self._ch+":BURS:PHAS "+str(value)+"\n")

        
    #SOUR:BURS:TRIG:SOUR
    #queries or sets the trigger source for burst mode: internal, external or manual
    def do_get_trigger_source(self):
        temp=self._phy.ask(":SOUR"+self._ch+":BURS:TRIG:SOUR?\n").strip()
        if temp == "INT":
            return 0
        elif temp == "EXT":
            return 1
        elif temp == "MAN":
            return 2
        else:
            return None
    
    def do_set_trigger_source(self,value):
        if value == 0:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:SOUR INT\n")
        elif value == 1:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:SOUR EXT\n")
        elif value == 2:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:SOUR MAN\n")
        else:
            return False

    #SOUR:BURS:TRIG:SLOP
    #queries or sets trigger edge: falling or rising
    def do_get_trigger_edge(self):
        return self._phy.ask(":SOUR"+self._ch+":BURS:TRIG:SLOP?\n").strip() == "POS"
    
    def do_set_trigger_edge(self,value):
        if value:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:SLOP POS\n")
        else:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:SLOP NEG\n")
    
    #SOUR:BURS:GATE:POL
    #queries or sets the gate polarity for burst mode
    def do_get_gate_polarity(self):
        return self._phy.ask(":SOUR"+self._ch+":BURS:GATE:POL?\n").strip() == "NORM"    
     
    def do_set_gate_polarity(self,value):
        if value:
            self._phy.write(":SOUR"+self._ch+":BURS:GATE:POL NORM\n")
        else:
            self._phy.write(":SOUR"+self._ch+":BURS:GATE:POL INV\n")
      
    #SOUR:BURS:TRIG:TRIGO
    #queries or sets trigger output for manual or internal triggered bursts
    def do_get_trigger_out(self):
        temp=self._phy.ask(":SOUR"+self._ch+":BURS:TRIG:TRIGO?\n").strip()
        if temp == "OFF":
            return 0
        elif temp == "POS":
            return 1
        elif temp == "NEG":
            return 2
        else:
            return None
        
    def do_set_trigger_out(self,value):
        if value == 0:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:TRIGO OFF\n")
        elif value == 1:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:TRIGO POS\n")
        elif value == 2:
            self._phy.write(":SOUR"+self._ch+":BURS:TRIG:TRIGO NEG\n")

    #SOUR:SWE:HTIME:STAR|STOP
    #queries or sets the holdtime at the start/end of frequency sweep
    def do_get_sweep_holdtime_start(self):
        return float(self._phy.ask(":SOUR"+self._ch+":SWE:HTIME:STAR?\n"))

    def do_set_sweep_holdtime_start(self,value):
        self._phy.write(":SOUR"+self._ch+":SWE:HTIME:STAR " + str(value) + "\n")    

    def do_get_sweep_holdtime_stop(self):
        return float(self._phy.ask(":SOUR"+self._ch+":SWE:HTIME:STOP?\n"))

    def do_set_sweep_holdtime_stop(self,value):
        self._phy.write(":SOUR"+self._ch+":SWE:HTIME:STOP " + str(value) + "\n")
 
    #SOUR:SWE:RTIME
    #queries or sets the return time of frequency sweep
    def do_get_sweep_returntime(self):
        return float(self._phy.ask(":SOUR"+self._ch+":SWE:RTIME?\n"))

    def do_set_sweep_returntime(self,value):
        self._phy.write(":SOUR"+self._ch+":SWE:RTIME " + str(value) + "\n")  
        
    #SOUR:SWE:TIME
    #queries or sets the return time of frequency sweep
    def do_get_sweep_time(self):
        return float(self._phy.ask(":SOUR"+self._ch+":SWE:TIME?\n"))

    def do_set_sweep_time(self,value):
        self._phy.write(":SOUR"+self._ch+":SWE:TIME " + str(value) + "\n")
 
    #SOUR:SWE:SPAC
    #sets or queries the FM sweep spacing: linear, logarithmic or steps
    def do_get_sweep_spacing(self):
        temp=self._phy.ask(":SOUR"+self._ch+":SWE:SPAC?\n").strip()
        if temp == "LIN":
            return 0
        elif temp == "LOG":
            return 1
        elif temp == "STE":
            return 2
        else:
            return None
        
    def do_set_sweep_spacing(self,value):
        if value == 0:
            self._phy.write(":SOUR"+self._ch+":SWE:SPAC LIN\n")
        elif value == 1:
            self._phy.write(":SOUR"+self._ch+":SWE:SPAC LOG\n")
        elif value == 2:
            self._phy.write(":SOUR"+self._ch+":SWE:SPAC STE\n")
            
    #SOUR:SWE:STEP
    #sets or queries the number of steps for FM sweep
    def do_get_sweep_steps(self):
        return int(float(self._phy.ask(":SOUR"+self._ch+":SWE:STEP?\n")))

    def do_set_sweep_steps(self,value):
        self._phy.write(":SOUR"+self._ch+":SWE:STEP " + str(value) + "\n")
    
    #SOUR:BURS:TRIG
    #triggers a single channel of the instrument
    def trigger(self):
        self._phy.write(":SOUR"+self._ch+":BURS:TRIG\n")

    