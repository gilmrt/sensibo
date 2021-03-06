# -*- coding: utf-8 -*-
#
#     pySensibo_Sky - A python library to access the Sensibo Sky API
#     Copyright (C) 2018  Kevin G. Schlosser
#
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import print_function
import sys
import os

PY2 = sys.version_info.major == 2

pth = sys.executable
pth = os.path.split(pth)[0]

if 'eventghost' in pth.lower():
    pth = os.path.join(pth, 'lib27')
    sys.path += [os.path.join(pth, 'site-packages')]
else:
    pth = os.path.join(pth, 'lib')

ca_path = os.path.join(pth, 'site-packages', 'requests')

if os.path.isdir(ca_path) and 'cacert.pem' in os.listdir(ca_path):
    os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(ca_path, 'cacert.pem')

import threading  # NOQA
import requests  # NOQA
import json  # NOQA
import fnmatch  # NOQA

from uuid import uuid4 as new_guid  # NOQA


_SERVER = 'https://home.sensibo.com/api/v2'


def c2f(c_temp):
    return float(c_temp) * 9.0 / 5.0 + 32.0


def f2c(f_temp):
    return (float(f_temp) - 32.0) * 5.0 / 9.0


class Singleton(type):
    _instances = {}

    def __call__(cls, *args):
        if cls not in cls._instances:
            cls._instances[cls] = {}

        keys = list(args[:])
        for i, arg in enumerate(keys[:]):
            if isinstance(arg, dict):
                keys[i] = str(arg)

        keys = tuple(keys)

        instances = cls._instances[cls]

        for key, value in instances.items():
            if key == keys:
                return value

        instances[keys] = super(
            Singleton,
            cls
        ).__call__(*args)

        return instances[keys]


class Notify(object):

    def __init__(self):
        self.__callbacks = {}

    def bind(self, event, callback):
        guid = new_guid()
        if event not in self.__callbacks:
            self.__callbacks[event] = {}

        self.__callbacks[event][guid] = callback

        return guid

    def unbind(self, guid):
        for callbacks in self.__callbacks.values():
            if guid in callbacks:
                del (callbacks[guid])

    def __call__(self, event, value, obj):

        def process_callbacks(e):
            for callback in self.__callbacks[e].values():
                callback(event, value, obj)

        for evt in self.__callbacks.keys():
            if ('*' in evt or '?' in evt) and fnmatch.fnmatch(event, evt):
                process_callbacks(evt)
            elif evt.lower() == event:
                process_callbacks(evt)


Notify = Notify()


