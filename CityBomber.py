#!/usr/bin/python3
#
# CityBomber: Python version of the classic Commodore VIC-20 game called Blitzkrieg
#
# Author    : Dean Gawler
#
# Version   : 1.0 January 2021
#

import pygame
import os
import random
import time


## Global variables & constants
#
ASSETS="./assets"
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,11,3)
DRED = (128,0,0)
BLUE = (3,45,255)
YELLOW = (255,255,0)
COLORS = [WHITE,RED,BLUE]

BOMB_COLOR = WHITE
BOMB_HEIGHT = 15
BOMB_WIDTH = 15
TOTAL_BOMBS_FALLING = 0

BUILDING_GAP = 5
BUILDING_LEVEL_HEIGHT = 30
BUILDING_WIDTH = 32
CITY_START_X = 100

PLANE_WIDTH = 50
PLANE_HEIGHT = 30

FPS = 50
GAME_RUNNING = True

## Load sounds
#
# freq, size, channel, buffsize
pygame.mixer.pre_init(44100, 16, 1, 512)
pygame.mixer.init()
bomb_drop_sound = pygame.mixer.Sound(ASSETS + "/" + "bomb_dropping.wav")
plane_crash_sound = pygame.mixer.Sound(ASSETS + "/" + "bomb_explosion.wav")
building_destroy_sound = pygame.mixer.Sound(ASSETS + "/" + "bomb-explode.wav")


########################## CLASSES AND FUNCTIONS #########################


class Plane:
    def __init__(self, x, y, velocity):
        self.x = x
        self.y = y
        self.velocity = velocity
        self.plane_landed = False
        self.plane_crashed = False

    def move(self,city):
        # Move plane to the right, and if we reach edge of screen, then move
        # plane down one row.
        if (self.x + self.velocity) >= SCREEN_WIDTH:
           self.x = 0
           self.y += int(PLANE_HEIGHT * 1.5)
           if self.y >= (SCREEN_HEIGHT - PLANE_HEIGHT):
               self.y = SCREEN_HEIGHT - PLANE_HEIGHT
        else:
           self.x += self.velocity

        # Move the plane
        plane_front = self.x + PLANE_WIDTH
        plane_bottom = self.y

        # See if we have hit a building.
        for next_building in range(0,len(city)):
            building = city[next_building]
            building_top = SCREEN_HEIGHT - (building.building_levels * BUILDING_LEVEL_HEIGHT)
            level_start_x = CITY_START_X + building.building_number * (BUILDING_WIDTH + BUILDING_GAP)
            building_end_x = level_start_x + BUILDING_WIDTH
            if plane_front >= level_start_x and plane_front <= building_end_x and (plane_bottom + PLANE_HEIGHT) >= building_top:
                # We crashed!
                self.plane_crashed = True
                self.crash_into_building()

        # Has bomber reached bottom of screen?
        if self.y + int(PLANE_HEIGHT * 1.5) > SCREEN_HEIGHT:
            self.plane_landed = True

    def draw_self(self, gamesurface):
        # Draw main plane. Show the bomb within the plane unless the bomb
        # has been dropped.

        # Tail
        pygame.draw.polygon(gamesurface,RED,[(self.x,self.y),(self.x,self.y+20),(self.x+13,self.y+24),(self.x+13,self.y)])

        #Body
        pygame.draw.rect(gamesurface,RED,(self.x+13,self.y+13,30,12))

        # Nose
        pygame.draw.polygon(gamesurface,RED,[(self.x+43,self.y+13),(self.x+43,self.y+24),(self.x+PLANE_WIDTH,self.y+24)])

        # Draw bomb location on plane so player knows how to aim
        b_x = self.x + PLANE_WIDTH - 20
        b_y = self.y + PLANE_HEIGHT - 10
        pygame.draw.rect(gamesurface,BOMB_COLOR,(b_x, b_y, 8, 5))

    def crash_into_building(self):
        pygame.mixer.Sound.play(plane_crash_sound)


