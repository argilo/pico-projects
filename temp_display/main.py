import machine
import network
import picographics
import rp2
import time
import CONFIG
from umqtt.simple import MQTTClient

rp2.country(CONFIG.COUNTRY)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

while True:
    wlan.connect(CONFIG.SSID, CONFIG.PSK)

    max_wait = 60
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        time.sleep(0.5)

    if wlan.status() == 3:
        break
    else:
        time.sleep(1)

data = {}
door_status = b"closed"


def on_message(topic, msg):
    global door_status

    _, sensor_type, device_name, data_type = topic.split(b"/")
    if sensor_type == b"sensor":
        if device_name.startswith(b"h5075_"):
            device_id = device_name[6:10]
            device_type = device_name[11:]
            if device_id not in data:
                data[device_id] = ["", 0, 0]

            if data_type == b"friendly_name":
                if device_type == b"temperature":
                    data[device_id][0] = msg[1:-13].decode()
            elif data_type == b"state":
                if msg != b"unavailable":
                    if device_type == b"temperature":
                        data[device_id][1] = float(msg)
                    elif device_type == b"humidity":
                        data[device_id][2] = float(msg)
    elif sensor_type == b"cover":
        door_status = msg


graphics = picographics.PicoGraphics(picographics.DISPLAY_INKY_PACK)
graphics.set_update_speed(2)
graphics.set_font("sans")
graphics.set_thickness(2)
graphics.set_pen(15)
graphics.clear()
graphics.set_pen(0)
graphics.update()


def display(data):
    text_size = 0.7
    graphics.set_pen(15 if door_status == b"closed" else 0)
    graphics.clear()
    graphics.set_pen(0 if door_status == b"closed" else 15)
    for i, (_, (name, temp, hum)) in enumerate(sorted(data.items(), key=lambda x: CONFIG.ORDER.get(x[0], 100))):
        y = 9 + 22*i
        graphics.text(name, 5, y, scale=text_size)

        text = f"{temp:5.1f}"
        width = graphics.measure_text(text, scale=text_size)
        graphics.text(text, 230-width, y, scale=text_size)

        text = f"{int(hum):02}%"
        width = graphics.measure_text(text, scale=text_size)
        graphics.text(text, 295-width, y, scale=text_size)

    graphics.update()


client = MQTTClient(machine.unique_id().hex(), CONFIG.SERVER, CONFIG.PORT, CONFIG.USERNAME, CONFIG.PASSWORD)
client.set_callback(on_message)

while True:
    try:
        client.connect()

        client.subscribe("homeassistant/sensor/+/state")
        client.subscribe("homeassistant/sensor/+/friendly_name")
        client.subscribe("homeassistant/cover/garagedoor_door/state")

        last_update = time.time() - CONFIG.UPDATE_PERIOD + 1
        while True:
            client.check_msg()
            if time.time() - last_update >= CONFIG.UPDATE_PERIOD:
                last_update = time.time()
                display(data)
    except OSError as e:
        pass
