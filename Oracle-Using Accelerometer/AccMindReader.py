################################################################# 
#                      M I N D   R E A D E R                    #
#################################################################
#       You are presented with an image carousel, and are       #
#       expected to select an image by trying to move           #
#       your left or right hand.                                #
#                                                               #
#       Mind, this is not a real mind reader, yet... :-)        #
#       Coded by Thomas Vikström, 2022                          #
#################################################################

# *******************  IMPORTING MODULES ********************

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

import threading
import numpy as np
#import tensorflow as tf          # << Model code removed >>
#from nltk import flatten          # << Not needed with OSC accelerometer control >>
import webbrowser

import pygame
import pygame_menu
from pygame.locals import *
from pygame_menu.examples import create_example_window
import string
import os

from pynput.keyboard import Key, Controller
from timeit import default_timer as timer

# *********************  G L O B A L S *********************

alpha = beta = delta = theta = gamma = [-1,-1,-1,-1]
all_waves = [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]
all_samples = []      # Not used anymore

sample_nr = 0
expected_samples = 30  # Not used anymore

confidence_threshold = 0.5  # Not used (model code removed)
left = right = background = 0

blinks = 0
blinked = False
bl2 = bl3 = False
jaw_clenches = 0
jaw_clenched = False
state = 0
alphabet = []
blink_time = []

start = timer()
secs = 3

IP = "0.0.0.0"     # listening on all IP-addresses
PORT = 5000        # on this port


# ******************* New Accelerometer Handler *******************
def accel_handler(address, *args):
    global state
    # Expecting OSC accelerometer message with three values: [accel_x, accel_y, accel_z]
    if len(args) < 2:
        return  # Not enough data; ignore
    accel_y = args[1]
    print(f"Accelerometer Y-axis value: {accel_y}")  # Print the Y-axis value for debugging
    # Define threshold values (adjust these thresholds as needed)
    threshold_up = 0.4    # Sudden rise above this moves left
    threshold_down = -0.3 # Sudden drop below this moves right
    if accel_y > threshold_up:
        state = 1    # Move left
    elif accel_y < threshold_down:
        state = -1     # Move right
    else:
        state = 0     # No movement


# ****************** Existing EEG handlers (for blinks, jaw, etc.) ******************
def blink_handler(address, *args):
    global blinks, blinked, state, bl2
    bl2_treshold = 0.7
    blink_time.append(timer())
    bl2 = False
    if blinks >= 2:
        now  = blink_time[blinks]
        then = blink_time[blinks-1]
        if (now - then) < bl2_treshold:
            bl2 = True
        else:
            bl2 = False
            blinked = True
            state = 0
    blinks += 1

def jaw_handler(address, *args):
    global jaw_clenches, jaw_clenched
    jaw_clenches += 1
    jaw_clenched = True
    print("Jaw Clench detected")

def alpha_handler(address: str, *args):
    global alpha, beta, delta, theta, gamma
    if (len(args)==5):
        for i in range(1,5):
            all_waves[i-1] = args[i]

def beta_handler(address: str, *args):
    global alpha, beta, delta, theta, gamma
    if (len(args)==5):
        for i in range(1,5):
            all_waves[i-1 + 4] = args[i]

def delta_handler(address: str, *args):
    global alpha, beta, delta, theta, gamma
    if (len(args)==5):
        for i in range(1,5):
            all_waves[i-1 + 8] = args[i]

def theta_handler(address: str, *args):
    global alpha, beta, delta, theta, gamma
    if (len(args)==5):
        for i in range(1,5):
            all_waves[i-1 + 12] = args[i]

def gamma_handler(address: str, *args):
    global alpha, beta, delta, theta, gamma, sample_nr, expected_samples, all_samples, sample
    if (len(args)==5):
        for i in range(1,5):
            all_waves[i-1 + 16] = args[i]
        all_samples.append(all_waves)
        sample_nr += 1 
        if sample_nr == expected_samples:
            # In model mode, we would perform inference here.
            # With accelerometer control, we simply reset.
            sample_nr = 0
            all_samples.clear()
            all_samples = []

# ****************** OSC Dispatcher and Server ******************
def get_dispatcher():
    dispatcher = Dispatcher()
    dispatcher.map("/muse/elements/blink", blink_handler)
    dispatcher.map("/muse/elements/jaw_clench", jaw_handler)
    dispatcher.map("/muse/elements/delta_absolute", delta_handler, 0)
    dispatcher.map("/muse/elements/theta_absolute", theta_handler, 1)
    dispatcher.map("/muse/elements/alpha_absolute", alpha_handler, 2)
    dispatcher.map("/muse/elements/beta_absolute", beta_handler, 3)
    dispatcher.map("/muse/elements/gamma_absolute", gamma_handler, 4)
    # Map the accelerometer OSC address to our new handler
    dispatcher.map("/muse/acc", accel_handler)
    return dispatcher

