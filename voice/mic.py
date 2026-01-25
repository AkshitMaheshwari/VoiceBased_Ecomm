import sounddevice as sd
import queue

audio_queue = queue.Queue()

_stream = None

def callback(indata, frames, time, status):
    audio_queue.put(bytes(indata))

def start_mic(sample_rate=16000):
    global _stream
    _stream = sd.RawInputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        callback=callback
    )
    _stream.start()
    return _stream

def stop_mic():
    global _stream
    if _stream:
        _stream.stop()
        _stream.close()