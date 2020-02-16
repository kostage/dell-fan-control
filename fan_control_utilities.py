#!/usr/bin/python3


import signal
import sys
import time
import threading


class FanControlObject:
    def get_json_state(self):
        return 'Not Implemented'


class FanBase(FanControlObject):
    def set_fan_speed(self, speed):
        print('Not implemented')


class TempSensorBase(FanControlObject):
    def get_temp(self):
        return Nan

    def start(self):
        pass

    def stop(self):
        pass


class HystCurveBase(FanControlObject):
    def calculate_speed(self, temp):
        return Nan


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
        return self.get_filtered_value()

    def get_filtered_value(self):
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


class TempSensorStub(TempSensorBase):
    def __init__(self, ts_file_name, filter_order, period):
        self.__ts_file_name = ts_file_name
        print('TempSensorStub for', ts_file_name, 'with filter order = ', filter_order, ', period = ', period)

    def start(self):
        print('TempSensorStub for', self.__ts_file_name, 'started')

    def stop(self):
        print('TempSensorStub for', self.__ts_file_name, 'stopped')

    def __del__(self):
        self.stop()

    def get_temp(self):
        return 0


class ThreadedTS(TempSensorBase):
    def __init__(self, ts_file_name, filter_order, period):
        self.__thread = threading.Thread(target=self.__thread_func)
        self.__filtered_ts = FilteredTempSensor(ts_file_name, filter_order)
        self.__filtered_temp = self.__filtered_ts.get_filtered_temp()
        self.__period = period
        self.__stop_flag = False

    def __thread_func(self):
        while not self.__stop_flag:
            new_temp = self.__filtered_ts.get_filtered_temp()
            self.__filtered_temp = new_temp
            time.sleep(self.__period)

    def start(self):
        self.__stop_flag = False
        if not self.__thread.is_alive():
            self.__thread.start()

    def stop(self):
        self.__stop_flag = True
        if self.__thread.is_alive():
            self.__thread.join()

    def __del__(self):
        self.stop()

    def get_temp(self):
        return self.__filtered_temp


class FanStub(FanBase):
    def __init__(self, fan_file_name):
        self.__fan_file_name = fan_file_name
        print('FanStub for', fan_file_name, 'created')

    def set_fan_speed(self, speed):
        print('set', self.__fan_file_name, 'to speed', speed)


class Fan(FanBase):
    def __init__(self, fan_file_name):
        self.__fan_file_name = fan_file_name

    def set_fan_speed(self, speed):
        file = open(self.__fan_file_name, 'w')
        file.write(str(speed))


class HystPoint:
    HIGH_STATE = 0
    LOW_STATE = 1

    def __init__(self, value, gap):
        self.__value = value
        self.__gap = gap
        self.__state = HystPoint.HIGH_STATE

    def set_state(self, state):
        self.__state = state

    @property
    def value(self):
        return self.__value if self.__state == HystPoint.HIGH_STATE else self.__value - self.__gap


class HystSpeedCurve(HystCurveBase):
    def __init__(self, speeds, transitions, hyst_gap):
        self.__speeds = speeds
        self.__transitions = [HystPoint(temp, hyst_gap) for temp in transitions]
        self.__cur_speed = speeds[0]

    def calculate_speed(self, temp):
        zone_index = self.__calc_temp_zone(temp)
        speed = self.__speeds[zone_index]
        if speed != self.__cur_speed:
            self.__cur_speed = speed
            self.__update_transitions(zone_index)
        return speed

    def __calc_temp_zone(self, temp):
        index = 0
        for transition in self.__transitions:
            if transition.value > temp:
                break
            index += 1
        return index

    def __update_transitions(self, zone_index):
        [t.set_state(HystPoint.LOW_STATE) for t in self.__transitions[0:zone_index]]
        [t.set_state(HystPoint.HIGH_STATE) for t in self.__transitions[zone_index:]]


class HystSpeedCurveStub(HystSpeedCurve):
    def __init__(self, speeds, transitions, hyst_gap):
        super().__init__(speeds, transitions, hyst_gap)
        print('created hystcurve, speeds:', speeds, 'transitions:', transitions, 'gap:', hyst_gap)

    def calculate_speed(self, temp):
        speed = super().calculate_speed(temp)
        print('temp', temp, '-> speed', speed)
        return speed


class FanControl:
    def __init__(self, fan, ts, hyst_curve):
        self.__fan = fan
        self.__ts = ts
        self.__fan_speed_calc = hyst_curve

    def start(self):
        self.__ts.start()

    def update_fan_speed_according_to_temp(self):
        temp = self.__ts.get_temp()
        # print 'temp', temp
        fan_speed = self.__fan_speed_calc.calculate_speed(temp)
        # print 'speed', fan_speed
        self.__fan.set_fan_speed(fan_speed)

    def stop_and_set_max_speed(self):
        self.__ts.stop()
        max_speed = self.__fan_speed_calc.calculate_speed(100.0)
        self.__fan.set_fan_speed(max_speed)


if __name__ == '__main__':
    LOW_SPEED = 0
    MED_SPEED = 128
    HIGH_SPEED = 255
    HYSTERESIS_GAP = 5

    curve = HystSpeedCurve([LOW_SPEED, MED_SPEED, HIGH_SPEED], [50, 60], HYSTERESIS_GAP)

    temps = [49, 60, 55, 49, 59, 60, 59, 44]
    print([curve.calculate_speed(temp) for temp in temps])

    temps = [61, 55, 54, 50, 49, 45, 44 ,43]
    print([curve.calculate_speed(temp) for temp in temps])