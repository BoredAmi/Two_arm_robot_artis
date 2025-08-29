import threading
import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import time


# Default model path and commands (Polish small model used in this repo)
DEFAULT_MODEL_PATH = "vosk-model-small-pl-0.22"
DEFAULT_COMMANDS = ["start", "stop", "uchwyć", "połącz", "karykatura", "portret", "podgląd"]


class VoiceCommandListener:
    """Listens to the microphone and calls a callback with recognized commands.

    Usage:
        def on_cmd(cmd):
            print('Got', cmd)

        listener = VoiceCommandListener(callback=on_cmd)
        listener.start()
        # ... later:
        listener.stop()
    """

    def __init__(self, callback=None, commands=None, model_path=None, samplerate=16000):
        self.callback = callback
        self.commands = commands or DEFAULT_COMMANDS
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.samplerate = samplerate

        self._q = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = None
        self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            # Print status but don't crash
            print("Audio status:", status, flush=True)
        # Put raw bytes into queue
        self._q.put(bytes(indata))

    def _run(self):
        try:
            model = Model(self.model_path)
        except Exception as e:
            print(f"Failed to load VOSK model from '{self.model_path}': {e}")
            return

        rec = KaldiRecognizer(model, self.samplerate)

        try:
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, dtype='int16',
                                   channels=1, callback=self._audio_callback):
                print("Voice listener started. Speak a command...")
                while not self._stop_event.is_set():
                    try:
                        data = self._q.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    if rec.AcceptWaveform(data):
                        try:
                            result = json.loads(rec.Result())
                            text = result.get("text", "").lower().strip()
                        except Exception:
                            text = ""

                        if not text:
                            continue

                        if text in self.commands:
                            print(f"✅ Command recognized: {text}")
                            if self.callback:
                                try:
                                    # Call callback synchronously from listener thread.
                                    # GUI integrations should re-dispatch to the main thread.
                                    self.callback(text)
                                except Exception as cb_e:
                                    print("Callback error:", cb_e)
                        else:
                            # Not one of the exact commands; you can implement fuzzy matching
                            print(f"Heard: '{text}' (ignored)")

        except Exception as e:
            print("Error while listening:", e)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout=1.0):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)


if __name__ == "__main__":
    # Simple CLI test
    def print_cb(cmd):
        print("-> callback():", cmd)

    l = VoiceCommandListener(callback=print_cb)
    l.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping listener...")
        l.stop()
