import time
from collections import namedtuple
from functools import partial
import json
from sys import stdout

Pixel = namedtuple('Pixel', ['r', 'g', 'b'])
Player = namedtuple('Player', ['start_pixel', 'end_pixel', 'active', 'to_act'])

TOTAL_LED_COUNT = 50
ACTIVE_LEDS = 50
GLOBAL_DIM = 1.0  # Adjust to change maximum brightness


def pixels_to_spi(device, pixels):
    pixel_out_bytes = bytearray(2)
    device.write(bytearray(b'\x00\x00'))

    for pixel in pixels:
        # 5 bit per color
        dimmed_pixel = filter_pixel(pixel, GLOBAL_DIM)
        scaled_r = int(round(dimmed_pixel.r * 31.0))
        scaled_g = int(round(dimmed_pixel.g * 31.0))
        scaled_b = int(round(dimmed_pixel.b * 31.0))

        pixel_out = 0b1000000000000000  # bit 16 must be ON
        pixel_out |= (scaled_b) << 10  # BLUE is bits 11-15
        pixel_out |= (scaled_r) << 5  # RED is bits 6-10
        pixel_out |= (scaled_g)  # GREEN is bits 1-5

        pixel_out_bytes[0] = (pixel_out & 0xFF00) >> 8
        pixel_out_bytes[1] = (pixel_out & 0x00FF) >> 0
        device.write(pixel_out_bytes)
    # Need to write to more here for some reason
    device.write(pixel_out_bytes)
    device.write(pixel_out_bytes)
    device.flush()


def pixels_to_console(pixels):
    output = '|'
    ascii_colors = [' ', ';', 'l', '}', 'j', 'O', 'q', '$']

    for pixel in pixels:
        intensity = 0.3 * pixel.r + 0.6 * pixel.g + 0.11 * pixel.b
        ascii_idx = int(round(intensity * (len(ascii_colors) - 1)))
        output += ascii_colors[ascii_idx]
    output += '|'

    stdout.write("\r")
    stdout.write(output)
    stdout.flush()


def json_to_player_list(jsonstr):
    d = json.loads(jsonstr)
    players = []
    for p in d:
        players.append(Player(int(p['start_pixel']),
                              int(p['end_pixel']),
                              bool(p['active']),
                              p.get('to_act', False)))
    return players


def game_mode(output, sleeper, players):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    player_colors = [
        Pixel(0.8, 0.8, 0.4),
        Pixel(0.8, 0.0, 0.8),
        Pixel(0.8, 0.4, 0.8),
        Pixel(0.1, 1.0, 0.0),
        Pixel(0.4, 0.8, 0.8),
        Pixel(0.4, 0.0, 0.8),
        Pixel(1.0, 0.3, 0.9),
        Pixel(0.2, 0.8, 0.9)
    ]

    i = 0
    while True:
        for color_idx, player in enumerate(players):
            if player.active:
                if player.to_act:
                    length = player.end_pixel - player.start_pixel
                    steps = length / 2 + (length % 2)
                    for pixel_idx in range(player.start_pixel,
                                           player.end_pixel):
                        if pixel_idx == player.start_pixel + i or\
                           pixel_idx == player.end_pixel - i - 1:
                            color = player_colors[color_idx]
                        else:
                            color = Pixel(0.0, 0.0, 0.0)
                        pixels[pixel_idx] = color

                    i += 1
                    i = i % steps
                else:
                    color = player_colors[color_idx]
                    for pixel_idx in range(player.start_pixel,
                                           player.end_pixel):
                        pixels[pixel_idx] = color
        output(pixels)
        sleeper(2)


def carousel(output, sleeper):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    colors = [
        Pixel(1.0, 0.2, 0.8),
        Pixel(0.4, 1.0, 0.0),
        Pixel(0.0, 0.0, 1.0),
        Pixel(1.0, 0.3, 0.3),
        Pixel(0.3, 1.0, 0.3),
    ]
    for _ in range(2 * len(colors)):
        color = colors[_ % len(colors)]
        for a in range(6):
            for b in range(0, ACTIVE_LEDS, 5):
                pixels[b:b + a] = [color for _ in range(a)]
            output(pixels)
            sleeper(1)
        pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
        for a in range(1, 5):
            for b in range(0, ACTIVE_LEDS, 5):
                pixels[b + a:b + 6] = [color for _ in range(5 - a)]
            output(pixels)
            pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
            sleeper(1)


