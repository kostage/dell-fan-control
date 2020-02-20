#!/usr/bin/python3

import yaml

from fan_control_utilities import HystSpeedCurveStub
from fan_control_utilities import HystSpeedCurve
from fan_control_utilities import TempSensorStub
from fan_control_utilities import ThreadedTS
from fan_control_utilities import FanStub
from fan_control_utilities import Fan
from fan_control_utilities import FanControl


class FanBuilder:
    def __init__(self, type):
        self.__type = type

    def build(self, obj_attrs):
        sys_file_name = obj_attrs['sys_path']
        return self.__build(sys_file_name)

    def __build(self, sys_file_name):
        return self.__type(sys_file_name)


class TempSensorBuilder:
    def __init__(self, type):
        self.__type = type

    def build(self, obj_attrs):
        sys_file_name_list = obj_attrs['sys_path_list']
        order = obj_attrs['filter_order']
        period = obj_attrs['poll_period']
        return self.__build(sys_file_name_list, order, period)

    def __build(self, sys_file_name_list, order, period):
        return self.__type(sys_file_name_list, order, period)


class HystCurveBuilder:
    def __init__(self, type):
        self.__type = type

    def build(self, obj_attrs):
        speed_zones = obj_attrs['speed_zones']
        transition_temps = obj_attrs['transition_temps']
        hyst_gap = obj_attrs['hyst_gap']
        return self.__build(speed_zones, transition_temps, hyst_gap)

    def __build(self, speed_zones, transition_temps, hyst_gap):
        return self.__type(speed_zones, transition_temps, hyst_gap)


class FanControlBuilder:
    def __init__(self, type):
        self.__type = type

    def build(self, obj_attrs, objects):
        fan = objects[obj_attrs['fan']]
        curve = objects[obj_attrs['curve']]
        ts = objects[obj_attrs['ts']]
        return self.__build(fan, ts, curve)

    def __build(self, fan, ts, hyst_curve):
        return self.__type(fan, ts, hyst_curve)


class FanControlSystem:
    def __init__(self, ymlfile_name, debug_stub):
        self.__builders = dict()
        self.__init_builders(debug_stub)
        ymlfile = open(ymlfile_name, 'r')
        self.__objects_cfg = yaml.load(ymlfile)
        self.__utility_objects = dict()
        self.__build_utility_objects()
        self.__fan_controls = dict()
        self.__build_fan_controls()

    def start(self):
        for fan_control in self.__fan_controls.values():
            fan_control.start()

    def stop(self):
        for fan_control in self.__fan_controls.values():
            fan_control.stop_and_set_max_speed()

    def update_fan_controls(self):
        for fan_control in self.__fan_controls.values():
            fan_control.update_fan_speed_according_to_temp()

    def __init_builders(self, debug_stub):
        if debug_stub:
            self.__builders = {
                'fan': FanBuilder(FanStub),
                'temp_sensor': TempSensorBuilder(TempSensorStub),
                'hyst_curve': HystCurveBuilder(HystSpeedCurveStub)
            }
        else:
            self.__builders = {
                'fan': FanBuilder(Fan),
                'temp_sensor': TempSensorBuilder(ThreadedTS),
                'hyst_curve': HystCurveBuilder(HystSpeedCurve)
            }

    def __build_utility_objects(self):
        utility_object_cfgs = \
            {obj_name: obj_attrs for (obj_name, obj_attrs) in self.__objects_cfg.items() \
             if obj_attrs['type'] != 'fan_control'}
        self.__utility_objects = \
            {obj_name: self.__build_utility_object(obj_attrs) for (obj_name, obj_attrs) in utility_object_cfgs.items()}

    def __build_utility_object(self, obj_attrs):
        return self.__builders[obj_attrs['type']].build(obj_attrs)

    def __build_fan_controls(self):
        fan_control_cfgs = \
            {obj_name: obj_attrs for (obj_name, obj_attrs) in self.__objects_cfg.items() \
             if obj_attrs['type'] == 'fan_control'}
        self.__fan_controls = \
            {obj_name: self.__build_fan_control(obj_attrs) for (obj_name, obj_attrs) in fan_control_cfgs.items()}

    def __build_fan_control(self, fan_control_attrs):
        fan = self.__utility_objects[fan_control_attrs['fan']]
        curve = self.__utility_objects[fan_control_attrs['curve']]
        ts = self.__utility_objects[fan_control_attrs['ts']]
        return FanControl(fan, ts, curve)