class Building:
    def __init__(self, building_number):
        # Create a building of random height and color
        self.building_number = building_number
        self.building_levels = random.randrange(2,(SCREEN_HEIGHT // 2) // BUILDING_LEVEL_HEIGHT)
        self.building_color = COLORS[random.randrange(0,len(COLORS))]
        self.max_levels_to_destroy = 5
        self.levels_destroyed = 0
        self.draw_building_roof = True

        # Set a color for our windows
        same_color = True
        while same_color:
            self.win_color = COLORS[random.randrange(0,len(COLORS))]
            if not (self.win_color == self.building_color):
                same_color = False

    def draw_self(self, gamesurface):
        # Draw remaining buildings using the predetermined heights, but only if the
        # building has 1 or more levels.
        for next_level in range(1,self.building_levels + 1):
            if next_level == self.building_levels and self.draw_building_roof:
                self.draw_roof(gamesurface,next_level)
            else:
                self.draw_next_level(gamesurface,next_level)

    def draw_next_level(self, gamesurface, level_number):
            # Draw the next level in our building
            level_start_y = level_number * BUILDING_LEVEL_HEIGHT
            level_start_x = CITY_START_X + self.building_number * (BUILDING_WIDTH + BUILDING_GAP)
            pygame.draw.rect(gamesurface,self.building_color,(level_start_x,SCREEN_HEIGHT-level_start_y,BUILDING_WIDTH,BUILDING_LEVEL_HEIGHT))

            # Draw the windows in the building level - make them 6x6 pixels
            for row in [4,20]:
                for col in [4,20]:
                    pygame.draw.rect(gamesurface,self.win_color,(level_start_x+col,SCREEN_HEIGHT-level_start_y+row,6,6))

    def draw_roof(self, gamesurface, level_number):
            # Draw the next level in our building
            level_start_y = level_number * BUILDING_LEVEL_HEIGHT
            level_start_x = CITY_START_X + self.building_number * (BUILDING_WIDTH + BUILDING_GAP)
            # Draw the roof as a simple pyramid on top of the last level
            ROOF_STEEPLE=(level_start_x + int(BUILDING_WIDTH / 2),SCREEN_HEIGHT - level_start_y)
            ROOF_BASE_LEFT=(level_start_x,SCREEN_HEIGHT - level_start_y + BUILDING_LEVEL_HEIGHT)
            ROOF_BASE_RIGHT=(level_start_x + BUILDING_WIDTH,SCREEN_HEIGHT - level_start_y + BUILDING_LEVEL_HEIGHT)
            ROOF_TUPLE=[ROOF_STEEPLE,ROOF_BASE_RIGHT,ROOF_BASE_LEFT]
            pygame.draw.polygon(gamesurface, self.building_color, ROOF_TUPLE)

    def destroy_level(self,falling_bomb):
        global TOTAL_BOMBS_FALLING

        # If the bomb has reached the building, simply remove one level of the building
        if self.building_levels > 0:
            building_height = self.building_levels * BUILDING_LEVEL_HEIGHT
            bomb_bottom_y = falling_bomb.y + BOMB_HEIGHT

            # Check to see if bottom of bomb has hit current top of building
            if bomb_bottom_y > SCREEN_HEIGHT - building_height:
                # Yep, so destroy another level as long as we have not exceeded
                # the maximum levels that a single bomb can destroy. If the height
                # of the building is close to maximum levels, then just destroy it.
                # Also set the flag to not redraw the roof, because it has been destroyed.
                self.draw_building_roof = False
                if self.building_levels > 0:
                    if self.levels_destroyed < self.max_levels_to_destroy:
			# Play destruction sound
                        self.destroy_level_sound()
                        self.building_levels -= 1
                        self.levels_destroyed += 1
                        if self.building_levels <= 0:
                            falling_bomb.falling = False
                            TOTAL_BOMBS_FALLING -= 1
                            bomb_drop_sound.stop()
                    else:
                        falling_bomb.falling = False
                        self.levels_destroyed = 0
                        TOTAL_BOMBS_FALLING -= 1
                        bomb_drop_sound.stop()

    def destroy_level_sound(self):
        bomb_drop_sound.stop()
        pygame.mixer.Sound.play(building_destroy_sound)


class Bomb:

    def __init__(self):
        # Set basic defaults
        self.falling = False
        self.hit_building = False
        self.hit_building_number = 0

    def drop(self,plane,city):
        # This function only gets called when a new bomb is dropped.
        # Set flag to say bomb is falling
        self.falling = True

        # Bomb drop sounds
        ##pygame.mixer.Sound.play(bomb_drop_sound)
        bomb_drop_sound.play()

        # Work out where start of bomb is
        self.x = plane.x + int((PLANE_WIDTH - BOMB_WIDTH) // 2)
        self.y = plane.y + PLANE_HEIGHT
        #### print("Dropping bomb at x: %d y: %d" % (self.x, self.y))

        # Work out if a building will be hit by a falling bomb
        for next_building in range(0,len(city)):
            next_b = city[next_building]
            next_b_start_x = CITY_START_X + next_b.building_number * (BUILDING_WIDTH + BUILDING_GAP)
            if ((self.x + BOMB_WIDTH) > next_b_start_x) and (self.x < (next_b_start_x + BUILDING_WIDTH)):
                self.hit_building = True
                self.hit_building_number = next_building

    def draw_self(self,gamesurface):
        # Draw remaining buildings using the predetermined heights
        pygame.draw.rect(gamesurface,BOMB_COLOR,(self.x,self.y,BOMB_WIDTH,BOMB_HEIGHT))

    def move(self):
        # Move bomb down the screen if it has been dropped
        if self.falling:
            if self.y + (BOMB_HEIGHT * 0.75) < SCREEN_HEIGHT:
                #### self.y += int(BOMB_HEIGHT * 1.5)
                self.y += int(BOMB_HEIGHT * 0.75)
            else:
                self.falling = False
                self.hit_building = False
                self.hit_building_number = 0

################################### MAIN #################################

def main():
    global GAME_RUNNING
    global TOTAL_BOMBS_FALLING

    start_x = 0
    start_y = 0
    start_velocity=7
    MAX_BOMBS = 2
    MAX_BUILDINGS = 16
    hit_building = False
    hit_building_number =0
    falling_bomb_count = 0
    all_bombs=[]
    city=[]

    # Initialise screen
    pygame.init()
    gamewindow = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
    pygame.display.set_caption("CITY BOMBER")
    background = pygame.Surface(gamewindow.get_size())
    background = background.convert()

    # Set font for game_title
    ##font = pygame.font.SysFont("comicsansms", 36)
    font = pygame.font.SysFont("comicsansms", 24)
    game_title = font.render("City Bomber", True, BLUE)

    #### background.fill(BLACK)
    BG = pygame.transform.scale(pygame.image.load(ASSETS + "/" + "city_skyline-background.png"), (SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.flip()

    # Work out starting Y position for our bomber. We want the starting height to
    # be a multiple of the height of our bomber plane, minus a couple of pixels. This
    # will allow the plane to land at the end of the game if the player is successful.
    #
    # Aim to start the plane somewhere in the top third of the screen.
    #
    random.seed()
    screen_plane_heights=SCREEN_HEIGHT // PLANE_HEIGHT
    screen_middle=SCREEN_HEIGHT - ((screen_plane_heights // 2) * PLANE_HEIGHT)
    start_y=screen_middle - random.randrange(3,screen_plane_heights // 2) * PLANE_HEIGHT

    # Create our bomber plane and list of bombs
    plane=Plane(start_x,start_y,start_velocity)

    # Create some bombs
    for n in range(0,MAX_BOMBS):
        all_bombs.append(Bomb())

    # Create a city skyline full of buildings
    for next_b in range(0,MAX_BUILDINGS):
        b=Building(next_b)
        city.append(b)

    # Set the Clock
    clock = pygame.time.Clock()

    # Run our bomber across the screen until the user presses the window exit button
    while GAME_RUNNING:
        # Look for keyboard input and process
        for next_event in pygame.event.get():
            if next_event.type == pygame.KEYDOWN:
                if next_event.key == pygame.K_SPACE:
                    if falling_bomb_count < MAX_BOMBS:
                        # Look for an undropped bomb and use that one. Make sure
                        # that we cannot launch more than the max bombs.
                        bomb_to_use = 0
                        found_undropped_bomb = False
                        while bomb_to_use < MAX_BOMBS and not found_undropped_bomb:
                            if not all_bombs[bomb_to_use].falling:
                                found_undropped_bomb = True
                            else:
                                bomb_to_use += 1
                        all_bombs[bomb_to_use].drop(plane,city)
                        falling_bomb_count += 1
                elif next_event.key == pygame.K_ESCAPE:
                    GAME_RUNNING=False
            elif next_event.type == pygame.QUIT:
                GAME_RUNNING=False

        # Check if building will be hit and do some damage if the bomb has hit it
        for n in range(0,MAX_BOMBS):
            next_bomb = all_bombs[n]
            if next_bomb.falling:
                if next_bomb.hit_building:
                    damaged_building = city[next_bomb.hit_building_number]
                    damaged_building.destroy_level(next_bomb)

        # Update our surface with the current status for plane, buildings, and bomb
        gamewindow.blit(BG,(0,0))
        ## gamewindow.blit(game_title,((SCREEN_WIDTH // 2) - game_title.get_width() // 2, game_title.get_height() // 2))
        gamewindow.blit(game_title,((SCREEN_WIDTH // 2) - game_title.get_width() // 2, 5))

        #### gamewindow.fill(BLACK)
        plane.move(city)
        plane.draw_self(gamewindow)
        for next_building in range(0,len(city)):
            city[next_building].draw_self(gamewindow)

        # Count how many bombs are still active to make sure we do not exceed
        # the maximum number of dropping bombs. Move each active bomb.
        active = 0
        for next_bomb in range(0,len(all_bombs)):
            if all_bombs[next_bomb].falling:
                active += 1
                all_bombs[next_bomb].move()
                all_bombs[next_bomb].draw_self(gamewindow)
        falling_bomb_count = active

        # Check to see if we landed or crashed and stop the game if we did
        if plane.plane_landed or plane.plane_crashed:
            GAME_RUNNING = False

        # Draw our updated surface on the screen
        pygame.display.update()
        clock.tick(FPS)

################################# END MAIN ###############################

if __name__ == '__main__':
    main()

pygame.time.delay(3000)
pygame.quit()
