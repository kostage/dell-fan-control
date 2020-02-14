#!/usr/bin/python


import signal
import sys
import time
import threading

from hyst_curve import HystSpeedCurve

LOW_SPEED = 0
MED_SPEED = 128
HIGH_SPEED = 255
HYSTERESIS_GAP = 5

FANS = [
    '/sys/class/hwmon/hwmon3/pwm1',
    '/sys/class/hwmon/hwmon3/pwm2'
]

TEMP_TRANSITIONS = [
    [45, 60],
    [50, 65]
]

SPEEDS = [
    LOW_SPEED,
    MED_SPEED,
    HIGH_SPEED
]

TS = '/sys/class/hwmon/hwmon1/temp1_input'


class AveragingFilter:
    def __init__(self, order, init_value=0):
        self.__order = order
        self.__cyclic_buf = [float(init_value) / order for i in range(order)]
        self.__cbuf_tail = 0  # oldest
        self.__cbuf_head = order - 1  # newest
        self.__filtered_value = sum(self.__cyclic_buf)

    def __cbuf_pop_tail(self):
        oldest_value = self.__cyclic_buf[self.__cbuf_tail]
        self.__cbuf_tail = self.__advance_cbuf_pos(self.__cbuf_tail)
        return oldest_value

    def __cbuf_push_head(self, value):
        self.__cbuf_head = self.__advance_cbuf_pos(self.__cbuf_head)
        self.__cyclic_buf[self.__cbuf_head] = value

    def __advance_cbuf_pos(self, pos):
        return (pos + 1) % self.__order

    def update_value(self, value):
        averaged_value = float(value) / self.__order
        oldest_value = self.__cbuf_pop_tail()
        self.__cbuf_push_head(averaged_value)
        self.__filtered_value = self.__filtered_value + averaged_value - oldest_value

    def filter_value(self, value):
        self.update_value(value)
        return self.filtered_value

    @property
    def filtered_value(self):
        return self.__filtered_value


class FilteredTempSensor:
    def __init__(self, file_name_str, filter_order):
        self.__file_name_str = file_name_str
        temp = self.__read_temp_from_file()
        self.__filter = AveragingFilter(filter_order, temp)

    def __read_temp_from_file(self):
        file = open(self.__file_name_str)
        str_temp_value = file.readline()
        return float(str_temp_value) / 1000

    def get_filtered_temp(self):
        temp = self.__read_temp_from_file()
        return self.__filter.filter_value(temp)


class ThreadedTS(threading.Thread):
    def __init__(self, ts_file_name):
        threading.Thread.__init__(self)
        self.__filtered_ts = FilteredTempSensor(ts_file_name, 8)
        self.__filtered_temp = self.__filtered_ts.get_filtered_temp()
        self.__stop_flag = False

    def run(self):
        while not self.__stop_flag:
            new_temp = self.__filtered_ts.get_filtered_temp()
            self.__filtered_temp = new_temp
            time.sleep(1)

    def stop(self):
        self.__stop_flag = True
        self.join()

    def __del__(self):
        self.stop()

    @property
    def temp(self):
        return self.__filtered_temp


class Fan:
    def __init__(self, fan_file_name):
        self.__fan_file_name = fan_file_name

    def set_fan_speed(self, float_speed):
        file = open(self.__fan_file_name, 'w')
        file.write(str(float_speed))


class FanControl:
    def __init__(self, fan, ts, hyst_curve):
        self.__fan = fan
        self.__ts = ts
        self.__fan_speed_calc = hyst_curve

    def update_fan_speed_according_to_temp(self):
        temp = self.__ts.temp
        # print 'temp', temp
        fan_speed = self.__fan_speed_calc.calculate_speed(temp)
        # print 'speed', fan_speed
        self.__fan.set_fan_speed(fan_speed)

    def set_max_speed(self):
        max_speed = self.__fan_speed_calc.calculate_speed(100.0)
        self.__fan.set_fan_speed(max_speed)


if __name__ == '__main__':
    ts = ThreadedTS('/sys/class/hwmon/hwmon1/temp1_input')
    fans = [Fan(fan_file) for fan_file in FANS]
    curves = [HystSpeedCurve(SPEEDS, transition, HYSTERESIS_GAP) for transition in TEMP_TRANSITIONS]
    fan_controls = [FanControl(fan, ts, curves[idx]) for idx, fan in enumerate(fans)]

    def fan_control_stop(sig, frame):
        ts.stop()
        for fan_control in fan_controls:
            fan_control.set_max_speed()
        sys.exit(0)

    signal.signal(signal.SIGINT, fan_control_stop)
    signal.signal(signal.SIGQUIT, fan_control_stop)
    signal.signal(signal.SIGTERM, fan_control_stop)
    signal.signal(signal.SIGHUP, fan_control_stop)
    try:
        ts.start()
        while True:
            for fan_control in fan_controls:
                fan_control.update_fan_speed_according_to_temp()
            time.sleep(5)
    except KeyboardInterrupt:
        pass

    fan_control_stop()