class Mode(object):
    __metaclass__ = Singleton

    def __init__(self, pod, name, supported):
        self._pod = pod
        self.name = name
        self._supported = supported

    @property
    def supported_swing_modes(self):
        """
        Gets the supported swing modes for this device mode.

        *Returns:* A `list` of supported swing modes

            Example list items:

                * ``"stopped"``
                * ``"rangeFull"``

        *Return type:* `list`
        """

        if 'swing' in self._supported:
            return self._supported['swing']
        raise AttributeError

    @property
    def supported_temp_units(self):
        """
        Gets the supported temperature units for this device mode.

        *Returns:* A `list` of supported temperature units.

            Example list items:

                * ``"C"``
                * ``"F"``
                * ``"Celsius"``
                * ``"Fahrenheit"``

        *Return type:* `list`
        """
        if 'temperatures' in self._supported:
            return self._supported['temperatures'].keys()
        raise AttributeError

    @property
    def supported_temps(self):
        """
        Gets the supported temperatures for this device mode.

        *Returns:* A `list` of supported temperatures for the current
        temperature unit.

        *Return type:* `list`
        """
        try:
            temp_unit = self.temp_unit
        except AttributeError:
            raise AttributeError

        if (
            'temperatures' in self._supported and
            temp_unit in self._supported['temperatures']
        ):
            return self._supported['temperatures'][self.temp_unit]['values']
        raise AttributeError

    @property
    def supported_fan_levels(self):
        """
        Gets the supported fan modes for this device mode.

        *Returns:* A `list` of supported fan modes

            Example list items:

                * ``"low"``
                * ``"medium_low"``
                * ``"medium"``
                * ``"medium_high"``
                * ``"high"``
                * ``"auto"``

        *Return type:* `list`
        """
        if 'fanLevels' in self._supported:
            return self._supported['fanLevels']
        raise AttributeError

    @property
    def swing(self):
        """
        Swing mode.

        **Getter:** Gets the swing mode.

            *Returns:* A `list` of possible returned values can be obtained
            from :attr:`~Mode.supported_swing_modes`

            *Return type:* `str`

        **Setter:** Sets the swing mode.

            *Accepted values:* A `list` of acceptable values can be obtained
            from :attr:`~Mode.supported_swing_modes`

            *Value type:* `str`
        """
        state = self._pod.state
        if 'swing' in state:
            return state['swing']
        raise AttributeError

    @swing.setter
    def swing(self, value):
        try:
            if value in self.supported_swing_modes:
                self._pod.set_state(swing=value)
            else:
                raise ValueError
        except AttributeError:
            raise AttributeError

    @property
    def temp_unit(self):
        """
        Temperature unit of measure.

        **Getter:** Gets the temp unit.

            *Returns:* A `list` of possible returned values can be obtained
            from :attr:`~Mode.supported_temp_units`

            *Return type:* `str`

        **Setter:** Sets the temp unit.

            *Accepted values:* A `list` of acceptable values can be obtained
            from :attr:`~Mode.supported_temp_units`

            *Value type:* `str`
        """
        state = self._pod.state
        if 'temperatureUnit' in state:
            return state['temperatureUnit']
        raise AttributeError

    @temp_unit.setter
    def temp_unit(self, value):

        values = (
            value.lower(),
            value.title(),
            value.title()[0],
            value.lower()[0]
        )

        for v in values:
            if v in self.supported_temp_units:
                self._pod.set_state(temperatureUnit=v)
                break
        else:
            raise ValueError

    @property
    def temp(self):
        """
        Temperature set point.

        **Getter:** Gets the set point.

            *Returns:* A `list` of possible returned values can be obtained
            from :attr:`~Mode.supported_temps`

            *Return type:* `int`

        **Setter:** Sets the set point.

            *Accepted values:* A `list` of acceptable values can be obtained
            from :attr:`~Mode.supported_temps`

            *Value type:* `int`
        """
        state = self._pod.state
        if 'targetTemperature' in state:
            return state['targetTemperature']
        raise AttributeError

    @temp.setter
    def temp(self, value):
        value = int(value)
        try:
            if value in self.supported_temps:
                self._pod.set_state(targetTemperature=value)
            else:
                raise ValueError
        except AttributeError:
            raise AttributeError

    @property
    def fan_level(self):
        """
        Fan speed.

        **Getter:** Gets the fan speed.

            *Returns:* A `list` of possible returned values can be obtained
            from :attr:`~Mode.supported_fan_levels`

            *Return type:* `str`

        **Setter:** Sets the fan speed.

            *Accepted values:* A `list` of acceptable values can be obtained
            from :attr:`~Mode.supported_fan_levels`

            *Value type:* `str`
        """
        state = self._pod.state
        if 'fanLevel' in state:
            return state['fanLevel']
        raise AttributeError

    @fan_level.setter
    def fan_level(self, value):
        try:
            if value in self.supported_fan_levels:
                self._pod.set_state(fanLevel=value)
            else:
                raise ValueError
        except AttributeError:
            raise AttributeError

    @property
    def pod(self):
        """
        Gets the supported swing modes for this device mode.

        *Returns:* The device instance for this mode

        *Return type:* :class:`Pod` instance
        """
        return self._pod

    def activate(self):
        """
        Activates this mode on the parent device.
        """
        if self._pod.mode != self:
            self._pod.mode = self

    def bind(self, property_name, callback):
        property_names = (
            'swing',
            'temp',
            'fan_level',
            'temp_unit',
            '*'
        )

        if property_name not in property_names:
            raise ValueError

        return Notify.bind(
            '{0}.{1}.{2}'.format(
                self._pod.name,
                self.name,
                property_name
            ),
            callback
        )


