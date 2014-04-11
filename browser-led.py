from functools import partial
import gevent
import json

from flask import Flask, render_template
from flask_sockets import Sockets

from control import (idle_mode, random_on_off, fill_and_drain,
                     carousel, test_game_mode, test_winner_mode,
                     waves, vegas_baby)

app = Flask(__name__)
sockets = Sockets(app)


def websocket_output(ws, pixels):
    color_array = []
    for p in pixels:
        color_array.append(p.r)
        color_array.append(p.g)
        color_array.append(p.b)
    resp = {
        'type': 'led_update',
        'data': color_array
    }
    ws.send(json.dumps(resp))
    #ws.send(json.dumps(color_array))

PROGRAMS = [
    idle_mode,
    random_on_off,
    fill_and_drain,
    carousel,
    test_game_mode,
    test_winner_mode,
    waves,
    vegas_baby
]


def start_led_program(program, outputter, prev_program=None):
    if prev_program:
        prev_program.kill()
    return gevent.spawn(program,
                        outputter,
                        lambda x: gevent.sleep(0.1 * x))


@sockets.route('/led')
def led_socket(ws):
    outputter = partial(websocket_output, ws)
    #idle_mode(outputter, lambda x: gevent.sleep(0.1*x))
    #waves(outputter, lambda x: gevent.sleep(0.1*x))
    running_program = start_led_program(idle_mode, outputter)

    p_names = [p.func_name for p in PROGRAMS]
    resp = {
        'type': 'list_programs',
        'data': p_names
    }
    ws.send(json.dumps(resp))

    while True:
        msg = json.loads(ws.receive())
        print msg
        if msg['type'] == 'set_program':
            programs = filter(lambda p: p.func_name == msg['program_name'],
                              PROGRAMS)
            if len(programs) == 1:
                running_program = start_led_program(programs[0],
                                                    outputter,
                                                    running_program)


@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
