#!/usr/bin/python3
import melee
import argparse
from os import listdir
import signal
import sys
import time

#This example program demonstrates how to use the Melee API to run dolphin programatically,
#   setup controllers, and send button presses over to dolphin

def check_port(value):
    ivalue = int(value)
    if ivalue < 1 or ivalue > 4:
         raise argparse.ArgumentTypeError("%s is an invalid controller port. \
         Must be 1, 2, 3, or 4." % value)
    return ivalue

chain = None
doneWriting = False

parser = argparse.ArgumentParser(description='Example of libmelee in action')
parser.add_argument('--port', '-p', type=check_port,
                    help='The controller port your AI will play on',
                    default=2)
parser.add_argument('--opponent', '-o', type=check_port,
                    help='The controller port the opponent will play on',
                    default=1)
parser.add_argument('--live', '-l',
                    help='The opponent is playing live with a GCN Adapter',
                    default=True)
parser.add_argument('--debug', '-d', default=False, action='store_true',
                    help='Debug mode. Creates a CSV of all game state')
parser.add_argument('--framerecord', '-r', default=False, action='store_true',
                    help='(DEVELOPMENT ONLY) Records frame data from the match, stores into logs/')
parser.add_argument('--flush', '-f', default=False, action='store_true',
                    help='Empties button press file after every game')

parser.add_argument("--iso", type=str, help="path to smash iso", default="../smash.iso")

args = parser.parse_args()

log = None
if args.debug:
    log = melee.logger.Logger()

#Options here are:
#   "Standard" input is what dolphin calls the type of input that we use
#       for named pipe (bot) input
#   GCN_ADAPTER will use your WiiU adapter for live human-controlled play
#   UNPLUGGED is pretty obvious what it means
opponent_type = melee.enums.ControllerType.UNPLUGGED
if args.live:
    opponent_type = melee.enums.ControllerType.GCN_ADAPTER

#Create our Dolphin object. This will be the primary object that we will interface with
dolphin = melee.dolphin.Dolphin(ai_port=args.port,
                                opponent_port=args.opponent,
                                opponent_type=opponent_type,
                                logger=log)
#Create our GameState object for the dolphin instance
gamestate = melee.gamestate.GameState(dolphin)
#Create our Controller object that we can press buttons on
controller = melee.controller.Controller(port=args.port, dolphin=dolphin)


#Run dolphin and render the output
dolphin.run(render=True, iso_path=args.iso)

#Plug our controller in
#   Due to how named pipes work, this has to come AFTER running dolphin
#   NOTE: If you're loading a movie file, don't connect the controller,
#   dolphin will hang waiting for input and never receive it
controller.connect()

# Find Button Presses File
doneWriting = True
curr_time = str(int(time.time()))
if args.framerecord:
    found_file = False
    num_actions = 16
    while not found_file:
        time.sleep(5)
        filenames = listdir('logs/')
        for filename in filenames:
            if "keyboard_presses_" + curr_time in filename:
                button_presses_filename = filename
                print("Tracking file " + filename)
                found_file = True
                break
        

#Main loop
gamecount = 0
while True:
    #"step" to the next frame
    gamestate.step()
    if(gamestate.processingtime * 1000 > 12):
        print("WARNING: Last frame took " + str(gamestate.processingtime*1000) + "ms to process.")

    #What menu are we in?
    if gamestate.menu_state in [melee.enums.Menu.IN_GAME, melee.enums.Menu.SUDDEN_DEATH]:
        if args.framerecord:
            if doneWriting:
                framedata = melee.framedata.FrameData(args.framerecord, "logs/game" + str(gamecount) + "-" + str(int(time.time()))+ ".csv")
                doneWriting = False

            framedata.recordframe(gamestate)
            
            
        #XXX: This is where your AI does all of its stuff!
        #This line will get hit once per frame, so here is where you read
        #   in the gamestate and decide what buttons to push on the controller
        pass
    #If we're at the character select screen, choose our character
    elif gamestate.menu_state == melee.enums.Menu.CHARACTER_SELECT:
        melee.menuhelper.choosecharacter(character=melee.enums.Character.FOX,
                                        gamestate=gamestate,
                                        port=args.port,
                                        opponent_port=args.opponent,
                                        controller=controller,
                                        swag=True,
                                        start=True)

    #If we're at the postgame scores screen, spam START
    elif gamestate.menu_state == melee.enums.Menu.POSTGAME_SCORES:
        if args.framerecord and not doneWriting:
            time.sleep(1)
            gamecount += 1
            framedata.saverecording(button_presses_filename)
            doneWriting = True
            if args.flush:
                framedata.flush_button_presses(button_presses_filename)

        melee.menuhelper.skippostgame(controller=controller)

    #If we're at the stage select screen, choose a stage
    elif gamestate.menu_state == melee.enums.Menu.STAGE_SELECT:
        melee.menuhelper.choosestage(stage=melee.enums.Stage.POKEMON_STADIUM,
                                    gamestate=gamestate,
                                    controller=controller)

    #Flush any button presses queued up
    controller.flush()
    if log:
        log.logframe(gamestate)
        log.writeframe()