class Pod(object):
    __metaclass__ = Singleton

    def __init__(self, api_key, name, uid):
        self.__fnht = None
        self.__clcs = None

        self._api_key = api_key

        if PY2:
            self.name = name.encode('utf-8')
        else:
            self.name = str(name)

        self.uid = uid
        self._model = None
        self._capabilities = None

        mode = self.state['mode']
        self._mode = Mode(self, mode, self.capabilities['modes'][mode])
        self._event = threading.Event()
        self._thread = None

    def start_poll(self, poll_interval):
        """
        Start polling.

        Starts a polling cycle for a Sensibo device. When a polling cycle is
        started for each device a new thread is created so the cycles can run
        parallel to each other.

        :param poll_interval: how often to check, decimal notation of seconds.
        Example:
            * ``0.5`` - half a second
            * ``1.0`` - one second
            * ``2.25`` - two and a quarter seconds
        :type poll_interval: float

        :return: None
        :rtype: None
        """
        while self._event.isSet():
            pass

        if self._thread is None:
            self._thread = threading.Thread(
                target=self._poll,
                args=(poll_interval,)
            )
            self._thread.start()

    def stop_poll(self):
        """
        Stops the polling cycle.

        Stops the polling cycle if one is running.

        :return: None
        :rtype: None
        """
        if self._thread is not None:
            self._event.set()
            self._thread.join(3)

    @property
    def is_polling(self):
        """
        Checks if there is a running polling cycle.
        :return: True/False
        :rtype: bool
        """
        return self._thread is not None and not self._event.isSet()

    def _poll(self, poll_interval):
        old_state = dict(
            mode=None,
            swing=None,
            targetTemperature=None,
            fanLevel=None,
            on=None,
            temperatureUnit=None
        )

        for key, value in self.state.items():
            old_state[key] = value

        measurements = self._measurements

        old_measurements = dict(
            temperature=None,
            humidity=None,
            batteryVoltage=None
        )

        if 'temperature' in measurements:
            old_measurements['temperature'] = measurements['temperature']

        if 'humidity' in measurements:
            old_measurements['humidity'] = measurements['humidity']

        if 'batteryVoltage' in measurements:
            old_measurements['batteryVoltage'] = measurements['batteryVoltage']

        while not self._event.isSet():
            state = self.state
            measurements = self._measurements

            if 'mode' in state:
                mode = state['mode']
            else:
                mode = None

            if 'swing' in state:
                swing = state['swing']
            else:
                swing = None

            if 'targetTemperature' in state:
                temp = state['targetTemperature']
            else:
                temp = None

            if 'fanLevel' in state:
                fan = state['fanLevel']
            else:
                fan = None

            if 'on' in state:
                power = state['on']
            else:
                power = None

            if 'temperatureUnit' in state:
                temp_unit = state['temperatureUnit']
            else:
                temp_unit = None

            if 'temperature' in measurements:
                temperature = measurements['temperature']
            else:
                temperature = None
            if 'humidity' in measurements:
                humidity = measurements['humidity']
            else:
                humidity = None

            if 'batteryVoltage' in measurements:
                battery_voltage = measurements['batteryVoltage']
            else:
                battery_voltage = None

            if mode is not None and mode != old_state['mode']:
                self._mode = Mode(self, mode, self.capabilities['modes'][mode])
                old_state['mode'] = mode
                Notify('{0}.mode'.format(self.name), self._mode.name, self)

            if swing is not None and swing != old_state['swing']:
                old_state['swing'] = swing
                Notify(
                    '{0}.{1}.swing'.format(self.name, self._mode.name),
                    swing,
                    self._mode
                )

            if temp is not None and temp != old_state['targetTemperature']:
                old_state['targetTemperature'] = temp

                Notify(
                    '{0}.{1}.temp'.format(self.name, self._mode.name),
                    temp,
                    self._mode
                )

            if fan is not None and fan != old_state['fanLevel']:
                old_state['fanLevel'] = fan
                Notify(
                    '{0}.{1}.fan_level'.format(self.name, self._mode.name),
                    fan,
                    self._mode
                )

            if power is not None and power != old_state['on']:
                old_state['on'] = power

                Notify(
                    '{0}.power'.format(self.name),
                    bool(power),
                    self
                )

            if (
                temp_unit is not None and
                temp_unit != old_state['temperatureUnit']
            ):
                old_state['temperatureUnit'] = temp_unit

                Notify(
                    '{0}.{1}.temp_unit'.format(self.name, self._mode.name),
                    temp_unit,
                    self._mode
                )

            def hi_dp_event():
                try:
                    Notify(
                        '{0}.room_dew_point'.format(self.name),
                        self.room_dew_point,
                        self
                    )
                    Notify(
                        '{0}.room_heat_index'.format(self.name),
                        self.room_heat_index,
                        self
                    )
                except AttributeError:
                    pass

            def rh_event():
                Notify(
                    '{0}.room_humidity'.format(self.name),
                    humidity,
                    self
                )

            def temp_event():
                Notify(
                    '{0}.room_temp'.format(self.name),
                    temperature,
                    self
                )

            if (
                humidity != old_measurements['humidity'] and
                temperature != old_measurements['temperature']
            ):
                old_measurements['temperature'] = temperature
                old_measurements['humidity'] = humidity
                temp_event()
                rh_event()
                hi_dp_event()

            elif temperature != old_measurements['temperature']:
                old_measurements['temperature'] = temperature
                temp_event()
                hi_dp_event()

            elif humidity != old_measurements['humidity']:
                old_measurements['humidity'] = humidity
                rh_event()
                hi_dp_event()

            if battery_voltage != old_measurements['batteryVoltage']:
                old_measurements['batteryVoltage'] = battery_voltage

                Notify(
                    '{0}.battery_voltage'.format(self.name),
                    battery_voltage,
                    self
                )

            self._event.wait(poll_interval)

        self._thread = None
        self._event.clear()

    @property
    def supported_modes(self):
        """
        Supported modes.

        *Returns:* a `list` of :class:`Mode' instances this device supports.

        *Return type:* `list`
        """
        for mode in sorted(self.capabilities['modes'].keys()):
            yield Mode(self, mode, self.capabilities['modes'][mode])

    @property
    def capabilities(self):
        """
        Device capabilities.

        *Returns:* The devices capability.

        *Return type:* `dict`
        """
        if self._capabilities is None:
            self._capabilities = self._get(
                fields='remoteCapabilities'
            )['remoteCapabilities']
        return self._capabilities

    @property
    def model(self):
        """
        Model.

        *Returns:* The device model number.

        *Return type:* `str`
        """
        if self._model is None:
            self._model = self._get(
                fields='productModel'
            )['productModel']
        return self._model

    def _get(self, path=None, **params):
        params['apiKey'] = self._api_key

        if path is None:
            response = requests.get(
                '{0}/pods/{1}'.format(_SERVER, self.uid),
                params=params
            )
        else:
            response = requests.get(
                '{0}/pods/{1}/{2}'.format(_SERVER, self.uid, path),
                params=params
            )

        response.raise_for_status()

        response = json.loads(response.content.decode())['result']

        try:
            return response[0]
        except KeyError:
            return response

    def _patch(self, property_name, data, **params):
        params['apiKey'] = self._api_key
        response = requests.patch(
            "{0}/pods/{1}/acStates/{2}".format(
                _SERVER,
                self.uid,
                property_name
            ),
            params=params,
            data=data
        )
        response.raise_for_status()

        return json.loads(response.content.decode())

    def _post(self, path, data, **params):
        params['apiKey'] = self._api_key
        response = requests.post(
            '{0}/pods/{1}/{2}'.format(_SERVER, self.uid, path),
            params=params,
            data=data
        )
        response.raise_for_status()
        return json.loads(response.content.decode())

    @property
    def _measurements(self):
        try:
            result = self._get(
                "measurements",
                fields="batteryVoltage,temperature,humidity,time"
            )
        except requests.HTTPError:
            result = self._get(
                "measurements",
                fields="temperature,humidity,time"
            )

        return result

    @property
    def battery_voltage(self):
        """
        Battery voltage.

        *Returns:* The battery voltage (if supported).

        *Return type:* `float`
        """
        try:
            return self._measurements['batteryVoltage']
        except KeyError:
            raise AttributeError

    @property
    def room_humidity(self):
        """
        Room Humidity.

        *Returns:* The humidity in the room.

        *Return type:* `float`
        """
        try:
            return self._measurements['humidity']
        except KeyError:
            raise AttributeError

    @property
    def room_temp(self):
        """
        Room Temperature.

        *Returns:* The temperature of the room.

        *Return type:* `float`
        """
        try:
            return self._measurements['temperature']
        except KeyError:
            raise AttributeError

    @property
    def room_dew_point(self):
        """
        Room Dew Point.

        *Returns:* The dew point in the room.

        *Return type:* `float`
        """
        temp = self.room_temp
        humidity = self.room_humidity

        try:
            self.__fnht = fnht = self.mode.temp_unit.lower().startswith('f')
            self.__clcs = not self.__fnht
        except AttributeError:
            if self.__fnht is None:
                raise AttributeError
            fnht = self.__fnht

        if fnht:
            temp = f2c(temp)

        if temp > 0:
            var1 = 17.368
            var2 = 238.88
        else:
            var1 = 17.966
            var2 = 247.15

        import math

        pa = humidity / 100. * math.exp(var1 * temp / (var2 + temp))
        dew_point = var2 * math.log(pa) / (var1 - math.log(pa))

        if fnht:
            dew_point = c2f(dew_point)

        return dew_point

    @property
    def room_heat_index(self):
        """
        Room Heat Index.

        *Returns:* The heat index in the room.

        *Return type:* `float`
        """
        temp = self.room_temp
        humidity = self.room_humidity

        try:
            self.__clcs = clcs = self.mode.temp_unit.lower().startswith('c')
            self.__fnht = not self.__clcs
        except AttributeError:
            if self.__clcs is None:
                raise AttributeError
            clcs = self.__clcs

        if clcs:
            temp = c2f(temp)

        heat_index = (
            0.5 * (temp + 61.0 + (temp - 68.0) * 1.2 + humidity * 0.094)
        )

        if heat_index >= 80:
            import math

            heat_index = math.fsum([
                -42.379,
                2.04901523 * temp,
                10.14333127 * humidity,
                -0.22475541 * temp * humidity,
                -6.83783e-3 * temp ** 2,
                -5.481717e-2 * humidity ** 2,
                1.22874e-3 * temp ** 2 * humidity,
                8.5282e-4 * temp * humidity ** 2,
                -1.99e-6 * temp ** 2 * humidity ** 2,
            ])

        if clcs:
            heat_index = f2c(heat_index)

        return heat_index

    @property
    def state(self):
        result = self._get(
            "acStates",
            limit=1,
            fields="status,reason,acState"
        )

        return result['acState']

    def set_state(self, **kwargs):
        data = dict(
            currentAcState=self.state,
            newValue=list(kwargs.values())[0]
        )
        self._patch(
            list(kwargs.keys())[0],
            json.dumps(data)
        )

    @property
    def power(self):
        """
        Device power.

        **Getter:** Gets the power state of the device.

            *Returns:* ``True`` or ``False``

            *Return type:* `bool`

        **Setter:** Sets the power state of the device.

            *Accepted values:* ``True`` or ``False``

            *Value type:* `bool`
        """
        return self.state['on']

    @power.setter
    def power(self, value=False):
        self.set_state(on=value)

    @property
    def mode(self):
        """
        Mode.

        **Getter:** Gets the mode the device is in.

            *Returns:* A :class:`Mode` instance that represents the current
            device mode.

            *Return type:* :class:`Mode` instance

        **Setter:** Sets the mode.

            *Accepted values:* Either a :class:`Mode` instance or one of the
            `str` values below.

                * ``"cool"``
                * ``"fan"``
                * ``"heat"``
                * ``"auto"``
                * ``"dry"``

            *Value type:* `str` or :class:`Mode` instance
        """
        return self._mode

    @mode.setter
    def mode(self, value):

        if isinstance(value, Mode):
            if value.pod == self and value != self._mode:
                if not self.is_polling:
                    self._mode = value
                self.set_state(mode=value.name)
            else:
                raise ValueError

        elif 'mode' in self.capabilities['modes']:
            for found_mode in self.supported_modes:
                if found_mode.name == value:
                    if not self.is_polling:
                        self._mode = found_mode

                    self.set_state(mode=value)
                    break
            else:
                raise ValueError
        else:
            raise AttributeError

    @property
    def firmware_version(self):
        """
        Gets the devices firmware version.

        *Returns:* Firmware version.

        *Return type:* `str`
        """
        result = self._get('acStates', fields='device', limit=1)
        if 'firmwareVersion' in result['device']:
            return result['device']['firmwareVersion']
        raise AttributeError

    def bind(self, property_name, callback):
        """
        Bind event.

        Bind a callback to a specific setting change on the Sensibo device.
        This will bind a callback for this device only. You must have a
        polling cycle running to recieve a callback.

        :param property_name: The name of the item to monitor for changes.
        Can be one of the following:

            * ``'mode'`` - Operating mode.
            * ``'power'`` - Power.
            * ``'room_temp'`` - Temperature of the room.
            * ``'room_humidity'`` - Humidity of the room.
            * ``'battery_voltage'`` - Battery voltage (if supported)
            * ``'*'`` - All of the above

        :type property_name: str
        :param callback: Callable object.
        When called there are 3 arguments that are passed:

            * event - A ``str`` that represents the name of the event.
            * value - The new value that has been set.
            * event object - the object that holds the property that has
            changed. This will be either a :class:`Pod` instance or a
            :class:`Mode` instance
        :return: A unique identifier that is used when unbind from the event.
        :rtype: str
        """
        property_names = (
            'mode',
            'power',
            'room_temp',
            'room_humidity',
            'battery_voltage',
            '*'
        )

        if property_name in property_names[:6]:
            return Notify.bind(
                '{0}.{1}'.format(self.name, property_name),
                callback
            )
        elif property_name in property_names[6:]:
            return Notify.bind(
                '{0}.*.{1}'.format(self.name, property_name),
                callback
            )
        else:
            raise ValueError

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        for mode in self.supported_modes:
            if mode.name == item:
                return mode

        raise AttributeError