def vegas_baby(output, sleeper):
    pixels = range(ACTIVE_LEDS)
    for i in range(ACTIVE_LEDS):
        if i % 3 == 0:
            pixels[i] = Pixel(0.8, 0.2, 0.0)
        elif i % 3 == 1:
            pixels[i] = Pixel(0.0, 0.8, 0.2)
        else:
            pixels[i] = Pixel(0.0, 0.2, 0.8)
    for i in range(ACTIVE_LEDS):
        output(pixels)
        popper = pixels.pop()
        pixels.insert(0, popper)
        sleeper(1)


def fill_and_drain(output, sleeper):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    colors = [
        Pixel(1.0, 0.4, 0.4),
        Pixel(0.4, 1.0, 0.4),
        Pixel(0.4, 0.4, 1.0),
    ]
    color_idx = 0
    fill_idx = 0
    fill = True
    for _ in range(6):
        while True:
            if fill:
                for i in range(0, fill_idx):
                    pixels[i] = colors[color_idx]
                for i in range(fill_idx, ACTIVE_LEDS):
                    pixels[i] = Pixel(0.0, 0.0, 0.0)
            else:  # Empty
                for i in range(0, fill_idx):
                    pixels[i] = Pixel(0.0, 0.0, 0.0)
                for i in range(fill_idx, ACTIVE_LEDS):
                    pixels[i] = colors[color_idx]
            output(pixels)
            if fill_idx == ACTIVE_LEDS - 1:
                if not fill:
                    color_idx = (color_idx + 1) % len(colors)
                fill = not fill
                fill_idx = (fill_idx + 1) % ACTIVE_LEDS
                break
            fill_idx = (fill_idx + 1) % ACTIVE_LEDS
            sleeper(0.1)


def idle_mode(output, sleep):
    while True:
        carousel(output, sleep)
        fill_and_drain(output, sleep)
        vegas_baby(output, sleep)


def test_game_mode(output, sleeper):
    players = [
        Player(3, 8, True, False),
        Player(9, 17, True, True),
        Player(18, 23, True, False),
        Player(26, 32, True, False)
    ]
    game_mode(output, sleeper, players)


def color_test(output, sleeper):
    while True:
        pixels = [Pixel(1.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
        print 'red'
        output(pixels)
        raw_input()
        pixels = [Pixel(0.0, 1.0, 0.0) for _ in range(ACTIVE_LEDS)]
        print 'green'
        output(pixels)
        raw_input()
        pixels = [Pixel(0.0, 0.0, 1.0) for _ in range(ACTIVE_LEDS)]
        print 'blue'
        output(pixels)
        raw_input()


def count_down_test(output, sleeper):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    output(pixels)
    pixels[0] = Pixel(1.0, 0.0, 0.0)
    pixels[49] = Pixel(1.0, 0.0, 0.0)
    output(pixels)
    for i in range(ACTIVE_LEDS):
        raw_input()
        pixels[0:i + 1] = [Pixel(0.0, 1.0, 0.0) for _ in range(i + 1)]
        output(pixels)


def filter_pixel(input_pixel, intensity):
    output_pixel = Pixel(intensity * input_pixel.r,
                         intensity * input_pixel.g,
                         intensity * input_pixel.b)
    return output_pixel

if __name__ == '__main__':
    spidev = file("/dev/spidev0.0", "wb")
    spi = partial(pixels_to_spi, spidev)
    TIME_INTERVAL = .1
    sleeper = lambda x: time.sleep(x * TIME_INTERVAL)
    #fill_and_drain(pixels_to_console, sleeper)
    #vegas_baby(pixels_to_console, sleeper)
    #test_game_mode(spi, sleeper)
    #color_test(spi, sleeper)
    idle_mode(spi, sleeper)
    #count_down_test(spi, sleeper)
