import time
import random
import math
from collections import namedtuple
from functools import partial
import json
import sys
try:
    import termcolor
    has_term_colors = True
except:
    has_term_colors = False

Pixel = namedtuple('Pixel', ['r', 'g', 'b'])
Player = namedtuple('Player', ['start_pixel', 'end_pixel',
                               'active', 'to_act'])

TOTAL_LED_COUNT = 50
ACTIVE_LEDS = 50
GLOBAL_DIM = 1.0  # Adjust to change maximum brightness
DISTINCT_COLORS = [
    Pixel(1.0, 0.4, 0.4),
    Pixel(0.4, 1.0, 0.4),
    Pixel(0.4, 0.4, 1.0),
    Pixel(0.4, 1.0, 1.0),
]


def get_distinct_color(index):
    return DISTINCT_COLORS[index % len(DISTINCT_COLORS)]


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
    outputter = '|'
    ascii_colors = [' ', ';', 'l', '}', 'j', 'O', 'q', '$']

    for pixel in pixels:
        intensity = 0.3 * pixel.r + 0.6 * pixel.g + 0.11 * pixel.b
        ascii_idx = int(round(intensity * (len(ascii_colors) - 1)))
        color = 'grey'
        if has_term_colors:
            if pixel.r > max(pixel.g, pixel.b):
                color = 'red'
            if pixel.g > max(pixel.r, pixel.b):
                color = 'green'
            if pixel.b > max(pixel.r, pixel.g):
                color = 'blue'
            outputter += termcolor.colored(ascii_colors[ascii_idx], color)
        else:
            outputter += ascii_colors[ascii_idx]
    outputter += '|'

    sys.stdout.write("\r")
    sys.stdout.write(outputter)
    sys.stdout.flush()


def json_to_player_list(jsonstr):
    d = json.loads(jsonstr)
    players = []
    for p in d:
        players.append(Player(int(p['start_pixel']),
                              int(p['end_pixel']),
                              bool(p['active']),
                              p.get('to_act', False)))
                              
    return players


def game_mode(outputter, sleeper, players):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    i = 0
    while True:
        for color_index, player in enumerate(players):
            if not player.active:
                continue
            if player.to_act:
                length = player.end_pixel - player.start_pixel
                steps = length / 2 + (length % 2)
                for pixel_idx in range(player.start_pixel,
                                       player.end_pixel):
                    color = get_distinct_color(color_index)
                    if pixel_idx == player.start_pixel + i or\
                       pixel_idx == player.end_pixel - i - 1:
                        color = get_distinct_color(color_index)
                    elif pixel_idx == player.start_pixel + i - 1 or\
                            pixel_idx == player.end_pixel - i:
                        color = filter_pixel(color, 0.3)
                    elif pixel_idx == player.start_pixel + i - 2 or\
                            pixel_idx == player.end_pixel - i + 1:
                        color = filter_pixel(color, 0.1)
                    else:
                        color = Pixel(0.0, 0.0, 0.0)
                    pixels[pixel_idx] = color

                i += 1
                i = i % steps
            else:
                color = get_distinct_color(color_index)
                for pixel_idx in range(player.start_pixel,
                                       player.end_pixel):
                    pixels[pixel_idx] = color
        outputter(pixels)
        sleeper(2)


def winner_mode(outputter, sleeper, winner_pos):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    colors = [
        Pixel(0.4, 0.4, 1.0),
        Pixel(1.0, 0.4, 0.4),
        Pixel(0.0, 0.0, 0.0),
    ]
    i = 0

    while True:
        for i in range(ACTIVE_LEDS / 2):
            for x in range(winner_pos - i, winner_pos + i):
                if x < 0:
                    x += ACTIVE_LEDS
                x = x % ACTIVE_LEDS
                pixels[x] = colors[0]
            outputter(pixels)
            sleeper(0.1)

        for i in range(ACTIVE_LEDS / 2, 0, -1):
            pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
            for x in range(winner_pos - i, winner_pos + i):
                if x < 0:
                    x += ACTIVE_LEDS
                x = x % ACTIVE_LEDS
                pixels[x] = colors[0]
            outputter(pixels)
            sleeper(0.1)