class Client(object):

    def __init__(self, api_key):
        self._api_key = api_key

    def bind(self, property_name, callback):
        """
        Bind event.

        Bind a callback to a specific setting change on the Sensibo device.
        This will bind a callback for all devices that have a polling cycle
        running.

        :param property_name: The name of the item to monitor for changes.
        Can be one of the following:

            * ``'mode'`` - Operating mode.
            * ``'power'`` - Power.
            * ``'room_temp'`` - Temperature of the room.
            * ``'room_humidity'`` - Humidity of the room.
            * ``'battery_voltage'`` - Battery voltage (if supported)
            * ``'swing'`` - Air flow control.
            * ``'temp'`` - Temperature set point.
            * ``'fan_level'`` - Fan speed.
            * ``'temp_unit'`` - Unit of measure (C/F).
            * ``'*'`` - All of the above

        :type property_name: str
        :param callback: Callable object.
        When called there are 3 arguments that are passed:

            * event - A ``str`` that represents the name of the event.
            * value - The new value that has been set.
            * event object - the object that holds the property that has
            changed. This will be either a :class:`Pod` instance or a
            :class:`Mode` instance
        :return: A unique identifier that is used when unbind from the event.
        :rtype: str
        """

        property_names = (
            'mode',
            'power',
            'room_temp',
            'room_humidity',
            'battery_voltage',
            'swing',
            'temp',
            'fan_level',
            'temp_unit',
            '*'
        )

        if property_name not in property_names:
            raise ValueError

        return Notify.bind('*' + property_name, callback)

    def unbind(self, guid):
        """
        Unbinds an event callback.

        :param guid: This is returned when an event is bound to a callback.
        :type guid: str
        :return: None
        :rtype: None
        """
        Notify.unbind(guid)

    @property
    def device_names(self):
        """
        Gets all available unit (room) names.
        :return: a `list` of all available unit (room) names.
        :rtype: list
        """
        return sorted(self.devices.keys())

    @property
    def devices(self):
        """
        Gets all unit names and accompanying UID's for the units.
        :return: `dict` of the names: uid.
        :rtype: dict
        """
        params = dict(
            apiKey=self._api_key,
            fields="id,room"
        )

        response = requests.get(
            _SERVER + '/users/me/pods',
            params=params
        )

        response.raise_for_status()
        result = json.loads(response.content.decode())
        devices = []

        for device in result['result']:
            devices += [(device['room']['name'], device['id'])]

        return dict(devices)

    def get_device(self, name):
        """
        Get device.

        Creates a :class:`Pod` instance that represents a device.

        :param name: Unit (room) name.
        :type name: str
        :return: A :class:`Pod` instance
        :rtype: Pod
        """
        devices = self.devices

        try:
            name = name.decode('utf-8')
        except UnicodeDecodeError:
            try:
                name = (
                    name.decode('latin-1').decode('utf-8')
                )
            except UnicodeEncodeError:
                pass

        except AttributeError:
            pass

        for pod_name in devices.keys():
            try:
                pd_name = pod_name.decode('utf-8')
            except UnicodeEncodeError:
                try:
                    pd_name = pod_name.decode('latin-1').decode('utf-8')
                except UnicodeEncodeError:
                    pd_name = pod_name
            except AttributeError:
                pd_name = pod_name

            if pd_name == name:
                return Pod(
                    self._api_key,
                    pd_name,
                    devices[pod_name]
                )


