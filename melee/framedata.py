import csv
import os
import math
import numpy as np
import time
from melee.enums import Action, Character, AttackState
from melee import stages
from melee.extract_data import *
from itertools import filterfalse
from collections import defaultdict

class FrameData:
    def __init__(self, write=False, output = 'logs/framedata.csv'):
        if write:
            self.csvfile = open(output, 'a+')
            fieldnames = ['character', 'action', 'frame',
                'hitbox_1_status', 'hitbox_1_size', 'hitbox_1_x', 'hitbox_1_y',
                'hitbox_2_status', 'hitbox_2_size', 'hitbox_2_x', 'hitbox_2_y',
                'hitbox_3_status', 'hitbox_3_size', 'hitbox_3_x', 'hitbox_3_y',
                'hitbox_4_status', 'hitbox_4_size', 'hitbox_4_x', 'hitbox_4_y',
                'locomotion_x', 'locomotion_y', 'iasa', 'facing_changed', 'projectile']
            self.writer = csv.writer(self.csvfile)
            #self.writer.writeheader()
            self.rows = []

            self.actionfile = open("actiondata.csv", "a")
            fieldnames = ["character", "action", "zeroindex"]
            self.actionwriter = csv.DictWriter(self.actionfile, fieldnames=fieldnames)
            self.actionwriter.writeheader()
            self.actionrows = []

            self.prevfacing = {}
            self.prevprojectilecount = {}

        #Read the existing framedata
        path = os.path.dirname(os.path.realpath(__file__))
        self.framedata = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        with open(path + "/framedata.csv") as csvfile:
            # A list of dicts containing the frame data
            csvreader = list(csv.DictReader(csvfile))
            # Build a series of nested dicts for faster read access
            for frame in csvreader:
                # Pull out the character, action, and frame
                character = Character(int(frame["character"]))
                action = Action(int(frame["action"]))
                action_frame = int(frame["frame"])
                self.framedata[character][action][action_frame] = \
                    {"hitbox_1_status": frame["hitbox_1_status"] == "True", \
                    "hitbox_1_size": float(frame["hitbox_1_size"]), \
                    "hitbox_1_x": float(frame["hitbox_1_x"]), \
                    "hitbox_1_y": float(frame["hitbox_1_y"]), \
                    "hitbox_2_status": frame["hitbox_2_status"] == "True", \
                    "hitbox_2_size": float(frame["hitbox_2_size"]), \
                    "hitbox_2_x": float(frame["hitbox_2_x"]), \
                    "hitbox_2_y": float(frame["hitbox_2_y"]), \
                    "hitbox_3_status": frame["hitbox_3_status"] == "True", \
                    "hitbox_3_size": float(frame["hitbox_3_size"]), \
                    "hitbox_3_x": float(frame["hitbox_3_x"]), \
                    "hitbox_3_y": float(frame["hitbox_3_y"]), \
                    "hitbox_4_status": frame["hitbox_4_status"] == "True", \
                    "hitbox_4_size": float(frame["hitbox_4_size"]), \
                    "hitbox_4_x": float(frame["hitbox_4_x"]), \
                    "hitbox_4_y": float(frame["hitbox_4_y"]), \
                    "locomotion_x": float(frame["locomotion_x"]), \
                    "locomotion_y": float(frame["locomotion_y"]), \
                    "iasa": frame["iasa"] == "True", \
                    "facing_changed": frame["facing_changed"] == "True", \
                    "projectile": frame["projectile"] == "True"}

        #read the character data csv
        self.characterdata = dict()
        path = os.path.dirname(os.path.realpath(__file__))
        with open(path + "/characterdata.csv") as csvfile:
            reader = csv.DictReader(csvfile)
            for line in reader:
                del line["Character"]
                #Convert all fields to numbers
                for key, value in line.items():
                    line[key] = float(value)
                self.characterdata[Character(line["CharacterIndex"])] = line

    #Returns boolean on if the given action is a roll
    def isgrab(self, character, action):
        if action in [Action.GRAB, Action.GRAB_RUNNING]:
            return True

        # Yea, I know. The sword dance isn't the right name
        if character in [Character.CPTFALCON, Character.GANONDORF] and \
                action in [Action.SWORD_DANCE_3_MID, Action.SWORD_DANCE_3_LOW]:
            return True

        if character == Character.BOWSER and \
                action in [Action.NEUTRAL_B_ATTACKING_AIR, Action.SWORD_DANCE_3_MID]:
            return True

        if character == Character.YOSHI and \
                action in [Action.NEUTRAL_B_CHARGING_AIR, Action.SWORD_DANCE_2_MID]:
            return True

        return False

    #Returns boolean on if the given action is a roll
    def isroll(self, character, action):
        # Marth counter
        if character == Character.MARTH and action == Action.MARTH_COUNTER:
            return True
        if character == Character.MARTH and action == Action.MARTH_COUNTER_FALLING:
            return True

        # Turns out that the actions we'd call a "roll" are fairly few. Let's just
        # hardcode them since it's just more cumbersome to do otherwise
        rolls = [Action.SPOTDODGE, Action.ROLL_FORWARD, Action.ROLL_BACKWARD, \
            Action.NEUTRAL_TECH, Action.FORWARD_TECH, Action.BACKWARD_TECH, \
            Action.GROUND_GETUP, Action.TECH_MISS_UP, Action.TECH_MISS_DOWN, \
            Action.EDGE_GETUP_SLOW, Action.EDGE_GETUP_QUICK, Action.EDGE_ROLL_SLOW, \
            Action.EDGE_ROLL_QUICK, Action.GROUND_ROLL_FORWARD_UP, Action.GROUND_ROLL_BACKWARD_UP, \
            Action.GROUND_ROLL_FORWARD_DOWN, Action.GROUND_ROLL_BACKWARD_DOWN, Action.SHIELD_BREAK_FLY, \
            Action.SHIELD_BREAK_FALL, Action.SHIELD_BREAK_DOWN_U, Action.SHIELD_BREAK_DOWN_D, \
            Action.SHIELD_BREAK_STAND_U, Action.SHIELD_BREAK_STAND_D, Action.TAUNT_RIGHT, Action.TAUNT_LEFT, Action.SHIELD_BREAK_TEETER]
        return action in rolls

    def isbmove(self, character, action):
        # If we're missing it, don't call it a B move
        if action == Action.UNKNOWN_ANIMATION:
            return False

        # Don't consider peach float to be a B move
        #   But the rest of her float aerials ARE
        if character == Character.PEACH and action in [Action.LASER_GUN_PULL, \
                Action.NEUTRAL_B_CHARGING, Action.NEUTRAL_B_ATTACKING]:
            return False
        # Peach smashes also shouldn't be B moves
        if character == Character.PEACH and action in [Action.SWORD_DANCE_2_MID, Action.SWORD_DANCE_1, \
                Action.SWORD_DANCE_2_HIGH]:
            return False

        if Action.LASER_GUN_PULL.value <= action.value:
            return True

        return False

    #Returns boolean on if the given action is an attack (contains a hitbox)
    def isattack(self, character, action):
        # For each frame...
        for i, frame in self.framedata[character][action].items():
            if frame:
                if frame['hitbox_1_status'] or frame['hitbox_2_status'] or frame['hitbox_3_status'] or \
                        frame['hitbox_4_status'] or frame['projectile']:
                    return True
        return False

    def isshield(self, action):
        out = action == Action.SHIELD \
            or action == Action.SHIELD_START \
            or action == Action.SHIELD_REFLECT \
            or action == Action.SHIELD_STUN \
            or action == Action.SHIELD_RELEASE
        return out

    def maxjumps(character):
        if character == Character.JIGGLYPUFF:
            return 5
        if character == Character.KIRBY:
            return 5
        return 1

    # Returns an attackstate enum
    #    WINDUP
    #    ATTACKING
    #    COOLDOWN
    #    NOT_ATTACKING
    def attackstate_simple(self, player):
        return self.attackstate(player.character, player.action, player.action_frame)

    def attackstate(self, character, action, frame):
        if not self.isattack(character, action):
            return AttackState.NOT_ATTACKING

        if frame < self.firsthitboxframe(character, action):
            return AttackState.WINDUP

        if frame > self.lasthitboxframe(character, action):
            return AttackState.COOLDOWN

        return AttackState.ATTACKING


    """
    Returns the maximum remaining range of the given attack, in the forward direction
        (relative to how the character starts facing)
        Range "remaining" means that it won't consider hitboxes that we've already passed.
    """
    def getrange_forward(self, character, action, frame):
        attackrange = 0
        lastframe = self.lasthitboxframe(character, action)
        for i in range(frame+1, lastframe+1):
            attackingframe = self.getframe(character, action, i)
            if attackingframe is None:
                continue

            if attackingframe['hitbox_1_status']:
                attackrange = max(attackingframe["hitbox_1_size"] + attackingframe["hitbox_1_x"], attackrange)
            if attackingframe['hitbox_2_status']:
                attackrange = max(attackingframe["hitbox_2_size"] + attackingframe["hitbox_2_x"], attackrange)
            if attackingframe['hitbox_3_status']:
                attackrange = max(attackingframe["hitbox_3_size"] + attackingframe["hitbox_3_x"], attackrange)
            if attackingframe['hitbox_4_status']:
                attackrange = max(attackingframe["hitbox_4_size"] + attackingframe["hitbox_4_x"], attackrange)
        return attackrange

    """
    Returns the maximum remaining range of the given attack, in the backwards direction
        (relative to how the character starts facing)
        Range "remaining" means that it won't consider hitboxes that we've already passed.
    """
    def getrange_backward(self, character, action, frame):
        attackrange = 0
        lastframe = self.lasthitboxframe(character, action)
        for i in range(frame+1, lastframe+1):
            attackingframe = self.getframe(character, action, i)
            if attackingframe is None:
                continue

            if attackingframe['hitbox_1_status']:
                attackrange = min(-attackingframe["hitbox_1_size"] + attackingframe["hitbox_1_x"], attackrange)
            if attackingframe['hitbox_2_status']:
                attackrange = min(-attackingframe["hitbox_2_size"] + attackingframe["hitbox_2_x"], attackrange)
            if attackingframe['hitbox_3_status']:
                attackrange = min(-attackingframe["hitbox_3_size"] + attackingframe["hitbox_3_x"], attackrange)
            if attackingframe['hitbox_4_status']:
                attackrange = min(-attackingframe["hitbox_4_size"] + attackingframe["hitbox_4_x"], attackrange)
        return abs(attackrange)

    # Returns the frame that the specified attack will hit the defender
    #   Returns 0 if it won't hit
    # NOTE: This considers the defending character to have a single hurtbox, centered
    #       at the x,y coordinates of the player (adjusted up a little to be centered)
    def inrange(self, attacker, defender, stage):
        lastframe = self.lasthitboxframe(attacker.character, attacker.action)

        # Adjust the defender's hurtbox up a little, to be more centered.
        #   the game keeps y coordinates based on the bottom of a character, not
        #   their center. So we need to move up by one radius of the character's size
        defender_size = float(self.characterdata[defender.character]["size"])
        defender_y = defender.y + defender_size

        # Running totals of how far the attacker will travel each frame
        attacker_x = attacker.x
        attacker_y = attacker.y

        onground = attacker.on_ground

        attacker_speed_x = 0
        if onground:
            attacker_speed_x = attacker.speed_ground_x_self
        else:
            attacker_speed_x = attacker.speed_air_x_self
        attacker_speed_y = attacker.speed_y_self

        friction = self.characterdata[attacker.character]["Friction"]
        gravity = self.characterdata[attacker.character]["Gravity"]
        termvelocity = self.characterdata[attacker.character]["TerminalVelocity"]

        for i in range(attacker.action_frame+1, lastframe+1):
            attackingframe = self.getframe(attacker.character, attacker.action, i)
            if attackingframe is None:
                continue

            # Figure out how much the attaker will be moving this frame
            #   Is there any locomotion in the animation? If so, use that
            locomotion_x = float(attackingframe["locomotion_x"])
            locomotion_y = float(attackingframe["locomotion_y"])
            if locomotion_y == 0 and locomotion_x == 0:
                # There's no locomotion, so let's figure out how the attacker will be moving...
                #   Are they on the ground or in the air?
                if onground:
                    attacker_speed_y = 0
                    # Slow down the speed by the character's friction, then apply it
                    if attacker_speed_x > 0:
                        attacker_speed_x = max(0, attacker_speed_x - friction)
                    else:
                        attacker_speed_x = min(0, attacker_speed_x + friction)
                    attacker_x += attacker_speed_x
                # If attacker is in tha air...
                else:
                    # First consider vertical movement. They will decelerate towards the stage
                    attacker_speed_y = max(-termvelocity, attacker_speed_y - gravity)
                    # NOTE Assume that the attacker will keep moving how they currently are
                    # If they do move halfway, then this will re-calculate later runs

                    attacker_y += attacker_speed_y
                    # Did we hit the ground this frame? If so, let's make some changes
                    if attacker_y <= 0 and abs(attacker_x) < stages.edgegroundposition(stage):
                        # TODO: Let's consider A moves that cancel when landing
                        attacker_y = 0
                        attacker_speed_y = 0
                        onground = True

                    attacker_x += attacker_speed_x
            else:
                attacker_x += locomotion_x
                attacker_y += locomotion_y

            if attackingframe['hitbox_1_status'] or attackingframe['hitbox_2_status'] or \
                    attackingframe['hitbox_3_status'] or attackingframe['hitbox_4_status']:
                # Calculate the x and y positions of all 4 hitboxes for this frame
                hitbox_1_x = float(attackingframe["hitbox_1_x"])
                hitbox_1_y = float(attackingframe["hitbox_1_y"]) + attacker_y
                hitbox_2_x = float(attackingframe["hitbox_2_x"])
                hitbox_2_y = float(attackingframe["hitbox_2_y"]) + attacker_y
                hitbox_3_x = float(attackingframe["hitbox_3_x"])
                hitbox_3_y = float(attackingframe["hitbox_3_y"]) + attacker_y
                hitbox_4_x = float(attackingframe["hitbox_4_x"])
                hitbox_4_y = float(attackingframe["hitbox_4_y"]) + attacker_y

                # Flip the horizontal hitboxes around if we're facing left
                if not attacker.facing:
                    hitbox_1_x *= -1
                    hitbox_2_x *= -1
                    hitbox_3_x *= -1
                    hitbox_4_x *= -1

                hitbox_1_x += attacker_x
                hitbox_2_x += attacker_x
                hitbox_3_x += attacker_x
                hitbox_4_x += attacker_x

                # Now see if any of the hitboxes are in range
                distance1 = math.sqrt((hitbox_1_x - defender.x)**2 + (hitbox_1_y - defender_y)**2)
                distance2 = math.sqrt((hitbox_2_x - defender.x)**2 + (hitbox_2_y - defender_y)**2)
                distance3 = math.sqrt((hitbox_3_x - defender.x)**2 + (hitbox_3_y - defender_y)**2)
                distance4 = math.sqrt((hitbox_4_x - defender.x)**2 + (hitbox_4_y - defender_y)**2)

                if distance1 < defender_size + float(attackingframe["hitbox_1_size"]):
                    return i
                if distance2 < defender_size + float(attackingframe["hitbox_2_size"]):
                    return i
                if distance3 < defender_size + float(attackingframe["hitbox_3_size"]):
                    return i
                if distance4 < defender_size + float(attackingframe["hitbox_4_size"]):
                    return i
        return 0

    """
    Returns the height the character's double jump will take them.
        If character is in jump already, returns how heigh that one goes
    """
    def getdjheight(self, character_state):
        # Peach's DJ doesn't follow normal physics rules. Hardcoded it
        if character_state.character == Character.PEACH:
            # She can't get height if not in the jump action
            if character_state.action != Action.JUMPING_ARIAL_FORWARD:
                if character_state.jumps_left == 0:
                    return 0
                else:
                    return 33.218964577
            # This isn't exact. But it's close
            return 33.218964577 * (1 - (character_state.action_frame / 60))

        gravity = self.characterdata[character_state.character]["Gravity"]
        initdjspeed = self.characterdata[character_state.character]["InitDJSpeed"]
        if character_state.jumps_left == 0:
            initdjspeed = character_state.speed_y_self - gravity

        if character_state.character == Character.JIGGLYPUFF:
            if character_state.jumps_left >= 5:
                initdjspeed = 1.586
            if character_state.jumps_left == 4:
                initdjspeed = 1.526
            if character_state.jumps_left == 3:
                initdjspeed = 1.406
            if character_state.jumps_left == 2:
                initdjspeed = 1.296
            if character_state.jumps_left <= 1:
                initdjspeed = 1.186

        distance = 0

        while initdjspeed > 0:
            distance += initdjspeed
            initdjspeed -= gravity
        return distance

    """
    Return the number of frames it takes for the character to reach the apex of
        their double jump. If they haven't used it yet, then calculate it as if they
        jumped right now.
    """
    def getdjapexframes(self, character_state):
        # Peach's DJ doesn't follow normal physics rules. Hardcoded it
        # She can float-cancel, so she can be falling at any time during the jump
        if character_state.character == Character.PEACH:
            return 1

        gravity = self.characterdata[character_state.character]["Gravity"]
        initdjspeed = self.characterdata[character_state.character]["InitDJSpeed"]
        if character_state.jumps_left == 0:
            initdjspeed = character_state.speed_y_self - gravity

        if character_state.character == Character.JIGGLYPUFF:
            if character_state.jumps_left >= 5:
                initdjspeed = 1.586
            if character_state.jumps_left == 4:
                initdjspeed = 1.526
            if character_state.jumps_left == 3:
                initdjspeed = 1.406
            if character_state.jumps_left == 2:
                initdjspeed = 1.296
            if character_state.jumps_left <= 1:
                initdjspeed = 1.186

        frames = 0
        while initdjspeed > 0:
            frames += 1
            initdjspeed -= gravity
        return frames

    # Returns a frame dict for the specified frame
    def getframe(self, character, action, action_frame):
        if self.framedata[character][action][action_frame]:
            return self.framedata[character][action][action_frame]
        return None

    # Returns the last frame of the roll
    # -1 if not a roll
    def lastrollframe(self, character, action):
        if not self.isroll(character, action):
            return -1
        frames = []
        for action_frame in self.framedata[character][action]:
            frames.append(action_frame)
        if not frames:
            return -1
        return max(frames)

    # Returns the x coordinate that the current roll will end in
    def endrollposition(self, character_state, stage):
        distance = 0
        try:
            #TODO: Take current momentum into account
            # Loop through each frame in the attack
            for action_frame in self.framedata[character_state.character][character_state.action]:
                # Only care about frames that haven't happened yet
                if action_frame > character_state.action_frame:
                    distance += self.framedata[character_state.character][character_state.action][action_frame]["locomotion_x"]

            # We can derive the direction we're supposed to be moving by xor'ing a few things together...
            #   1) Current facing
            #   2) Facing changed in the frame data
            #   3) Is backwards roll
            facingchanged = self.framedata[character_state.character][character_state.action][character_state.action_frame]["facing_changed"]
            backroll = character_state.action in [Action.ROLL_BACKWARD, Action.GROUND_ROLL_BACKWARD_UP, \
                Action.GROUND_ROLL_BACKWARD_DOWN, Action.BACKWARD_TECH]
            if not (character_state.facing ^ facingchanged ^ backroll):
                distance = -distance

            position = character_state.x + distance

            if character_state.action not in [Action.TECH_MISS_UP, Action.TECH_MISS_DOWN]:
                # Adjust the position to account for the fact that we can't roll off the stage
                position = min(position, stages.edgegroundposition(stage))
                position = max(position, -stages.edgegroundposition(stage))
            return position
        # If we get a key error, just assume this animation doesn't go anywhere
        except KeyError:
            return character_state.x

    #Returns the first frame that a hitbox appears for a given action
    #   returns -1 if no hitboxes (not an attack action)
    def firsthitboxframe(self, character, action):
        # Grab only the subset that have a hitbox
        hitboxes = []
        for action_frame, frame in self.framedata[character][action].items():
            if frame:
                #Does this frame have a hitbox?
                if frame['hitbox_1_status'] or frame['hitbox_2_status'] \
                    or frame['hitbox_3_status'] or frame['hitbox_4_status'] or \
                        frame['projectile']:
                    hitboxes.append(action_frame)
        if not hitboxes:
            return -1
        return min(hitboxes)

    # Returns the number of hitboxes an attack has
    #   By this we mean is it a multihit attack? (Peach's down B?)
    #       or a single-hit attack? (Marth's fsmash?)
    def hitboxcount(self, character, action):
        # Grab only the subset that have a hitbox

        # This math doesn't work for Samu's UP_B
        #   Because the hitboxes are contiguous
        if character == Character.SAMUS and action in [Action.SWORD_DANCE_3_MID, Action.SWORD_DANCE_3_LOW]:
            return 7

        hitboxes = []
        for action_frame, frame in self.framedata[character][action].items():
            if frame:
                #Does this frame have a hitbox?
                if frame['hitbox_1_status'] or frame['hitbox_2_status'] \
                    or frame['hitbox_3_status'] or frame['hitbox_4_status'] or \
                        frame['projectile']:
                    hitboxes.append(action_frame)
        if not hitboxes:
            return 0
        hashitbox = False
        count = 0
        # Every time we go from NOT having a hit box to having one, up the count
        for i in range(1, max(hitboxes)+1):
            hashitbox_new = i in hitboxes
            if hashitbox_new and not hashitbox:
                count += 1
            hashitbox = hashitbox_new
        return count

    # Returns the first frame of an attack that the character is interruptible
    #   returns -1 if not an attack
    def iasa(self, character, action):
        if not self.isattack(character, action):
            return -1
        iasaframes = []
        allframes = []
        for action_frame, frame in self.framedata[character][action].items():
            if frame:
                #Does this frame have a hitbox?
                allframes.append(action_frame)
                if frame["iasa"]:
                    iasaframes.append(action_frame)
        if not iasaframes:
            return max(allframes)
        return min(iasaframes)

    #Returns the last frame that a hitbox appears for a given action
    #   returns -1 if no hitboxes (not an attack action)
    def lasthitboxframe(self, character, action):
        # Grab only the subset that have a hitbox
        hitboxes = []
        for action_frame, frame in self.framedata[character][action].items():
            if frame:
                #Does this frame have a hitbox?
                if frame['hitbox_1_status'] or frame['hitbox_2_status'] \
                    or frame['hitbox_3_status'] or frame['hitbox_4_status'] or \
                        frame['projectile']:
                    hitboxes.append(action_frame)
        if not hitboxes:
            return -1
        return max(hitboxes)

    """
    Returns the count of total frames in the given action.
    """
    def lastframe(self, character, action):
        frames = []
        for action_frame, frame in self.framedata[character][action].items():
            frames.append(action_frame)
        if not frames:
            return -1
        return max(frames)

    def recordframe(self, gamestate):
        state = gamestate.tolist()

        row = [time.time()] + state
        self.rows.append(row)

    def saverecording(self, filename):
        # Add actions
        actions = extract_actions(filename)
        self.rows = merge_state_action(self.rows, actions)

        # Save Data
        self.writer.writerows(self.rows)
        self.actionwriter.writerows(self.actionrows)
        self.csvfile.close()
        self.actionfile.close()

    def flush_button_presses(self, filename):
        print("Emptying old button presses")
        with open('logs/' + filename, 'r+') as action_file:
            action_file.seek(0)
            action_file.truncate()

    """
    How far will a character slide, given:
        character: An enum value of the sliding character
        initspeed: The initial speed of the character
        frames: How many frames we want to calculate for
    """
    def slidedistance(self, character_state, initspeed, frames):
        normalfriction = self.characterdata[character_state.character]["Friction"]
        friction = normalfriction
        totaldistance = 0
        walkspeed = self.characterdata[character_state.character]["MaxWalkSpeed"]
        # Just the speed, not direction
        absspeed = abs(initspeed)
        multiplier = 1
        for i in range(frames):
            # Special case for these two damn animations, for some reason. Thanks melee
            if character_state.action in [Action.TECH_MISS_UP]:
                if character_state.action_frame + i < 18:
                    friction = .051
                    multiplier = 1
                else:
                    friction = normalfriction
            # If we're sliding faster than the character's walk speed, then
            #   the slowdown is doubled
            elif absspeed > walkspeed:
                multiplier = 2
            else:
                multiplier = 1

            absspeed -= friction * multiplier
            if absspeed < 0:
                break
            totaldistance += absspeed
        if initspeed < 0:
            totaldistance = -totaldistance

        return totaldistance
