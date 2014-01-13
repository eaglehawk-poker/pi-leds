import time
from collections import namedtuple
import json
import sys

Pixel = namedtuple('Pixel', ['r', 'g', 'b'])
Player = namedtuple('Player', ['start_pixel', 'end_pixel', 'active', 'to_act'])

# color constants
RED = Pixel(255, 0, 0)
GREEN = Pixel(0, 255, 0)
BLUE = Pixel(0, 0, 255)

LED_COUNT = 51


def send_pixels(device, pixels):
    pixel_out_bytes = bytearray(2)
    device.write(bytearray(b'\x00\x00'))

    for pixel in pixels:
        # 5 bit per color
        scaled_r = int(round(pixel.r * 31.0))
        scaled_g = int(round(pixel.g * 31.0))
        scaled_b = int(round(pixel.b * 31.0))

        pixel_out = 0b1000000000000000  # bit 16 must be ON
        pixel_out |= (scaled_r) << 10  # RED is bits 11-15
        pixel_out |= (scaled_g) << 5  # GREEN is bits 6-10
        pixel_out |= (scaled_b)  # BLUE is bits 1-5

        pixel_out_bytes[0] = (pixel_out & 0xFF00) >> 8
        pixel_out_bytes[1] = (pixel_out & 0x00FF) >> 0
        device.write(pixel_out_bytes)
    device.flush()


def json_to_player_list(jsonstr):
    d = json.loads(jsonstr)
    players = []
    for p in d:
        players.append(Player(p['start_pixel'],
                              p['end_pixel'],
                              p['active'],
                              p.get('to_act', False)))
    return players


def color_test(spidev):
    while True:
        print 'Setting red'
        pixels = [Pixel(1.0, 0.0, 0.0) for _ in range(LED_COUNT)]
        print len(pixels)
        send_pixels(spidev, pixels)
        raw_input()
        print 'Setting green'
        pixels = [Pixel(0.0, 1.0, 0.0) for _ in range(LED_COUNT)]
        send_pixels(spidev, pixels)
        raw_input()
        print 'Setting blue'
        pixels = [Pixel(0.0, 0.0, 1.0) for _ in range(LED_COUNT)]
        send_pixels(spidev, pixels)
        time.sleep(3)


def vegas_baby(spidev):
    pixels = range(LED_COUNT)
    for i in range(LED_COUNT):
        if i % 3 == 0:
            pixels[i] = Pixel(8.0, 2.0, 0.0)
        elif i % 3 == 1:
            pixels[i] = Pixel(0.0, 8.0, 2.0)
        else:
            pixels[i] = Pixel(0.0, 2.0, 8.0)
    while True:
        send_pixels(spidev, pixels)
        popper = pixels.pop()
        pixels.insert(0, popper)
        time.sleep(0.1)


def game_mode(spidev, players, on):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(LED_COUNT)]
    player_colors = [
        Pixel(0.8, 0.8, 0.4),
        Pixel(0.8, 0.0, 0.8),
        Pixel(0.8, 4.0, 0.8),
        Pixel(0.1, 1.0, 0.0),
        Pixel(0.4, 8.0, 8.0)
    ]

    for color_idx, player in enumerate(players):
        if player.active:
            color = player_colors[color_idx]
            if player.to_act and not on:
                color = Pixel(0.0, 0.0, 0.0)

            for pixel_idx in range(player.start_pixel, player.end_pixel):
                pixels[pixel_idx] = color

    send_pixels(spidev, pixels)


def test_game_mode(spidev):
    players = [
        Player(3, 8, True, False),
        Player(9, 16, True, False),
        Player(18, 23, True, True),
        Player(26, 32, True, False)
    ]
    game_mode(spidev, players)


def filter_pixel(input_pixel, intensity):
    output_pixel = Pixel(intensity * input_pixel.r,
                         intensity * input_pixel.g,
                         intensity * input_pixel.b)
    return output_pixel

if __name__ == '__main__':
    spidev = file("/dev/spidev0.0", "wb")
    #test_game_mode()
    #vegas_baby()
    with open(sys.argv[1]) as f:
        players = json_to_player_list(f.read())
        on = True
        while True:
            game_mode(spidev, players, on)
            on = not on
            time.sleep(0.5)
