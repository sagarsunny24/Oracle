"""
carousel_controller.py - Pygame carousel UI integrating with EEG/accelerometer predictions

This module handles the image carousel and responds to EEG/accelerometer predictions
and blink detection, including launching applications when specific images are selected.
"""

import pygame
import pygame_menu
from pygame_menu.examples import create_example_window
import os
import numpy as np
import string
from timeit import default_timer as timer
from pynput.keyboard import Key, Controller
import threading
import time
import webbrowser

class CarouselController:
    def __init__(self, predictor, screen_size=(1200, 768)):
        self.predictor = predictor
        self.size = screen_size
        self.screen = None
        self.back_color = (55, 55, 55)
        self.WHITE = (200, 200, 200)
        self.GREEN = (48, 141, 70)
        
        # State variables
        self.state = 0  # -1: left, 0: neutral, 1: right
        self.alphabet = []
        self.keyboard = None
        
        # UI metrics
        self.img_w_def = 150  # default image width
        self.MAXHEALTH = 9  # 0..9 = 10 bars for health bars
        
        # Values for confidence visualization
        self.left = 0
        self.right = 0
        self.background = 0
        
        # App tracking variables
        self.app_open = False
        self.app_type = None
        self.app_open_time = 0
        
        # Initialize pygame
        pygame.init()
        pygame.font.init()
        
    def init_menu(self):
        """Initialize the main menu"""
        self.keyboard = Controller()
        
        # Create alphabet for text editor
        chars = list(string.ascii_uppercase)
        chars.append(' ')
        numbers = list(range(65, 91))
        numbers.append(32)
        self.alphabet = list(zip(chars, numbers))
        
        # Create window and menu
        surface = create_example_window('Mind Reader', self.size)
        
        menu = pygame_menu.Menu(
            height=self.size[1],
            onclose=pygame_menu.events.EXIT,
            theme=pygame_menu.themes.THEME_BLUE,
            title='Mind Reader',
            width=self.size[0]
        )
        
        # Add menu options
        menu.add.button('Play', self.start_the_game)
        menu.add.button('Quit', pygame_menu.events.EXIT)
        
        # Start menu loop
        menu.mainloop(surface)
    
    def clear_screen(self):
        """Clear the Pygame screen"""
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.update()
    
    def write(self, txt, x, y, color, size):
        """Write text to the screen"""
        font = pygame.font.SysFont(None, size)
        img = font.render(txt, True, color)
        self.screen.blit(img, (x, y))
    
    def draw_health_meter_left(self, current_health):
        """Draw left health bar"""
        HB_X = (self.size[0] / 2) - 185
        HB_HEIGHT = 11
        
        # Clear area
        pygame.draw.rect(self.screen, self.back_color, 
                         (HB_X, self.size[1] / 2 + 50, 100 * self.MAXHEALTH, HB_HEIGHT))
        
        # Draw green health bars
        for i in range(current_health):
            pygame.draw.rect(self.screen, self.GREEN, 
                             (HB_X + (10 * self.MAXHEALTH) - (i * 10), self.size[1] / 2 + 50, 20, HB_HEIGHT))
        
        # Draw white outlines
        for i in range(self.MAXHEALTH):
            pygame.draw.rect(self.screen, self.WHITE, 
                             (HB_X + (10 * self.MAXHEALTH) - (i * 10), self.size[1] / 2 + 50, 20, HB_HEIGHT), 1)
    
    def draw_health_meter_background(self, current_health):
        """Draw background health bar"""
        HB_X = (self.size[0] / 2) - 185
        HB_HEIGHT = 11
        
        cH = current_health
        
        # Draw green health bars
        for i in range(cH):
            pygame.draw.rect(self.screen, self.GREEN, 
                             ((self.size[0]/2) - (5*cH) + (i*10)-10, self.size[1] / 2 + 50, 20, HB_HEIGHT))
        
        # Draw white outlines
        for i in range(self.MAXHEALTH):
            pygame.draw.rect(self.screen, self.WHITE, 
                             (HB_X+120 + (10 * self.MAXHEALTH) - i * 10, self.size[1] / 2 + 50, 20, HB_HEIGHT), 1)
    
    def draw_health_meter_right(self, current_health):
        """Draw right health bar"""
        HB_X = (self.size[0] / 2) - 185
        HB_HEIGHT = 11
        
        # Draw green health bars
        for i in range(current_health):
            pygame.draw.rect(self.screen, self.GREEN, 
                             (HB_X+160 + (10 * self.MAXHEALTH) + i * 10, self.size[1] / 2 + 50, 20, HB_HEIGHT))
        
        # Draw white outlines
        for i in range(self.MAXHEALTH):
            pygame.draw.rect(self.screen, self.WHITE, 
                             (HB_X+160 + (10 * self.MAXHEALTH) + i * 10, self.size[1] / 2 + 50, 20, HB_HEIGHT), 1)
    
    def write_alphabet(self, char_list):
        """Write alphabet to screen"""
        pygame.draw.rect(self.screen, self.back_color, 
                         (0, self.size[1] / 2 + 100, self.size[0], 35))
        
        i = 0
        for c in char_list:
            self.write(c[0], 50 + (i*40), self.size[1]/2 + 100, self.WHITE, 60)
            i += 1
    
    def open_application(self, app_code):
        """Open applications based on image code"""
        print(f"Opening application with code: {app_code}")
        
        # Handle different application types
        if app_code == '001':  # Text Editor
            return "text_editor", None
        if app_code == '020':  # Text Editor
            return "text_editor", None
        elif app_code == '010':  # YouTube
            url = 'https://www.youtube.com/watch?v=HGOiuQUwqEw&ab_channel=REPORTERLIVE'
            try:
                webbrowser.open(url)
                print(f"Opened browser with URL: {url}")
                return "browser", url
            except Exception as e:
                print(f"Failed to open browser: {e}")
                return None, None
        elif app_code == '000':  # WhatsApp
            try:
                os.system("start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
                return "windows_app", "WhatsApp"
            except Exception as e:
                print(f"Failed to open WhatsApp: {e}")
                return None, None
        elif app_code == '001':  # Google
            url = 'https://www.google.co.in/'
            try:
                webbrowser.open(url)
                print(f"Opened browser with URL: {url}")
                return "browser", url
            except Exception as e:
                print(f"Failed to open browser: {e}")
                return None, None
        elif app_code == '003':  # Weather
            try:
                os.system("start shell:AppsFolder\\Microsoft.BingWeather_8wekyb3d8bbwe!App")
                return "windows_app", "Weather"
            except Exception as e:
                print(f"Failed to open Weather app: {e}")
                return None, None
        elif app_code == '011':  # Spotify
            try:
                os.system("start shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify")
                return "windows_app", "Spotify"
            except Exception as e:
                print(f"Failed to open Spotify: {e}")
                return None, None
        else:
            print(f"Unknown app code: {app_code}")
            return None, None
    
    def close_application(self, app_type):
        """Close applications based on type"""
        print(f"Attempting to close application of type: {app_type}")
        if app_type in ["browser", "windows_app"]:
            # Send Alt+F4 to close the current window
            self.keyboard.press(Key.alt)
            self.keyboard.press(Key.f4)
            self.keyboard.release(Key.f4)
            self.keyboard.release(Key.alt)
        return False  # Return app_open status
    
    def text_editor(self):
        """Run the text editor interface"""
        font = pygame.font.SysFont(None, 60)
        
        # Drawing selector Rectangle
        pygame.draw.rect(self.screen, self.GREEN, pygame.Rect(
            (self.size[0]/2)-35, (self.size[1]/2) + 88, 40, 60), 4, 6)
        
        self.write_alphabet(self.alphabet)
        
        # Text editor frame
        pygame.draw.rect(self.screen, self.WHITE, pygame.Rect(
            20, (self.size[1]/2) + 180, self.size[0]-40, 170), 1, 6)
        
        text = ""
        img = font.render(text, True, self.WHITE)
        rect = img.get_rect()
        
        start = timer()
        editing = True
        
        print("Text editor opened")
        
        while editing:
            # Check for exit event
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editing = False
            
            # Update prediction confidence visuals
            self.draw_health_meter_left(int(self.left * self.MAXHEALTH))
            self.draw_health_meter_background(int(self.background * self.MAXHEALTH))
            self.draw_health_meter_right(int(self.right * self.MAXHEALTH))
            
            # Check EEG prediction
            prediction = self.predictor.get_next_prediction()
            if prediction:
                result, confidence = prediction
                if result == "left":
                    self.left = confidence
                    self.right = 0
                    self.state = -1
                elif result == "right":
                    self.right = confidence
                    self.left = 0
                    self.state = 1
                else:
                    self.background = confidence
                    self.state = 0
            
            # Check blink status
            blink_status = self.predictor.get_blink_status()
            blinked = blink_status['blinked']
            bl2 = blink_status['double_blink']
            
            wait = 1  # Wait time in seconds
            end = timer()
            
            # Scroll alphabet based on state
            if (end - start) > wait:
                start = timer()
                if self.state == -1:
                    self.alphabet = np.roll(self.alphabet, 1, 0)
                    self.write_alphabet(self.alphabet)
                    pygame.display.update()  # Added display update
                elif self.state == 1:
                    self.alphabet = np.roll(self.alphabet, -1, 0)
                    self.write_alphabet(self.alphabet)
                    pygame.display.update()  # Added display update
            
            # Handle blink selection
            if blinked:
                print("Blink detected in text editor")
                self.state = 0
                text += self.alphabet[13][0]
                if text == 'EDGE':
                    text += ' IMPULSE :-D'
                img = font.render(text, True, self.WHITE)
            
            # Clear text area and redraw
            pygame.draw.rect(self.screen, self.back_color, 
                             (0, self.size[1] / 2 + 180, self.size[0]-40, 170))
            pygame.draw.rect(self.screen, self.WHITE, pygame.Rect(
                20, (self.size[1]/2) + 180, self.size[0]-40, 170), 1, 6)
            
            rect = img.get_rect()
            rect.topleft = (40, 580)
            self.screen.blit(img, rect)
            pygame.display.update()
            
            # Exit on double blink
            if bl2:
                print("Double blink detected - exiting text editor")
                pygame.draw.rect(self.screen, self.back_color, 
                                (0, (self.size[1]/2) + 88, self.size[0], self.size[1]))
                pygame.display.update()
                editing = False
            
            # Add a small delay to avoid CPU hogging
            pygame.time.delay(50)
        
        print("Text editor closed:", text)
        return text
    
    def show_image(self):
        """Show and control the image carousel"""
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.update()
        
        # Find images
        images = []
        path = 'Images/'
        for image in os.listdir(path):
            if image.startswith('0') and image.endswith('.png'):
                images.append(image)
        
        # Set up display
        self.screen.fill(self.back_color)
        
        # Write labels
        HB_X = (self.size[0] / 2) - 185
        self.write("Left", HB_X + 40, self.size[1]/2+65, self.WHITE, 24)
        self.write("Background", HB_X + 130, self.size[1]/2+65, self.WHITE, 24)
        self.write("Right", HB_X + 280, self.size[1]/2+65, self.WHITE, 24)
        
        # Draw selector rectangle
        pygame.draw.rect(self.screen, self.GREEN, pygame.Rect(
            (self.size[0]/2)-(self.img_w_def/2)-15, (self.size[1]/2)-(self.img_w_def/2)-25,
            self.img_w_def + 20, self.img_w_def/1.3), 5, 7)
        
        clock = pygame.time.Clock()
        start = timer()
        nr_images = len(images)
        
        # Start the image carousel loop
        running = True
        while running:
            # Check for exit events
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Check EEG prediction
            prediction = self.predictor.get_next_prediction()
            if prediction:
                result, confidence = prediction
                if result == "left":
                    self.left = confidence
                    self.right = 0
                    self.state = -1
                elif result == "right":
                    self.right = confidence
                    self.left = 0
                    self.state = 1
                else:
                    self.background = confidence
                    self.state = 0
            
            # Check blink status
            blink_status = self.predictor.get_blink_status()
            blinked = blink_status['blinked']
            bl2 = blink_status['double_blink']
            
            # Handle double blink - close app or exit carousel
            if bl2:
                if self.app_open:
                    self.app_open = self.close_application(self.app_type)
                else:
                    running = False
            
            # Handle blink selection - open app or perform action
            if blinked:
                self.write("Chosen", 20, 20, self.WHITE, 60)
                self.state = 0
                
                # Only proceed with opening apps if no app is currently open
                if not self.app_open:
                    # Get the app code from the selected image
                    app_code = images[3][0:3]
                    self.app_type, app_info = self.open_application(app_code)
                    
                    # Handle text editor specially
                    if self.app_type == "text_editor":
                        print("Launching text editor...")
                        search_text = self.text_editor()
                        if search_text and search_text.strip():
                            print(f"Searching Google for: {search_text}")
                            search_url = f'https://www.google.com/search?q={search_text.replace(" ", "+")}'
                            try:
                                webbrowser.open(search_url)
                                self.app_open = True
                                self.app_type = "browser"
                                self.app_open_time = timer()
                            except Exception as e:
                                print(f"Failed to open Google search: {e}")
                    elif self.app_type:  # If we successfully opened an app
                        self.app_open = True
                        self.app_open_time = timer()
            else:
                self.write("Chosen", 20, 20, self.back_color, 60)
            
            # Display app status if one is open
            if self.app_open:
                self.write("App Open - Double blink to close", 10, 50, self.GREEN, 30)
                
            # Update image carousel
            end = timer()
            if (end - start) > 0.1:
                start = timer()
                
                # Rotate images based on state
                images = np.roll(images, self.state*-1)
                
                # Display images
                for i in range(nr_images):
                    image_path = path + images[i]
                    image = pygame.image.load(image_path)
                    
                    # Scale image
                    img_width = image.get_width()
                    img_height = image.get_height()
                    IMAGE_SIZE = (self.img_w_def, self.img_w_def * img_height / img_width)
                    image = pygame.transform.scale(image, IMAGE_SIZE)
                    
                    # Position image
                    IMAGE_POSITION = ((i * (self.img_w_def + 20)) + 10, 290)
                    
                    # Clear description area
                    pygame.draw.rect(self.screen, self.back_color, 
                                     (IMAGE_POSITION[0] + 20, IMAGE_POSITION[1]+112, self.size[0], 24))
                    
                    # Write image description
                    self.write(images[i][4:-4], IMAGE_POSITION[0] + 20,
                               IMAGE_POSITION[1]+112, self.WHITE, 24)
                    
                    # Display image
                    self.screen.blit(image, IMAGE_POSITION)
                    
                    # Enlarge center image
                    large_image = pygame.image.load(path + images[3])
                    img_width = large_image.get_width()
                    img_height = large_image.get_height()
                    IMAGE_SIZE = (self.img_w_def*2.5, self.img_w_def*img_height/img_width*2.5)
                    large_image = pygame.transform.scale(large_image, IMAGE_SIZE)
                    IMAGE_POSITION = ((self.size[0]/2) - IMAGE_SIZE[0] / 2, 20)
                    self.screen.blit(large_image, IMAGE_POSITION)
            
            # Update health bars
            self.draw_health_meter_left(int(self.left * self.MAXHEALTH))
            self.draw_health_meter_background(int(self.background * self.MAXHEALTH))
            self.draw_health_meter_right(int(self.right * self.MAXHEALTH))
            
            # Update display
            pygame.display.flip()
            clock.tick(120)
    
    def start_the_game(self):
        """Start the game"""
        self.clear_screen()
        self.show_image()