def start_blocking_server(ip, port):
    server = BlockingOSCUDPServer((ip, port), dispatcher)
    server.serve_forever()  # Blocks forever

def dispatch():
    global dispatcher
    dispatcher = get_dispatcher()
    start_blocking_server(IP, PORT)

def start_threads():
    thread = threading.Thread(target=dispatch)
    thread.daemon = True
    thread.start()

# ****************** DISPLAY / UI FUNCTIONS ******************
def clear_screen():
    screen = pygame.display.set_mode(size)
    pygame.display.update()

def show_image():
    global screen, blinked, state, alphabet
    scr_width  = size[0]
    scr_height = size[1]
    MAXHEALTH = 9
    GREEN = (48, 141, 70)
    WHITE = (200,200,200)
    back_color = (55,55,55)
    HB_X = (scr_width / 2) - 185
    HB_HEIGHT = 11
    font = pygame.font.SysFont(None, 60)

    def clear_area():
        pygame.draw.rect(screen, back_color, (HB_X, scr_height / 2 + 50, 100 * MAXHEALTH, HB_HEIGHT))

    def drawHealthMeterLeft(currentHealth):
        clear_area()
        for i in range(currentHealth):
            pygame.draw.rect(screen, GREEN, (HB_X + (10 * MAXHEALTH) - (i * 10), scr_height / 2 + 50, 20, HB_HEIGHT))
        for i in range(MAXHEALTH):
            pygame.draw.rect(screen, WHITE, (HB_X + (10 * MAXHEALTH) - (i * 10), scr_height / 2 + 50, 20, HB_HEIGHT), 1)

    def drawHealthMeterBackground(currentHealth):
        cH = currentHealth
        for i in range(cH):
            pygame.draw.rect(screen, GREEN, ((scr_width/2) - (5*cH) + (i*10)-10, scr_height / 2 + 50, 20, HB_HEIGHT))
        for i in range(MAXHEALTH):
            pygame.draw.rect(screen, WHITE, (HB_X+120 + (10 * MAXHEALTH) - i * 10, scr_height / 2 + 50, 20, HB_HEIGHT), 1)

    def drawHealthMeterRight(currentHealth):
        for i in range(currentHealth):
            pygame.draw.rect(screen, GREEN, (HB_X+160 + (10 * MAXHEALTH) + i * 10, scr_height / 2 + 50, 20, HB_HEIGHT))
        for i in range(MAXHEALTH):
            pygame.draw.rect(screen, WHITE, (HB_X+160 + (10 * MAXHEALTH) + i * 10, scr_height / 2 + 50, 20, HB_HEIGHT), 1)

    def write(txt, x, y, color, size):
        font = pygame.font.SysFont(None, size)
        img = font.render(txt, True, color)
        screen.blit(img, (x, y))

    def write_alphabet(list):
        pygame.draw.rect(screen, back_color, (0, scr_height / 2 + 100, scr_width, 35))
        i = 0
        for c in list:
            write(c[0], 50 + (i*40), scr_height/2 + 100, WHITE, 60)
            i += 1

    def text_editor():
        global alphabet, text, blinked, state, bl2
        pygame.draw.rect(screen, GREEN, pygame.Rect((scr_width/2)-35, (scr_height/2) + 88, 40, 60), 4, 6)
        write_alphabet(alphabet)
        pygame.draw.rect(screen, WHITE, pygame.Rect(20, (scr_height/2) + 180, scr_width-40, 170), 1, 6)
        text = ""
        img = font.render(text, True, WHITE)
        rect = img.get_rect()
        start = timer()
        end = start
        blinked = False
        editing = True
        while editing:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editing = False
            drawHealthMeterLeft(int(left * MAXHEALTH))
            drawHealthMeterBackground(int(background * MAXHEALTH))
            drawHealthMeterRight(int(right * MAXHEALTH))
            wait = 1
            end = timer()
            if (end - start) > wait:
                start = timer()
                if state == -1:
                    alphabet = np.roll(alphabet, 1, 0)
                    write_alphabet(alphabet)
                elif state == 1:
                    alphabet = np.roll(alphabet, -1, 0)
                    write_alphabet(alphabet)
            if blinked == True:
                state = 0
                blinked = False
                text += alphabet[13][0]
                if text == 'EDGE':
                    text += ' IMPULSE :-D'
                img = font.render(text, True, WHITE)
                rect.size = img.get_size()
            pygame.draw.rect(screen, back_color, (0, scr_height / 2 + 180, scr_width-40, 170))
            pygame.draw.rect(screen, WHITE, pygame.Rect(20, (scr_height/2) + 180, scr_width-40, 170), 1, 6)
            rect = img.get_rect()
            rect.topleft = (40, 580)
            screen.blit(img, rect)
            pygame.display.update()
            if bl2 == True:
                pygame.draw.rect(screen, back_color, (0, (scr_height/2) + 88, scr_width, scr_height))
                pygame.display.update()
                editing = False
        return

    screen = pygame.display.set_mode(size)
    pygame.display.update()
    images = []
    path = 'Muse-EEG-main\Images/'
    for image in os.listdir(path):
        if image.startswith('0') and image.endswith('.png'):
            images.append(image)
    img_w_def = 150
    screen.fill(back_color)
    def writeLabels():
        write("Left",       HB_X +  40, scr_height/2+65, WHITE, 24)
        write("Background", HB_X + 130, scr_height/2+65, WHITE, 24)
        write("Right",      HB_X + 280, scr_height/2+65, WHITE, 24)
    writeLabels()
    pygame.draw.rect(screen, GREEN, pygame.Rect((scr_width/2)-(img_w_def/2)-15, (scr_height/2)-(img_w_def/2)-25, 
        img_w_def + 20, img_w_def/1.3), 5, 7)
    clock = pygame.time.Clock()
    start = timer()
    end = start
    nr_images = len(images)
    bl2 = False
    running = True
    while running:
        if bl2 == True:
            running = False
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        if blinked == True:
            write("Chosen", 20, 20, WHITE, 60)
            state = 0
            if images[3][0:3] == '020':
                text_editor()
            elif images[3][0:3] == '010':
                webbrowser.open('https://www.youtube.com/watch?v=HGOiuQUwqEw&ab_channel=REPORTERLIVE')
            elif images[3][0:3] == '000':
                os.system("start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
            elif images[3][0:3] == '001':
                webbrowser.open('https://www.google.co.in/')
            elif images[3][0:3] == '003':
                os.system("start shell:AppsFolder\\Microsoft.BingWeather_8wekyb3d8bbwe!App")
            elif images[3][0:3] == '011':
                os.system("start shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify")
            blinked = False
            
        
                
        else:
            write("Chosen", 20, 20, back_color, 60)
        end = timer()
        if (end - start) > 0.1:
            start = timer()
            images = np.roll(images, state*-1)
            for i in range(nr_images):
                image = pygame.image.load(path + images[i])
                img_width   = image.get_width()
                img_height  = image.get_height()
                IMAGE_SIZE  = (img_w_def, img_w_def * img_height / img_width)
                image       = pygame.transform.scale(image, IMAGE_SIZE)
                IMAGE_POSITION = ((i * (img_w_def + 20)) + 10, 290)
                pygame.draw.rect(screen, back_color, (IMAGE_POSITION[0] + 20,
                    IMAGE_POSITION[1]+112, scr_width, 24))
                write(images[i][4:-4], IMAGE_POSITION[0] + 20, IMAGE_POSITION[1]+112, WHITE, 24)
                screen.blit(image, IMAGE_POSITION)
                large_image = pygame.image.load(path + images[3])
                img_width   = large_image.get_width()
                img_height  = large_image.get_height()
                IMAGE_SIZE  = (img_w_def*2.5, img_w_def*img_height/img_width*2.5)
                large_image = pygame.transform.scale(large_image, IMAGE_SIZE)
                IMAGE_POSITION = ((scr_width/2) - IMAGE_SIZE[0] / 2, 20)
                screen.blit(large_image, IMAGE_POSITION)
        drawHealthMeterLeft(int(left * MAXHEALTH))
        drawHealthMeterBackground(int(background * MAXHEALTH))
        drawHealthMeterRight(int(right * MAXHEALTH))
        pygame.display.flip()
        clock.tick(120)

def init_menu():
    global keyboard, alphabet, surface, background_image
    keyboard = Controller()
    surface = create_example_window('Oracle', size)
    menu = pygame_menu.Menu(
        height=size[1],
        onclose=pygame_menu.events.EXIT,
        theme=pygame_menu.themes.THEME_BLUE,
        title='Oracle',
        width=size[0]
    )
    chars = list(string.ascii_uppercase)
    chars.append(' ')
    def createList(r1, r2):
        return list(range(r1, r2+1))
    numbers = createList(65,90)
    numbers.append(32)
    alphabet = list(zip(chars,numbers))
    menu.add.button('Start', start_the_game)
    menu.add.button('Quit', pygame_menu.events.EXIT)
    menu.mainloop(surface)

def start_the_game() -> None:
    pygame.init()
    pygame.font.init()
    clear_screen()
    show_image()

if __name__ == "__main__":
    size = (1200, 768)
    # Model initialization and LSL-based inference are now commented out,
    # as left/right control is derived from accelerometer OSC data.
    # initiate_tf()
    start_threads()
    init_menu()
