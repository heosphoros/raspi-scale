#!/usr/bin/env python
import time
import datetime
import os
import RPi.GPIO as GPIO
import scaleConfig
'''
This is mostly from:
https://learn.adafruit.com/
   reading-a-analog-in-and-controlling-audio-volume-with-the-raspberry-pi/
   script

(git://gist.github.com/3151375.git)

With some modifications by me that should have been other
commits, but weren't, so sorry, you'll have to diff it yourself
if you want to see what changed.

I have no idea what the license is on the original, so I have no
idea what the license on this is.  Personally, I don't care, but
Adafruit might.
'''

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
        if ((adcnum > 7) or (adcnum < 0)):
                return -1
        GPIO.output(cspin, True)

        GPIO.output(clockpin, False)  # start clock low
        GPIO.output(cspin, False)     # bring CS low

        commandout = adcnum
        commandout |= 0x18  # start bit + single-ended bit
        commandout <<= 3    # we only need to send 5 bits here
        for i in range(5):
                if (commandout & 0x80):
                        GPIO.output(mosipin, True)
                else:
                        GPIO.output(mosipin, False)
                commandout <<= 1
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)

        adcout = 0
        # read in one empty bit, one null bit and 10 ADC bits
        for i in range(12):
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)
                adcout <<= 1
                if (GPIO.input(misopin)):
                        adcout |= 0x1

        GPIO.output(cspin, True)

        adcout >>= 1       # first bit is 'null' so drop it
        return adcout


configFile = './scaleConfig.yaml'
cfg = readConfig(configFile)
plotlyConfigFile = './plotlyCreds.sec'

try:
        f = open(plotlyConfigFile)
except:
        print "=========================== ERROR ==========================="
        print "I couldn't open the file '{0}'".format(plotlyConfigFile)
        print "to read the plot.ly settings, so I can't make a plot and"
        print "am giving up."
        print "(I am:", os.path.abspath(os.path.dirname(sys.argv[0]))+"/"+sys.argv[0],")"
        print "=========================== ERROR ==========================="
        exit (1)

plotlyConfig = yaml.safe_load(f)
f.close()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False) # to stop the "This channel is already in use" warning

# change these as desired - they're the pins connected from the
# SPI port on the ADC to the Cobbler
# ADCPort    Cobbler
# -------- ----------
SPICLK    =    18
SPIMISO   =    23
SPIMOSI   =    24
SPICS     =    25
# -------------------
SPICLK    =    cfg['raspberryPiConfig']['ADCtoCobbler']['SPICLK']
SPIMISO   =    cfg['raspberryPiConfig']['ADCtoCobbler']['SPIMISO']
SPIMOSI   =    cfg['raspberryPiConfig']['ADCtoCobbler']['SPIMOSI']
SPICS     =    cfg['raspberryPiConfig']['ADCtoCobbler']['SPICS']
# Diagram of ADC (MCP3008) is at:
#   https://learn.adafruit.com/
#     reading-a-analog-in-and-controlling-audio-volume-with-the-raspberry-pi/
#     connecting-the-cobbler-to-a-mcp3008

# set up the SPI interface pins
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)

DEBUG = 1
DEBUG = cfg['raspberryPiConfig']['debug']

# FSR connected to adc #0
fsr_adc = 0;
fsr_adc = cfg['raspberryPiConfig']['adcPortWithFSR']

last_read = 0       # this keeps track of the last FSR value
tolerance = 4.5     # to keep from being jittery we'll only change
                    # when the FSR has moved more than this many 'counts'
tolerance = cfg['raspberryPiConfig']['tolerance']


while True:
        # we'll assume that the fsr reading didn't change
        fsr_changed = False

        # read the analog pin
        fsr = readadc(fsr_adc, SPICLK, SPIMOSI, SPIMISO, SPICS)
        # how much has it changed since the last read?
        fsr_change = (fsr - last_read)

        if fsr_change > cfg['raspberryPiConfig']['maxChange']:
                if ( abs(fsr_change) > tolerance ):
                        fsr_changed = True
                        last_read = fsr
                        if DEBUG:
                                print '{0}\tfsr: {1:4d}\tlast_value: {2:4d}\tchange: {3:4d}'.format(datetime.datetime.now(),
                                                                                                    fsr,
                                                                                                    last_read,
                                                                                                    fsr_change)
                        beans = int(fsr/1024)
                        updatePlot (datetime.datetime.now(),
                                    beans,
                                    plotlyConfig['username'],
                                    plotlyConfig['apikey'])

        time.sleep(cfg['raspberryPiConfig']['checkTime'])