if __name__ == "__main__":

    def get_client():
        try:
            a_key = raw_input('Enter API Key: ').strip()
        except NameError:
            a_key = input('Enter API Key: ').strip()

        try:
            return Client(a_key)
        except:
            print('Invalid API key or unable to connect to server.')
            return get_client()

    client = get_client()

    def connect_device():
        print("-" * 10, "devices", "-" * 10)
        for d in client.device_names:
            print(d)
        print('-' * 29)

        try:
            dev_name = raw_input('Enter device name to connect to: ').strip()
        except NameError:
            dev_name = input('Enter device name to connect to: ').strip()

        try:
            d = client.get_device(dev_name)
            print('Successfully connected to ' + dev_name)
            return d
        except:
            print('Invalid device.')
            return connect_device()

    dev = connect_device()

    HELP = '''
    Commands

    list devices - Lists all devices (pods)

    connect DEVICE NAME - Use this to connect to a device (pod), replace
                          DEVICE NAME with the name of the device.

    power - Gets the power state.
    operating mode - Gets the operating mode.
    scale = Gets the scale (unit of measure).
    temperature setpoint - Gets the temperature setpoint.
    swing mode - Gets the swing mode.
    fan level - Gets the fan level (speed)
    temperature - Gets the room temperature.
    humidity - Gets the room humidity.
    heat index - Gets the room heat index.
    dew point - Gets the room dew point.
    battery voltage - Gets the battery voltage (if supported)
    firmware version - Gets the firmware revision.
    model number - Gets the model number.
    uid - Gets the Unit Id (UID)
    info = Displays all of the devices information

    Use the next items to get the lists of specific values your
    device supports.

    supported operating modes
    supported temperature setpoints
    supported scales
    supported swing modes
    supported fan levels


    Use the following items to set specific features. Replace the argument
    name in capital letters with the value you want to use.

    operating mode MODE NAME
    temperature setpoint TEMPERATURE
    swing mode SWING MODE
    fan level FAN SPEED
    power POWER
    scale SCALE

    start poll POLLING SPEED - poll the device for changes.
                               POLLING SPEED is in seconds
                               example:
                                   "start poll 2.0" - every 2 seconds
                                   "start poll 0.5" - every 1/2 a second

    '''
    print('"help" for a list of commands')
    poll_guid = None


    def _callback(ev, vl, _):
        print(ev, '=', vl)


    while True:
        try:
            try:
                command = raw_input('Enter Command: ').strip()
            except NameError:
                command = input('Enter Command: ').strip()

            if command == 'help':
                print(HELP)
                continue

            if command == 'list devices':
                print("-" * 10, "devices", "-" * 10)
                for d in client.device_names:
                    print(d)
                print('-' * 29)
                continue

            if dev is None and 'connect' not in command:
                print('You need to connect to a device first')
                print()
                print(HELP)
                continue

            if 'connect' in command:
                device_name = command.replace('connect ', '')
                dev = client.get_device(device_name)
                print('Successfully connected to ' + device_name)
                continue

            elif command == 'info':
                device_attrs = (
                    'Model',
                    'Name',
                    'UID',
                    'Firmware Version',
                    'Battery Voltage',
                    'Power',
                    'Room Temp',
                    'Room Humidity',
                    'Room Dew Point',
                    'Room Heat Index'
                )

                for d_attr in device_attrs:
                    attr = getattr(dev, d_attr.lower().replace(' ', '_'), None)
                    if isinstance(attr, list):
                        print('Device', d_attr + ':')
                        for list_item in attr:
                            print('   ', list_item)
                    else:
                        print('Device', d_attr + ':', attr)

                print('Set Mode:', dev.mode.name)

                try:
                    print('Set Temp:', dev.mode.temp, dev.mode.temp_unit)
                except AttributeError:
                    pass

                try:
                    print('Set Fan Level:', dev.mode.fan_level)
                except AttributeError:
                    pass

                try:
                    print('Set Swing Mode:', dev.mode.swing)
                except AttributeError:
                    pass

                print('Supported Modes:')

                for m in dev.supported_modes:
                    print('   ', m.name)
                    mode_attrs = (
                        'Supported Swing Modes',
                        'Supported Temp Units',
                        'Supported Temps',
                        'Supported Fan Levels'
                    )

                    for m_attr in mode_attrs:
                        attr = getattr(
                            m,
                            m_attr.lower().replace(' ', '_'),
                            None
                        )


                        def iter_attr(a, label, indent):
                            if isinstance(attr, list):
                                print(indent, label + ':')
                                for itm in a:
                                    print(indent, '  ', itm)
                            elif isinstance(a, dict):
                                print(indent, label + ':')
                                for k, v in a.items():
                                    iter_attr(v, k, indent + '    ')
                            else:
                                print(indent, label + ':', a)


                        iter_attr(attr, m_attr, '       ')
                continue

            try:

                if command.startswith('power'):
                    command = command.replace('power', '').strip()
                    if command:
                        if command == 'on':
                            command = True

                        elif command == 'off':
                            command = False
                        else:
                            raise ValueError

                        dev.power = command

                    else:
                        print('on' if dev.power else 'off')
                elif command.startswith('operating mode'):
                    command = command.replace('operating mode', '').strip()
                    if command:
                        dev.mode = command

                    else:
                        print(dev.mode.name)
                elif command.startswith('scale'):
                    command = command.replace('scale', '').strip()
                    if command:
                        dev.mode.temp_unit = command

                    else:
                        print(dev.mode.temp_unit)
                elif command.startswith('temperature setpoint'):
                    command = command.replace(
                        'temperature setpoint',
                        ''
                    ).strip()

                    if command:
                        dev.mode.temp = int(command)

                    else:
                        print(dev.mode.temp)
                elif command.startswith('swing mode'):
                    command = command.replace('swing mode', '').strip()
                    if command:
                        dev.mode.swing = command

                    else:
                        print(dev.mode.swing)
                elif command.startswith('fan level'):
                    command = command.replace('fan level', '').strip()
                    if command:
                        dev.mode.fan_level = command

                    else:
                        print(dev.mode.fan_level)

                elif command.startswith('start poll'):
                    command = command.replace('start poll ', '').strip()

                    if poll_guid is not None:
                        client.unbind(poll_guid)
                        dev.stop_poll()
                        poll_guid = None

                    if command and command != '0.0':
                        dev.start_poll(float(command))
                        poll_guid = dev.bind('*', _callback)
                        print('Polling started.')

                    else:
                        print('Polling stopped.')

                    continue
                elif command == 'temperature':
                    print(dev.room_temp)
                elif command == 'humidity':
                    print(dev.room_humidity)
                elif command == 'battery voltage':
                    print(dev.battery_voltage)
                elif command == 'firmware version':
                    print(dev.firmware_version)
                elif command == 'model number':
                    print(dev.model)
                elif command == 'uid':
                    print(dev.uid)
                elif command == 'heat index':
                    print(dev.room_heat_index)
                elif command == 'dew point':
                    print(dev.room_dew_point)
                elif command == 'supported operating modes':
                    for m in dev.supported_modes:
                        print(m.name)
                elif command == 'supported temperature setpoints':
                    for t in dev.mode.supported_temps:
                        print(t)
                elif command == 'supported scales':
                    for u in dev.mode.supported_temp_units:
                        print(u)
                elif command == 'supported swing modes':
                    for s in dev.mode.supported_swing_modes:
                        print(s)
                elif command == 'supported fan levels':
                    for f in dev.mode.supported_fan_levels:
                        print(f)
                else:
                    raise AttributeError
            except AttributeError:
                print('Command not valid for this device/mode')
                continue
            except ValueError:
                print('setting value not allowed for this command')
                continue

            except Exception:
                import traceback


                traceback.print_exc()
                continue

        except KeyboardInterrupt:
            break