def carousel(outputter, sleeper):
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
            outputter(pixels)
            sleeper(1)
        pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
        for a in range(1, 5):
            for b in range(0, ACTIVE_LEDS, 5):
                pixels[b + a:b + 6] = [color] * len(pixels[b + a:b + 6])

            outputter(pixels)
            pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
            sleeper(1)


def waves(outputter, sleeper):
    def f(x):
        strength = 0.2 + (0.8*((math.sin(math.pi * (x / 50.0)))**2))
        return 0.4*strength, 0.4*strength, 1.0*strength
    wave = lambda x: 0.2 + (0.8*(math.sin(math.pi * (x / 50.0))))
    rs = [wave(x) for x in range(ACTIVE_LEDS)]
    #gs = [wave(x) for x in range(ACTIVE_LEDS)]
    #bs = [wave(x) for x in range(ACTIVE_LEDS)]
    #for i in range(20):
    #    tmp = gs.pop()
    #    gs.insert(0, tmp)
    #for i in range(40):
    #    tmp = bs.pop()
    #    bs.insert(0, tmp)

    #pixels = [Pixel(r, g, b) for r, g, b in zip(rs, gs, bs)]
    #pixels = [Pixel(wave(x), 0.0, 0.0) for x in range(ACTIVE_LEDS)]
    pixels = [Pixel(*f(x)) for x in range(ACTIVE_LEDS)]
    for i in range(100):
        outputter(pixels)
        tmp = pixels.pop()
        pixels.insert(0, tmp)
        sleeper(0.4)


def vegas_baby(outputter, sleeper):
    pixels = range(ACTIVE_LEDS)
    for i in range(ACTIVE_LEDS):
        if i % 3 == 0:
            pixels[i] = Pixel(0.8, 0.2, 0.0)
        elif i % 3 == 1:
            pixels[i] = Pixel(0.0, 0.8, 0.2)
        else:
            pixels[i] = Pixel(0.0, 0.2, 0.8)
    for i in range(ACTIVE_LEDS):
        outputter(pixels)
        popper = pixels.pop()
        pixels.insert(0, popper)
        sleeper(1)


def fill_and_drain(outputter, sleeper):
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
            outputter(pixels)
            if fill_idx == ACTIVE_LEDS - 1:
                if not fill:
                    color_idx = (color_idx + 1) % len(colors)
                fill = not fill
                fill_idx = (fill_idx + 1) % ACTIVE_LEDS
                break
            fill_idx = (fill_idx + 1) % ACTIVE_LEDS
            sleeper(0.1)


def random_on_off(outputter, sleeper):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    colors = [
        Pixel(1.0, 0.4, 0.4),
        Pixel(0.4, 1.0, 0.4),
        Pixel(0.4, 0.4, 1.0),
    ]

    random.seed(time)
    PIXEL_COUNT = 40
    for _ in range(5):
        for i in range(PIXEL_COUNT):
            idx = random.randint(0, ACTIVE_LEDS - 1)
            while pixels[idx].r != 0.0:
                idx = (idx + 1) % ACTIVE_LEDS
            color_idx = random.randint(0, 2)
            pixels[idx] = colors[color_idx]
            outputter(pixels)
            sleeper(0.2)

        for i in range(PIXEL_COUNT):
            idx = random.randint(0, ACTIVE_LEDS - 1)
            while pixels[idx].r == 0.0:
                idx = (idx + 1) % ACTIVE_LEDS
            pixels[idx] = Pixel(0.0, 0.0, 0.0)
            outputter(pixels)
            sleeper(0.2)


def idle_mode(outputter, sleep):
    while True:
        #waves(outputter, sleep)
        carousel(outputter, sleep)
        fill_and_drain(outputter, sleep)
        vegas_baby(outputter, sleep)
        random_on_off(outputter, sleep)


