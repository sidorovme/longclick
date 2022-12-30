from flask import Flask, request, Response
import yaml
import requests
import urllib.parse
import threading
import atexit
import time

with open("settings.yaml", "r") as stream:
    try:
        settings = yaml.safe_load(stream)
        print(settings)
    except yaml.YAMLError as exc:
        print(exc)

POOL_TIME = settings['timings']['pool_time']

#states = [None] * settings['max_pt']
states = {}

dataLock = threading.Lock()
checkerThread = threading.Thread()

def create_app():
    app = Flask(__name__)

    def interrupt():
        global checkerThread
        checkerThread.cancel()
    
    def checkState():
        global checkerThread
        global states
        with dataLock:
            pass
        #print(states)
        now_ms = int(time.time_ns() / 1000)
        for device, ports in states.items():
                for port, state in ports.items():
                    #print(device, port, state)
                    if state != None:
                        timedelta = now_ms - state
                        
                        # long press
                        if timedelta >= settings['timings']['long'] * 1000000:
                            states[device][port] = None
                            args = urllib.parse.urlencode({'pt': device, port: "L"}) # pt=35, ext9=1
                            uplink_query = settings['mapping']['long'].format(args = args)
                            requests.get(uplink_query)
                            print("performing long click action on port {}:{}".format(device, port))

                        if timedelta >= settings['timings']['timeout'] * 1000000: # for what reason it has happened who knows
                            states[device][port] = None
                            print("clearing port {}:{} state due to timeout".format(device, port))
                            #print(timedelta)
        checkerThread = threading.Timer(POOL_TIME, checkState, ())
        checkerThread.start()

    def checkStateStart():
        global checkerThread
        checkerThread = threading.Timer(POOL_TIME, checkState, ())
        checkerThread.start()
    
    checkStateStart()
    atexit.register(interrupt)
    return app

app = create_app()

def ask_uplik(request, mappingSetting):
    args_urlencoded = urllib.parse.urlencode(request.args)
    uplink_query = settings['mapping'][mappingSetting].format(args = args_urlencoded)
    uplink_response = requests.get(uplink_query)
    our_response = Response(
        response=uplink_response.text, 
        status=uplink_response.status_code, 
        mimetype=uplink_response.headers['content-type']
    )
    return our_response

@app.route("/longclick")
def process_get():
    pt = request.args.get('pt')
    try:
        pt = int(pt)
        if not pt in settings['ext_pts']:
            raise Exception('not our pt')
    except:
        return ask_uplik(request, 'unknown')
        
    for arg in request.args:
        if arg.startswith('ext'): # for example, pt=35&ext1=1
            value = request.args.get(arg)
            if value == '1': # press action
                now_ms = int (time.time_ns() / 1000)
                try:
                    states_pt = states[pt]
                    states_pt[arg] = now_ms
                except:
                    states[pt] = {arg: now_ms}
                return ask_uplik(request, 'short')
            elif value == '0': # release action
                try:
                    states_pt = states[pt]
                    states_pt[arg] = None
                except:
                    states[pt] = {arg: None}
                our_response = Response(response="OK release btn", status=200)
                return our_response
            else:
                our_response = Response(response="Unknow action", status=200)
                return our_response

