import sounddevice as sd
import queue

audio_queue = queue.Queue()

def callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

def start_mic(sample_rate=16000):
    stream = sd.RawInputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        callback=callback
    )
    stream.start()
    return stream
