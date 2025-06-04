import multiprocessing
import threading
import numpy as np
import pandas as pd
import mne
import tensorflow as tf
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from timeit import default_timer as timer


def _inference_worker(model_path, input_queue, output_queue, wait_flag,
                      fs, window_duration, window_overlap):
    """
    Top-level inference worker for EEG predictions.
    Runs in a separate process and only receives simple, picklable arguments.
    """
    print(f"Loading model from {model_path}")
    model = tf.keras.models.load_model(model_path)
    print("Model loaded successfully")

    while True:
        # Wait for the main thread to feed data
        while wait_flag.value != 0:
            pass

        # Retrieve raw EEG window
        raw_data = input_queue.get()

        # Convert to DataFrame
        df = pd.DataFrame(raw_data, columns=["TP9", "AF7", "AF8", "TP10"])

        # MNE preprocessing
        mne.set_log_level(verbose=False, return_old_level=False)
        info = mne.create_info(list(df.columns), ch_types=['eeg'] * df.shape[1], sfreq=fs)
        info.set_montage('standard_1020')
        raw = mne.io.RawArray(df.T, info)
        raw.set_eeg_reference()
        epochs = mne.make_fixed_length_epochs(raw, duration=window_duration)
        x = epochs.get_data()[:, :, :, np.newaxis]

        # Predict
        y = model.predict(x)
        if y[0][0] > y[0][1]:
            result, conf = "left", float(y[0][0])
        else:
            result, conf = "right", float(y[0][1])

        print(f"Predicted: {result} with confidence = {conf:.3f}")
        output_queue.put((result, conf))

        # Signal ready for next window
        wait_flag.value = 1


class PeriodicPredictor:
    """
    Handles EEG data collection via OSC and delegates prediction
    to a separate process using the module-level `_inference_worker`.
    """

    def __init__(self, model_path='Models/EEGITNet/model.h5', ip="0.0.0.0", port=5000):
        # Configuration
        self.ip = ip
        self.port = port
        self.model_path = model_path

        # EEG parameters
        self.fs = 256
        self.n_channels = 4
        self.window_duration = 1
        self.window_overlap = 0.2

        # Buffers
        self.buffer_main = np.empty((0, self.n_channels))

        # Recording state
        self.recording = False
        self.lock = False

        # IPC with inference process
        self.prediction_input_queue = multiprocessing.Queue()
        self.prediction_output_queue = multiprocessing.Queue()
        self.wait_flag = multiprocessing.Value('i', 1)

        # OSC setup
        self.dispatcher = Dispatcher()
        self.dispatcher.map("/muse/eeg", self.eeg_handler)
        self.dispatcher.map("/Marker/*", self.marker_handler)
        self.dispatcher.map("/muse/elements/blink", self.blink_handler)
        self.dispatcher.map("/muse/elements/jaw_clench", self.jaw_handler)

        # Blink tracking
        self.blinks = 0
        self.blinked = False
        self.bl2 = False
        self.blink_times = []
        self.jaw_clenches = 0
        self.server = None
        self.inference_process = None

    def blink_handler(self, address, *args):
        t = timer()
        self.blink_times.append(t)
        single = False
        if len(self.blink_times) >= 2:
            if (t - self.blink_times[-2]) < 0.7:
                self.bl2 = True
            else:
                single = True
        if single:
            self.blinked = True
        print("Blink event")

    def jaw_handler(self, address, *args):
        self.jaw_clenches += 1
        print("Jaw clench event")

    def eeg_handler(self, address, *args):
        if self.recording and not self.lock:
            self.buffer_main = np.append(self.buffer_main, [args[:4]], axis=0)
            if self.buffer_main.shape[0] >= self.window_duration * self.fs:
                self.lock = True
                window = self.buffer_main[:int(self.window_duration * self.fs)]
                # retain overlap
                keep = int(self.window_duration * (1 - self.window_overlap*0.5) * self.fs)
                self.buffer_main = self.buffer_main[-keep:]
                self.prediction_input_queue.put(window)
                self.wait_flag.value = 0
                self.lock = False

    def marker_handler(self, address, *args):
        marker = address[-1]
        if marker == '1':
            self.recording = True
            print("Recording started")
        elif marker == '2':
            self.recording = False
            if self.server:
                self.server.shutdown()
            print("Recording stopped")

    def start_server(self):
        """Launch OSC server thread and inference process."""
        self.server = ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        print(f"Listening on {self.ip}:{self.port}")
        server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        server_thread.start()

        # Start separate process for inference
        self.inference_process = multiprocessing.Process(
            target=_inference_worker,
            args=(
                self.model_path,
                self.prediction_input_queue,
                self.prediction_output_queue,
                self.wait_flag,
                self.fs,
                self.window_duration,
                self.window_overlap
            )
        )
        self.inference_process.start()
        return server_thread

    def stop(self):
        if self.server:
            self.server.shutdown()
        if self.inference_process:
            self.inference_process.terminate()

    def get_blink_status(self):
        status = {'blinked': self.blinked, 'double_blink': self.bl2}
        self.blinked = False
        self.bl2 = False
        return status

    def get_next_prediction(self):
        if not self.prediction_output_queue.empty():
            return self.prediction_output_queue.get()
        return None
