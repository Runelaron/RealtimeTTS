import io
import os
import threading
import tomllib
import wave
from pathlib import Path
from queue import Queue

from loguru import logger
from RealtimeTTS import (
    AzureEngine,
    CoquiEngine,
    EdgeEngine,
    ElevenlabsEngine,
    GTTSEngine,
    KokoroEngine,
    OpenAIEngine,
    PiperEngine,
    StyleTTSVoice,
    SystemEngine,
    TextToAudioStream,
)

from utils import log_helpers as log

log.setup_logger(logger, config=False)

class TTSRequestHandler:
    def __init__(self, engine):
        self.engine = engine
        self.audio_queue = Queue()
        self.stream = TextToAudioStream(
            engine, on_audio_stream_stop=self.on_audio_stream_stop, muted=True
        )
        self.speaking = False

    def on_audio_chunk(self, chunk):
        self.audio_queue.put(chunk)

    def on_audio_stream_stop(self):
        self.audio_queue.put(None)
        self.speaking = False

    def stream_text_to_speech(self, text):
        self.speaking = True
        self.stream.feed(text)
        logger.debug(f"Playing audio for text: {text}")
        print(f'Synthesizing: "{text}"')
        self.stream.play_async(on_audio_chunk=self.on_audio_chunk, muted=True)

    def audio_chunk_generator(self, send_wave_headers):
        first_chunk = False
        try:
            while True:
                chunk = self.audio_queue.get()
                if chunk is None:
                    print("Terminating stream")
                    break
                if not first_chunk:
                    if send_wave_headers:
                        print("Sending wave header")
                        yield self.create_wave_header_for_engine(self.engine)
                    first_chunk = True
                yield chunk
        except Exception as e:
            print(f"Error during streaming: {str(e)}")

    def create_wave_header_for_engine(self, engine):
        _, _, sample_rate = engine.get_stream_info()

        num_channels = 1
        sample_width = 2
        frame_rate = sample_rate

        wav_header = io.BytesIO()
        with wave.open(wav_header, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(frame_rate)

        wav_header.seek(0)
        wave_header_bytes = wav_header.read()
        wav_header.close()

        # Create a new BytesIO with the correct MIME type for Firefox
        final_wave_header = io.BytesIO()
        final_wave_header.write(wave_header_bytes)
        final_wave_header.seek(0)

        return final_wave_header.getvalue()

class TTSBuilder(TTSRequestHandler):

    def __init__(self) -> None:
        # Config settings
        self.conf_folder = "configs"
        self.conf_settings = "settings.toml"
        self.CONFIG = self._parse_config(self.conf_folder, self.conf_settings)

        # Folder settings
        self.write_to_file = self.CONFIG["save_settings"]["save"]
        self.session_folder = self.CONFIG["save_settings"]["folder"]

        # Engine settings
        # HACK Move to system after testing!
        self.current_engine = None
        self.voices = {}
        self.startup_engine = self.CONFIG["general"]["start_engine"]
        self.engines = self._assign_engines(
            self.CONFIG["general"]["supported_engines"]
        )
        self._set_engine(self.startup_engine)

        # Global locks
        self.play_text_to_speech_semaphore = threading.Semaphore(1)
        self.speaking_lock = threading.Lock()
        self.tts_lock = threading.Lock()
        self.gen_lock = threading.Lock()

    def _parse_config(self, folder, file):
        """
        Parse a TOML configuration file using the toml module.

        Args:
            file_path (str): Path to the TOML file.

        Returns:
            dict: Parsed configuration data as a dictionary.
        """
        folder = Path(folder)
        file_path = folder.joinpath(file)
        with open(file_path, "rb") as file:
            config = tomllib.load(file)
        return config

    def _assign_engines(self, engine_list):
        engines = {}
        for engine_name in engine_list:
            if "azure" == engine_name:
                azure_key = os.environ.get("AZURE_SPEECH_KEY")
                azure_region = os.environ.get("AZURE_SPEECH_REGION")
                if azure_key and azure_region:
                    print("Initializing azure engine")
                    self.engines["azure"] = AzureEngine(
                        azure_key, azure_region
                    )

            if "elevenlabs" == engine_name:
                elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY")
                if elevenlabs_key:
                    print("Initializing elevenlabs engine")
                    engines["elevenlabs"] = ElevenlabsEngine(elevenlabs_key)

            if "coqui" == engine_name:
                print("Initializing coqui engine")
                if self.CONFIG["advanced"]["deepspeed"]:
                    engines["coqui"] = CoquiEngine(use_deepspeed=True)
                else:
                    engines["coqui"] = CoquiEngine()

            if "edge" == engine_name:
                print("Initializing edge engine")
                engines["edge"] = EdgeEngine()

            if "gtts" == engine_name:
                print("Initializing gtts engine")
                engines["gtts"] = GTTSEngine()

            if "kokoro" == engine_name:
                import platform

                if platform.system() == "Darwin":
                    from phonemizer.backend.espeak.wrapper import EspeakWrapper

                    EspeakWrapper.set_library(
                        "/opt/homebrew/lib/libespeak-ng.dylib"
                    )
                    print("Setting Espeaker library for macOS.")
                else:
                    print(
                        "This system is not macOS skipping espeaker configuration."
                    )
                print("Initializing kokoro engine")
                engines["kokoro"] = KokoroEngine(
                    kokoro_root="/Users/Code/packs/Kokoro-82M"
                )

            if "openai" == engine_name:
                print("Initializing openai engine")
                engines["openai"] = OpenAIEngine()

            if "piper" == engine_name:
                print("Initializing openai engine")
                engines["piper"] = PiperEngine()

            if "style" == engine_name:
                print("Initializing openai engine")
                engines["stype"] = StyleTTSVoice()

            if "system" == engine_name:
                print("Initializing system engine")
                engines["system"] = SystemEngine()

            # TODO add if engine now found exit.

        for _engine in engines.keys():

            print(f"Retrieving voices for TTS Engine {_engine}")
            try:
                self.voices[_engine] = engines[_engine].get_voices()
            except Exception as e:
                self.voices[_engine] = []
                logger.error(f"Error retrieving voices: {_engine}: {str(e)}")

        return engines

    def _set_engine(self, engine_name):
        if self.current_engine is None:
            self.current_engine = self.engines[engine_name]
        else:
            self.current_engine = self.engines[engine_name]

        # TODO add config for sky
        if self.voices[engine_name]:
            print(f"Voices available for {engine_name} are:")
            print(f"{self.voices[engine_name]}")
            if engine_name == "kokoro":
                # Defaults to af_sky
                self.engines[engine_name].set_voice(
                    self.voices[engine_name][10]
                )
                print(f"Set voice as {self.voices[engine_name][10]}")
            elif engine_name != "gtts":
                self.engines[engine_name].set_voice(
                    self.voices[engine_name][0].name
                )

    def is_browser_request(self, request):
        BROWSER_IDENTIFIERS = [
            "mozilla",
            "chrome",
            "safari",
            "firefox",
            "edge",
            "opera",
            "msie",
            "trident",
        ]
        user_agent = request.headers.get("user-agent", "").lower()
        is_browser = any(
            browser_id in user_agent for browser_id in BROWSER_IDENTIFIERS
        )
        return is_browser

    # FIXME Integrate into class
    def save_file(self, text):
        start_time = ZuluTime.get_zulutime()
        CHANNELS = 1
        SAMPLE_WIDTH = 2
        RATE = 22050

        # Optionally set up WAV file
        if self.write_to_file:
            output_wav_file = f"{start_time}.wav"
            wav_file = wave.open(output_wav_file, "wb")
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(RATE)

        # Queue for chunk storage
        chunk_queue = Queue()
        temp_chunk = []
        # Read data as it becomes available
        for chunk in temp_chunk(chunk_size=None):
            if chunk and self.write_to_file:
                wav_file.writeframes(chunk)
                chunk_queue.put(chunk)
            else:
                chunk_queue.put(chunk)

        # Signal the end of the stream
        chunk_queue.put(None)

    def tts_stream(self, request, text: str):
        with self.tts_lock:
            request_handler = TTSRequestHandler(self.current_engine)
            browser_request = self.is_browser_request(request)

            if self.play_text_to_speech_semaphore.acquire(blocking=False):
                try:
                    threading.Thread(
                        target=request_handler.stream_text_to_speech,
                        args=(text,),
                        daemon=True,
                    ).start()
                finally:
                    self.play_text_to_speech_semaphore.release()

            return request_handler.audio_chunk_generator(browser_request)
