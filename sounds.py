import numpy as np
import scipy.io.wavfile as wavfile
import os

os.makedirs("sounds", exist_ok=True)

def synthesize_lightsaber_swing(filename, duration=0.3, base_freq=250, volume=0.4):
    fs = 44100
    t = np.linspace(0, duration, int(fs * duration), False)
    mod = np.sin(2 * np.pi * 2 * t)  # low freq modulation
    hum = np.sin(2 * np.pi * base_freq * t) * mod
    noise = np.random.normal(0, 0.3, size=hum.shape)
    sound = volume * (hum + 0.2 * noise)
    sound = np.int16(sound / np.max(np.abs(sound)) * 32767)
    wavfile.write(filename, fs, sound)

def synthesize_lightsaber_deflect(filename, duration=0.2, base_freq=600, volume=0.5):
    fs = 44100
    t = np.linspace(0, duration, int(fs * duration), False)
    chirp = np.sin(2 * np.pi * (base_freq + 1000 * t) * t)
    burst = chirp * np.hanning(len(t))
    noise = np.random.normal(0, 0.3, size=burst.shape)
    sound = volume * (burst + 0.2 * noise)
    sound = np.int16(sound / np.max(np.abs(sound)) * 32767)
    wavfile.write(filename, fs, sound)

synthesize_lightsaber_swing("sounds/swing.wav")
synthesize_lightsaber_deflect("sounds/deflect.wav")
