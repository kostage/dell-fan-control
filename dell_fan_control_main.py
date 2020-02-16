#!/usr/bin/python3


import signal
import sys
import time

from fan_control_system import FanControlSystem

DEBUG_STUBS = False

if __name__ == '__main__':
    fan_control_system = FanControlSystem('config.yml', DEBUG_STUBS)

    def fan_control_stop(sig, frame):
        fan_control_system.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, fan_control_stop)
    signal.signal(signal.SIGQUIT, fan_control_stop)
    signal.signal(signal.SIGTERM, fan_control_stop)
    signal.signal(signal.SIGHUP, fan_control_stop)

    try:
        fan_control_system.start()
        while True:
            fan_control_system.update_fan_controls()
            time.sleep(5)
    except KeyboardInterrupt:
        pass

    fan_control_stop()
