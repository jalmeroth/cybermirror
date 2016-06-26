#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import time
import homie
import logging
import RPi.GPIO as GPIO
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_INTERVAL = 60
IDLE_INTERVAL = 45

Homie = homie.Homie("range_sensor.json")
temperatureNode = Homie.Node("temperature", "temperature")
switchNode = Homie.Node("switch", "switch")

# define GPIO pins
GPIOEcho = 11
GPIORelais1 = 16
GPIORelais2 = 18
GPIOTrigger = 13

OVERRULED = False


# function to measure the distance
def measureDistance():
    # set trigger to high
    GPIO.output(GPIOTrigger, True)

    # set trigger after 10µs to low
    time.sleep(0.00001)
    GPIO.output(GPIOTrigger, False)

    # store initial start time
    StartTime = time.time()

    # store start time
    while GPIO.input(GPIOEcho) == 0:
        StartTime = time.time()

    # store stop time
    while GPIO.input(GPIOEcho) == 1:
        StopTime = time.time()

    # calculate distance
    TimeElapsed = StopTime - StartTime
    distance = (TimeElapsed * 34300) / 2

    return distance


def measureDistanceAvg():
    distance = measureDistance()
    time.sleep(0.1)
    distance += measureDistance()
    time.sleep(0.1)
    distance += measureDistance()
    return (distance / 3)


def toggleRelay(state):
    global OVERRULED
    if OVERRULED:
        logger.debug("OVERRULED: Doing nothing")
        return

    # turn on
    if state:
        # display not already turned on
        if not GPIO.input(GPIORelais1):
            logger.info("Display einschalten")
            GPIO.output(GPIORelais1, True)
            GPIO.output(GPIORelais2, True)
            Homie.setNodeProperty(switchNode, "on", "true", True)
        else:
            logger.debug("Display on already")
    # turn off
    else:
        # display not already turned off
        if GPIO.input(GPIORelais1):
            logger.info("Display ausschalten")
            GPIO.output(GPIORelais1, False)
            GPIO.output(GPIORelais2, False)
            Homie.setNodeProperty(switchNode, "on", "false", True)
        else:
            logger.debug("Display off already")


def switchOnHandler(mqttc, obj, msg):
    global OVERRULED
    logger.debug("OVERRULED: {}".format(OVERRULED))
    payload = msg.payload.decode("UTF-8").lower()
    if payload == 'true':
        logger.info("Switch: ON")
        toggleRelay(True)
        OVERRULED = True
    else:
        logger.info("Switch: OFF")
        OVERRULED = False
        toggleRelay(False)


def getCpuTemperature():
    tempFile = open("/sys/class/thermal/thermal_zone0/temp")
    cpu_temp = tempFile.read()
    tempFile.close()
    return (float(cpu_temp) / 1000)


def updateCpuTemp():
    temperature = "{:0.2f}".format(getCpuTemperature())
    logger.info("Temperature: {} °C".format(temperature))
    Homie.setNodeProperty(temperatureNode, "degrees", temperature, True)


def main():
    Homie.setFirmware("awesome-temperature", "1.0.0")
    Homie.subscribe(switchNode, "on", switchOnHandler)
    updateCpuTemp()
    Homie.Timer(TEMP_INTERVAL, updateCpuTemp).start()

    counter = 0
    start = time.time()

    while True:
        distance = measureDistanceAvg()

        # begin action
        if distance < 90 or distance > 800:
            logger.debug("Target in %.1f cm" % distance)
            # count positive measurements
            counter += 1
            # second positive measurement yet?
            if counter > 1:
                # activate display
                toggleRelay(True)
        else:
            logger.debug("Measured distance = %.1f cm" % distance)
            # when someone was in front of mirror
            if counter > 1:
                logger.debug("Starting idle timer")
                start = time.time()
            # reset measurements
            counter = 0
            # calculate idle time
            now = time.time()
            idle = (now - start)
            logger.debug("Idle since: {:.1f}".format(idle))

            # display on and idle since X
            if idle > IDLE_INTERVAL:
                toggleRelay(False)
        # end action

        time.sleep(1)

if __name__ == '__main__':
    # use GPIO pin numbering convention
    GPIO.setmode(GPIO.BOARD)

    # set up GPIO pins
    GPIO.setup(GPIOEcho, GPIO.IN)
    GPIO.setup(GPIORelais1, GPIO.OUT)
    GPIO.setup(GPIORelais2, GPIO.OUT)
    GPIO.setup(GPIOTrigger, GPIO.OUT)

    # set output PINs to false
    GPIO.output(GPIOTrigger, False)
    GPIO.output(GPIORelais1, False)
    GPIO.output(GPIORelais2, False)

    # call main function
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Quitting.")
        GPIO.cleanup()
