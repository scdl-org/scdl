"""Copied from
https://github.com/davidfischer-ch/pytoolbox/blob/master/pytoolbox/logging.py
"""


import yt_dlp
import yt_dlp.options

create_parser = yt_dlp.options.create_parser


def parse_patched_options(opts):
    patched_parser = create_parser()
    patched_parser.defaults.update(
        {
            "ignoreerrors": False,
            "retries": 0,
            "fragment_retries": 0,
            "extract_flat": False,
            "concat_playlist": "never",
        }
    )
    yt_dlp.options.create_parser = lambda: patched_parser
    try:
        return yt_dlp.parse_options(opts)
    finally:
        yt_dlp.options.create_parser = create_parser


default_opts = parse_patched_options([]).ydl_opts


def cli_to_api(opts):
    opts = yt_dlp.parse_options(opts).ydl_opts

    diff = {k: v for k, v in opts.items() if default_opts[k] != v}
    if "postprocessors" in diff:
        diff["postprocessors"] = [
            pp for pp in diff["postprocessors"] if pp not in default_opts["postprocessors"]
        ]
    return diff
