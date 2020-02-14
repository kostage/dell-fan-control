#!/usr/bin/python


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


class HystSpeedCurve:
    def __init__(self, speeds, transitions, gap):
        self.__speeds = speeds
        self.__transitions = [HystPoint(temp, gap) for temp in transitions]
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