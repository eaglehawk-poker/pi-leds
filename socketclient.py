import sys
from functools import partial
from socketIO_client import SocketIO, BaseNamespace

import gevent
from gevent import monkey
monkey.patch_socket()

import control

TIME_INTERVAL = 0.5
RUNNING_LED_MODIFIER = None
spidev = file("/dev/spidev0.0", "wb")

pixel_output = partial(control.pixels_to_spi, spidev)

def start_led_function(*args):
    # Terminate any running
    global RUNNING_LED_MODIFIER
    if RUNNING_LED_MODIFIER:
        RUNNING_LED_MODIFIER.kill()
    RUNNING_LED_MODIFIER = gevent.spawn(args[0], pixel_output,
                                        lambda x: gevent.sleep(x*TIME_INTERVAL),
                                        *args[1:])


class LEDStripeSocket(BaseNamespace):

    def on_connect(self):
        print '[Connected]'

    def on_update_led_configuration(self, *args):
        print 'on update led configuration'
        data = args[0]
        with open('led_config.json', 'w') as f:
            f.write(data)
        start_led_function(control.game_mode,
                           control.json_to_player_list(data))

    def on_request_led_configuration(self, *args):
        print 'requesting led configuration'
        with open('led_config.json') as f:
            self.emit('led_configuration_from_device', f.read())

    def on_ledgame(self, *args):
        #TODO: unjoin previously joined game
        print 'joining'
        self.emit('join_game', args[0])

    def on_round_completed(self, *args):
        start_led_function(control.vegas_baby)

    def on_current_hand_update(self, *args):
        data = args[0]
        print 'on_current_hand_update:'
        active_seats = sorted(data['active_seats'])
        active_seat = data.get('active_seat', -1)
        with open('led_config.json') as f:
            # Not mutable so make new array
            player_list = control.json_to_player_list(f.read())
            player_list_updated = []

            for idx, p in enumerate(player_list):
                active = ((idx + 1) in active_seats)
                to_act = ((idx + 1) == active_seat)
                player_list_updated.append(control.Player(p.start_pixel,
                                                          p.end_pixel,
                                                          active,
                                                          to_act))
            start_led_function(control.game_mode, player_list_updated)


def listener(host, port):
    socketIO = SocketIO(host, port, LEDStripeSocket)
    socketIO.wait()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s port host" % sys.argv[0]
        exit(1)
    greenlets = [
        gevent.spawn(listener, sys.argv[1], int(sys.argv[2]))
    ]

    gevent.joinall(greenlets)