def running_ant(outputter, sleeper):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    colors = [
        Pixel(1.0, 0.2, 0.0),
        Pixel(0.2, 0.1, 0.0),
        Pixel(0.2, 1.0, 0.0),
    ]

    while True:
        for color_index in range(6):
            for i in range(ACTIVE_LEDS):
                for j in range(ACTIVE_LEDS):
                    if j == i:
                        pixels[j] = colors[color_index % len(colors)]
                    else:
                        pixels[j] = Pixel(0.0, 0.0, 0.0)
                outputter(pixels)
                sleeper(0.1)

def love_pulse(outputter, sleeper):
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    red = Pixel(1.0, 0.0, 0.0)
    blue = Pixel(0.0, 0.0, 1.0)
    while True:
        for i in range(20):
            filter_constant = 0.2 + 0.8*math.sin((i / 19.0) * math.pi)
            red_color = filter_pixel(red, filter_constant)
            blue_color = filter_pixel(blue, 1 - filter_constant)
            for j in range(ACTIVE_LEDS):

                if j % 2 == 0:
		    pixels[j] = red_color
                else:
		    pixels[j] = blue_color
            outputter(pixels)
            sleeper(0.4)

def full_blown_hell(outputter, sleeper):
    all_red = [Pixel(1.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    all_green = [Pixel(0.0, 1.0, 0.0) for _ in range(ACTIVE_LEDS)]
    all_blue = [Pixel(0.0, 0.0, 1.0) for _ in range(ACTIVE_LEDS)]
    while True:
        outputter(all_red)
        sleeper(0.4)
        outputter(all_blue)
        sleeper(0.4)
        outputter(all_green)
        sleeper(0.4)

def sirens(outputter, sleeper):
    original_pixels = [None for _ in range(ACTIVE_LEDS)]
    pixels = [Pixel(0.0, 0.0, 0.0) for _ in range(ACTIVE_LEDS)]
    for i in range(ACTIVE_LEDS/2):
        original_pixels[i] = Pixel(1.0, 0.0, 0.0)
    for i in range(ACTIVE_LEDS/2, ACTIVE_LEDS):
        original_pixels[i] = Pixel(0.0, 0.0, 1.0)

    while True:
        for j in range(ACTIVE_LEDS):
            for i in range(ACTIVE_LEDS):
                pixels[(i + j) % ACTIVE_LEDS] = original_pixels[i]
            outputter(pixels)
            sleeper(0.05)



def test_winner_mode(outputter, sleeper):
    winner_mode(outputter, sleeper, 10)


def test_game_mode(outputter, sleeper):
    players = [
        Player(3, 8, True, False),
        Player(9, 17, True, True),
        Player(18, 23, True, False),
        Player(26, 32, True, False)
    ]
    game_mode(outputter, sleeper, players)


def filter_pixel(input_pixel, intensity):
    output_pixel = Pixel(intensity * input_pixel.r,
                         intensity * input_pixel.g,
                         intensity * input_pixel.b)
    return output_pixel


funcs = [
    idle_mode,
    random_on_off,
    fill_and_drain,
    carousel,
    test_game_mode,
    test_winner_mode,
    waves,
    running_ant,
    love_pulse,
    full_blown_hell,
    sirens
]

custom_programs = [
    running_ant,
    love_pulse,
    full_blown_hell
]


def print_usage_and_exit():
    print 'Usage: %s <program> [--console]' % sys.argv[0]
    print 'available programs:'
    print " - " + "\n - ".join(f.func_name for f in funcs)
    exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_usage_and_exit()

    func = filter(lambda f: f.func_name == sys.argv[1], funcs)
    if len(func) != 1:
        print_usage_and_exit()

    outputter = pixels_to_console
    use_console = len(sys.argv) == 3 and sys.argv[2] == '--console'
    if not use_console:
        spidev = file("/dev/spidev0.0", "wb")
        outputter = partial(pixels_to_spi, spidev)

    TIME_INTERVAL = .1
    sleeper = lambda x: time.sleep(x * TIME_INTERVAL)

    func[0](outputter, sleeper)
