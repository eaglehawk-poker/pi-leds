import sys
from socketIO_client import SocketIO

import gevent
from gevent import monkey
monkey.patch_socket()

import control

RUNNING_LED_MODIFIER = None
#spidev = file("/dev/spidev0.0", "wb")


def handle(msg):
    with open('led_config.json', 'w') as f:
        f.write(msg)

    print 'handle msg: ', msg
    #player_list = control.json_to_player_list(msg)
    #control.game_mode(spidev, player_list, on=True)


def on_player_update(*args):
    print 'player_update'


def on_current_hand_update(*args):
    print 'on_current_hand_update'
    print 'args: ', args

def on_leds(*args):
    global RUNNING_LED_MODIFIER
    if RUNNING_LED_MODIFIER:
        RUNNING_LED_MODIFIER.kill()
    RUNNING_LED_MODIFIER = gevent.spawn(handle, args[0])


def listener(host, port):
    with SocketIO(host, port) as socketIO:
        print 'connected, emitting join_game'
        #socketIO.emit('join_game', {'game_id': '5257aa9575035d1f14000005'})
        socketIO.on('led_update', on_led_update)
        socketIO.on('player_update', on_player_update)
        socketIO.on('current_hand_update', on_current_hand_update)
        print 'waiting'
        #socketIO.on('request_led_conf', send_led_conf)
        socketIO.wait()
    print 'Done'


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Usage: %s port host" % sys.argv[0]
        exit(1)
    greenlets = [
        gevent.spawn(listener, sys.argv[1], int(sys.argv[2]))
    ]

    gevent.joinall(greenlets)
