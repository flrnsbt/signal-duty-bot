from kokoro import KPipeline
from . import config

def generate_french_audio(text: str, output_path: str):
    # 'f' signifie français
    pipeline = KPipeline(lang_code='f') 
    generator = pipeline(text, voice=config.KOKORO_VOICE, speed=config.KOKORO_SPEED)
    
    for _, _, audio in generator:
        import soundfile as sf
        sf.write(output_path, audio, 24000)