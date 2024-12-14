# https://github.com/yt-dlp/yt-dlp/pull/11490
from yt_dlp.postprocessor.ffmpeg import FFmpegMetadataPP, FFmpegPostProcessor


@staticmethod
def _options_patched(target_ext):
    audio_only = target_ext in ("opus", "wav")
    yield from FFmpegPostProcessor.stream_copy_opts(not audio_only)
    if audio_only:
        yield from ("-vn", "-acodec", "copy")


FFmpegMetadataPP._options = _options_patched
