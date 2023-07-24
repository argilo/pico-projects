# Copyright 2022,2023 Clayton Smith
#
# This file is part of pico-projects
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import machine
import network
import rp2
import socket
import struct
import sys
import time
import WIFI_CONFIG
from pimoroni import RGBLED
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY_2, PEN_P8

ntp_host = "pool.ntp.org"


def ntptime():
    ntp_query = bytearray(48)
    ntp_query[0] = 0x1B

    while True:
        try:
            addr = socket.getaddrinfo(ntp_host, 123)[0][-1]
            break
        except OSError:
            time.sleep(5)

    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(2)
            res = s.sendto(ntp_query, addr)
            msg = s.recv(48)
            break
        except OSError:
            time.sleep(30)
        finally:
            s.close()

    val = struct.unpack("!I", msg[40:44])[0]
    t = val - 2208988800
    tm = time.gmtime(t)
    machine.RTC().datetime((tm[0], tm[1], tm[2], 0, tm[3], tm[4], tm[5], 0))


def eastern():
    now = time.time()
    year = time.localtime(now)[0]
    mar = time.mktime((year, 3, 14 - (5 * year // 4 + 1) % 7, 7, 0, 0, 0, 0))
    nov = time.mktime((year, 11, 7 - (5 * year // 4 + 1) % 7, 6, 0, 0, 0, 0))

    if now < mar or now > nov:
        return time.localtime(now - 3600 * 5)
    else:
        return time.localtime(now - 3600 * 4)


led = RGBLED(6, 7, 8)
led.set_rgb(0, 0, 0)

display = PicoGraphics(display=DISPLAY_PICO_DISPLAY_2, pen_type=PEN_P8)
display.set_backlight(1.0)
display.clear()
display.update()

BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)

WIDTH, HEIGHT = display.get_bounds()


rp2.country(WIFI_CONFIG.COUNTRY)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

while True:
    wlan.connect(WIFI_CONFIG.SSID, WIFI_CONFIG.PSK)

    max_wait = 60
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        led.set_rgb(128, 128, 128)
        time.sleep(0.25)
        led.set_rgb(0, 0, 0)
        time.sleep(0.25)

    if wlan.status() == 3:
        break
    else:
        led.set_rgb(128, 0, 0)
        time.sleep(1)
        led.set_rgb(0, 0, 0)

ntptime()
wlan.disconnect()


months = [
    None,
    "Jan.",
    "Feb.",
    "Mar.",
    "Apr.",
    "May",
    "Jun.",
    "Jul.",
    "Aug.",
    "Sep.",
    "Oct.",
    "Nov.",
    "Dec.",
]

days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

while True:
    year, month, day, hour, minute, _, weekday, _ = eastern()
    month_str = months[month]
    weekday_str = days[weekday]

    display.set_pen(BLACK)
    display.clear()

    display.set_pen(WHITE)
    display.set_font("serif")

    display.text(weekday_str, 0, 20, WIDTH, 1.78)
    display.text(f"{month_str} {day}", 0, 97, WIDTH, 2.62)
    display.text(f"{hour:02}:{minute:02}", 0, 207, WIDTH, 3.65)

    display.update()
    time.sleep(1)
