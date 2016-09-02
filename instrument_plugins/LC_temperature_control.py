from instrument import Instrument
import types
import win32com.client
import time


class LVApp:
    """
    Class for communicating with a LabView application.
    """
    def __init__(self, AppName, ViName):
        self.App = win32com.client.Dispatch(AppName)
        self.Vi = self.App.GetViReference(ViName)

    # Reading data from VI's is straight forward
    def GetData(self, ControlName):
        return self.Vi.GetControlValue(ControlName)

    # Writing data to VI's is more complicated.
    # It is possible to write data by simply using SetControlValue(<Name>), but that does not trigger ValueChanged event
    # in LabView program. Since a lot of things are happening inside the event structure, it breaks TC and FP programs.
    # Instead there is a special cluster called "SetControl". It has three fields: "Name", "Scalar" and "Array".
    # To write data to any control put it's name in "Name" field and value in either "Scalar" or "Array" field depending on
    # data type. Do not write data in both "Scalar" and "Array" fields as the LabView program will ignore the command. Put
    # empty string '' or empty list [[], []] in the unused field.
    # It is possible to write data to individual controls in clusters by <ClusterName>.<ControlName> notation. It will
    # trigger the ValueChanged event for that control and not the cluster.
    # After the program reads the "SetControl" structure it will empty it to flag that it's been processed. Checking if
    # the cluster is empty allows synchronous operation
    def SetData(self, ControlName, ControlData, Async = False):
        if type(ControlData) in (tuple, list):
            self.Vi.SetControlValue('SetControl', (ControlName, '', ControlData))
        else:
            self.Vi.SetControlValue('SetControl', (ControlName, ControlData, [[], []]))
        if not Async:
            while self.Vi.GetControlValue('SetControl')[0] != '': time.sleep(0.1)


class LC_temperature_control(Instrument):
    """
    Driver for the Leiden Cryogenics TemperatureControl application

    Install pywin32 using downloadable 2.7 32-bit installer

    If using an environment, put the path to it in the following
    registery key:

    HKEY_CURRENT_USER/Software/Python/PythonCore/2.7/InstallPath
    """
    def __init__(self, name, reset=False):
        Instrument.__init__(self, name)

        self.FP = LVApp("DRTempControl.Application",
                        "DR TempControl.exe\TC.vi")

        self._channels = range(10)
        self._currents = range(3)

        self.add_parameter('avs_name',
                           flags=Instrument.FLAG_GET,
                           type=types.StringType,
                           channels=self._channels)

        self.add_parameter('current',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._currents,
                           units='A')

        self.add_parameter('resistance',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._channels,
                           units='Ohm')

        self.add_parameter('temperature',
                           flags=Instrument.FLAG_GET,
                           type=types.FloatType,
                           channels=self._channels,
                           units='K')

        self.get_all()

    def do_get_avs_name(self, channel):
        return self.FP.GetData('AVS names')[channel]

    def do_get_current(self, channel):
        return self.FP.GetData('I')[channel]

    def do_get_resistance(self, channel):
        return self.FP.GetData('R')[channel]

    def do_get_temperature(self, channel):
        return self.FP.GetData('T')[channel]

    def get_all(self):
        for i in self._channels:
            self.get('avs_name%d' % i)
            self.get('resistance%d' % i)
            self.get('temperature%d' % i)

        for i in self._currents:
            self.get('current%d' % i)
