"""
main.py - Main entry point for the EEG-controlled Image Carousel

This script integrates the PeriodicPredictor and CarouselController
to create a unified EEG-controlled interface.
"""

import multiprocessing
import os
from periodic_predictor import PeriodicPredictor
from carousel_controller import CarouselController

def main():
    # Ensure proper directory structure
    if not os.path.exists('Images'):
        os.makedirs('Images')
        print("Created Images directory. Please add images with names starting with '0' and ending with '.png'")
    
    # Path to the EEGITNet model
    model_path = 'Models\EEG-ITNet\model.h5'
    
    # Check if model exists
    if not os.path.exists(model_path):
        parent_dir = os.path.dirname(model_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        print(f"Model not found at {model_path}. Please place the EEGITNet model there.")
        return
    
    # Initialize predictor with model
    predictor = PeriodicPredictor(model_path=model_path)
    
    # Start OSC server to receive EEG data
    server_thread = predictor.start_server()
    
    # Initialize carousel controller with predictor
    controller = CarouselController(predictor)
    
    try:
        # Start the Pygame menu and interface
        controller.init_menu()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # Clean up resources
        predictor.stop()
        
if __name__ == "__main__":
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
    