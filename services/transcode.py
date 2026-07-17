import bencodepy
import errno
import os
import os.path as path
import re
import shlex
import shutil
import signal
import subprocess
import unicodedata

from typing import Callable, Optional
import logging

LOGGER = logging.getLogger("transcode")

import mutagen.flac

from . import tagging

import models.format
from models import Torrent, TorrentGroup, Format
from models.exceptions import TranscodeException, TranscodeDownmixException, UnknownSampleRateException

# In most Unix shells, pipelines only report the return code of the
# last process. We need to know if any process in the transcode
# pipeline fails, not just the last one.
#
# This function constructs a pipeline of processes from a chain of
# commands just like a shell does, but it returns the status code (and
# stderr) of every process in the pipeline, not just the last one. The
# results are returned as a list of (code, stderr) pairs, one pair per
# process.
def run_pipeline(cmds: list[str]) -> list[tuple[int, str]]:
    # The Python executable (and its children) ignore SIGPIPE. (See
    # http://bugs.python.org/issue1652) Our subprocesses need to see
    # it.
    sigpipe_handler = signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    stdin = None
    last_proc = None
    procs = []
    try:
        for cmd in cmds:
            proc = subprocess.Popen(
                shlex.split(cmd),
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if last_proc is not None and last_proc.stdout is not None:
                # Ensure last_proc receives SIGPIPE if proc exits first
                last_proc.stdout.close()
            procs.append(proc)
            stdin = proc.stdout
            last_proc = proc
    finally:
        signal.signal(signal.SIGPIPE, sigpipe_handler)

    if last_proc is None:
        LOGGER.warning('No commands run.')
        return []

    _, stderr = last_proc.communicate()

    results: list[tuple[int, str]] = []
    for cmd, proc in zip(cmds[:-1], procs[:-1]):
        # wait() is OK here, despite use of PIPE above; these procs
        # are finished.
        proc.wait()
        results.append((proc.returncode, proc.stderr.read()))
    results.append((last_proc.returncode, stderr))
    return results


def locate(root: str, match_function: Callable[[str], bool], ignore_dotfiles:bool=True):
    """
    Yields all filenames within the root directory for which match_function returns True.
    """
    for path, _, files in os.walk(root):
        for filename in (
            os.path.abspath(os.path.join(path, filename))
            for filename in files
            if match_function(filename)
        ):
            if ignore_dotfiles and os.path.basename(filename).startswith("."):
                pass
            else:
                yield filename


def ext_matcher(*extensions: str) -> Callable[[str], bool]:
    """
    Returns a function which checks if a filename has one of the specified extensions. Expects a string in the format '.ext'.
    """
    return lambda f: os.path.splitext(f)[-1].lower() in extensions


def is_24bit(flac_dir: str) -> bool:
    """
    Returns True if any FLAC within flac_dir is 24 bit.
    """
    flacs = (
        mutagen.flac.FLAC(flac_file)
        for flac_file in locate(flac_dir, ext_matcher(".flac"))
    )
    return any(flac.info.bits_per_sample > 16 for flac in flacs)


def is_multichannel(flac_dir: str) -> bool:
    """
    Returns True if any FLAC within flac_dir is multichannel.
    """
    flacs = (
        mutagen.flac.FLAC(flac_file)
        for flac_file in locate(flac_dir, ext_matcher(".flac"))
    )
    return any(flac.info.channels > 2 for flac in flacs)


def needs_resampling(flac_dir: str):
    """
    Returns True if any FLAC within flac_dir needs resampling when
    transcoded.
    """
    return is_24bit(flac_dir)


def resample_rate(flac_dir: str) -> int | None:
    """
    Returns the rate to which the release should be resampled.
    """
    flacs = (
        mutagen.flac.FLAC(flac_file)
        for flac_file in locate(flac_dir, ext_matcher(".flac"))
    )
    original_rate: int = max(flac.info.sample_rate for flac in flacs) # type: ignore
    if original_rate % 44100 == 0:
        return 44100
    elif original_rate % 48000 == 0:
        return 48000
    else:
        return None


def transcode_commands(
    output_format: Format,
    resample: bool,
    needed_sample_rate: Optional[int],
    flac_file: str,
    transcode_file: str,
):
    """
    Return a list of transcode steps (one command per list element),
    which can be used to create a transcode pipeline for flac_file ->
    transcode_file using the specified output_format, plus any
    resampling, if needed.
    """
    if resample:
        flac_decoder = "sox {FLAC} -G -b 16 -t wav - rate -v -L {SAMPLERATE} dither"
    else:
        flac_decoder = "flac -dcs -- {FLAC}"

    transcoding_steps = [flac_decoder]

    encoder = output_format.encoder
    if encoder is None:
        raise TranscodeException(f'Missing encoder data for format {output_format.long_name}')

    match encoder.enc:
        case "lame":
            lame_encoder = "lame -S {OPTS} - {FILE}"
            transcoding_steps.append(lame_encoder)
        case "flac":
            flac_encoder = "flac {OPTS} -o {FILE} -"
            transcoding_steps.append(flac_encoder)
        case _:
            raise TranscodeException(f"Encoder out of valid range: {encoder}")

    transcode_args: dict[str, str | int | None] = {
        "FLAC": shlex.quote(flac_file),
        "FILE": shlex.quote(transcode_file),
        "OPTS": encoder.opts,
        "SAMPLERATE": needed_sample_rate,
    }

    if output_format.name == "FLAC" and resample:
        commands = [
            "sox {FLAC} -G -b 16 {FILE} rate -v -L {SAMPLERATE} dither".format(
                **transcode_args
            )
        ]
    else:
        commands = map(lambda cmd: cmd.format(**transcode_args), transcoding_steps)

    return commands

def transcode(flac_file: str, output_dir: str, output_format: Format) -> str:
    """
    Transcodes a FLAC file into another format.
    """
    # gather metadata from the flac file
    flac_info = mutagen.flac.FLAC(flac_file)
    sample_rate: int = flac_info.info.sample_rate # type: ignore
    bits_per_sample: int = flac_info.info.bits_per_sample # type: ignore
    resample: bool = sample_rate > 48000 or bits_per_sample > 16 # type: ignore

    # if resampling isn't needed then needed_sample_rate will not be used.
    needed_sample_rate = None

    if resample:
        if sample_rate % 44100 == 0:
            needed_sample_rate = 44100
        elif sample_rate % 48000 == 0:
            needed_sample_rate = 48000
        else:
            raise UnknownSampleRateException(
                'FLAC file "{0}" has a sample rate {1}, which is not 88.2, 176.4, 96, or 192kHz but needs resampling, this is unsupported'.format(flac_file, sample_rate)
            )

    if flac_info.info.channels > 2:
        raise TranscodeDownmixException(
            'FLAC file "{0}" has more than 2 channels, unsupported'.format(flac_file)
        )

    # determine the new filename
    transcode_basename = path.splitext(os.path.basename(flac_file))[0]
    transcode_basename = re.sub(r'[\?<>\\*\|":]', "_", transcode_basename)
    transcode_file = path.join(output_dir, transcode_basename)


    if output_format.encoder is not None:
        transcode_file += output_format.encoder.ext
    else:
        raise TranscodeException(f'Missing encoder data for format {output_format.long_name}')

    if not os.path.exists(path.dirname(transcode_file)):
        try:
            os.makedirs(path.dirname(transcode_file))
        except OSError as e:
            if e.errno == errno.EEXIST:
                # Harmless race condition -- another transcode process
                # beat us here.
                pass
            else:
                raise e

    commands = list(
        transcode_commands(
            output_format, resample, needed_sample_rate, flac_file, transcode_file
        )
    )
    results = run_pipeline(commands)

    # Check for problems. Because it's a pipeline, the earliest one is
    # usually the source. The exception is -SIGPIPE, which is caused
    # by "backpressure" due to a later command failing: ignore those
    # unless no other problem is found.
    last_sigpipe = None
    for cmd, (code, stderr) in zip(commands, results):
        if code:
            if code == -signal.SIGPIPE:
                last_sigpipe = (cmd, (code, stderr))
            else:
                raise TranscodeException(
                    'Transcode of file "{0}" failed: {1}'.format(flac_file, stderr)
                )
    if last_sigpipe:
        # XXX: this should probably never happen....
        raise TranscodeException(
            'Transcode of file "{0}" failed: SIGPIPE'.format(flac_file)
        )

    tagging.copy_tags(flac_file, transcode_file)
    (ok, msg) = tagging.check_tags(transcode_file)
    if not ok:
        raise TranscodeException("Tag check failed on transcoded file: {0}".format(msg))

    return transcode_file


def get_transcode_dir(flac_dir: str, output_dir: str, output_format: str, resample: bool) -> str:
    full_flac_dir = flac_dir
    transcode_dir = path.basename(flac_dir)
    flac_dir = transcode_dir

    def some_check(string: str):
        return string in flac_dir.upper() and (
            (flac_dir.upper().count("24") >= 2)
            or (not any(s in flac_dir for s in some_numbers))
        )

    def replace_insensitive(pattern: str, replacement: str, source: str):
        return re.sub(re.compile(pattern, re.I), replacement, source)

    # This is what happens when you spend your time transcoding 24 bit to 16 for
    # perfect FLACs.
    some_numbers = ("44", "88", "176", "48", "96", "192")
    list_of_flac = ["FLAC", "FLAC HD", "HD FLAC"]
    list_of_24_flac = [
        "FLAC 24-BIT",
        "FLAC-24BIT",
        "FLAC-24",
        "FLAC 24BIT",
        "FLAC 24 BIT",
        "FLAC, 24BIT",
        "FLAC, 24 BIT",
        "FLAC, 24-BIT",
        "FLAC 24",
        "FLAC24",
        "FLAC96",
        "24-BIT FLAC",
        "24-BIT LOSSLESS FLAC",
        "24BIT FLAC",
        "24 BIT FLAC",
        "24FLAC",
        "24 FLAC",
        "24 BITS",
        "24-BITS",
        "24BITS",
        "24BIT",
        "24 BIT",
        "24-BIT",
    ]

    for flac in list_of_flac:
        if flac in flac_dir.upper():
            transcode_dir = replace_insensitive(flac, output_format, transcode_dir)
            break

    for flac in list_of_24_flac:
        if some_check(flac):
            transcode_dir = replace_insensitive(flac, output_format, transcode_dir)
            break

    transcode_dir = f"{transcode_dir}({output_format})"
    if output_format != "FLAC":
        transcode_dir = replace_insensitive("FLAC", "", transcode_dir)

    if resample:
        rate = resample_rate(full_flac_dir)
        if rate == 44100:
            if "24" in flac_dir and "176.4" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("176.4", "44")
            elif "24" in flac_dir and "176 4" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("176 4", "44")
            elif "24" in flac_dir and "176" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("176", "44")
            elif "24" in flac_dir and "88.2" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("88.2", "44")
            elif "24" in flac_dir and "88 2" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("88 2", "44")
            elif "24" in flac_dir and "88" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("88", "44")
            elif "24" in flac_dir and "44.1" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("44.1", "44")
            elif "24" in flac_dir and "44 1" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("44 1", "44")
            elif "24" in flac_dir and "44" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
            else:
                transcode_dir += " [16-44]"
        elif rate == 48000:
            if "24" in flac_dir and "192" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("192", "48")
            elif "24" in flac_dir and "96" in flac_dir:
                # XXX: theoretically, this could replace part of the album title too.
                # e.g. "24 days in 96 castles - [24-96]" would become "16 days in 44 castles - [16-44]"
                transcode_dir = transcode_dir.replace("24", "16")
                transcode_dir = transcode_dir.replace("96", "48")
            elif "24" in flac_dir and "48" in flac_dir:
                transcode_dir = transcode_dir.replace("24", "16")
            else:
                transcode_dir += " [16-48]"

    return os.path.join(output_dir, transcode_dir)


def transcode_release(
    flac_dir: str,
    output_dir: str,
    output_format: Format,
    source_torrent: Torrent,
    source_torrent_group: TorrentGroup,
):
    """
    Transcode a FLAC release into another format.
    """
    flac_dir = os.path.abspath(flac_dir)
    output_dir = os.path.abspath(output_dir)
    flac_files = locate(flac_dir, ext_matcher(".flac"))

    # check if we need to resample
    resample = needs_resampling(flac_dir)

    # check if we need to encode
    if output_format.name == 'FLAC' and not resample:
        # XXX: if output_dir is not the same as flac_dir, this may not
        # do what the user expects.
        if output_dir != os.path.dirname(flac_dir):
            logging.info(
                "Warning: no encode necessary, so files won't be placed in", output_dir
            )
        return flac_dir

    # make a new directory for the transcoded files
    #
    # NB: The cleanup code that follows this block assumes that
    # transcode_dir is a new directory created exclusively for this
    # transcode. Do not change this assumption without considering the
    # consequences!
    transcode_dir = os.path.join(output_dir, source_torrent_group.get_transcode_dirname(source_torrent, output_format))
    logging.info("    " + transcode_dir)
    if not os.path.exists(transcode_dir):
        os.makedirs(transcode_dir)
    else:
        return transcode_dir
        # raise TranscodeException('transcode output directory "%s" already exists' % transcode_dir)

    try:
        arg_list = [
            (
                filename,
                path.dirname(filename).replace(flac_dir, transcode_dir),
                output_format,
            )
            for filename in flac_files
        ]
        for filename, output_dir, output_format in arg_list:
            transcode(filename, output_dir, output_format)
            try:
                print_filename = filename.rsplit("/",1)[1]
            except ValueError:
                print_filename = filename
            LOGGER.info(f"      Processing: {print_filename}")

        # copy other files
        allowed_extensions = [
            ".cue", ".gif", ".jpeg", ".jpg",
            ".log", ".md5", ".nfo", ".pdf",
            ".png", ".sfv", ".txt",
        ]
        allowed_files = locate(flac_dir, ext_matcher(*allowed_extensions))
        for filename in allowed_files:
            new_dir = os.path.dirname(filename).replace(flac_dir, transcode_dir)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            shutil.copy(filename, new_dir)

        return transcode_dir

    except:
        # Cleanup.
        #
        # ASSERT: transcode_dir was created by this function and does
        # not contain anything other than the transcoded files!
        shutil.rmtree(transcode_dir)
        raise

def normalize_torrent_metadata(torrent):
    with open(torrent, "rb") as f:
        data = bencodepy.decode(f.read())

    info = data[b"info"]
    if b"files" in info:  # multi-file torrent
        for f_entry in info[b"files"]:
            f_entry[b"path"] = [
                unicodedata.normalize("NFC", p.decode("utf-8")).encode("utf-8")
                for p in f_entry[b"path"]
            ]
    elif b"name" in info:  # single-file torrent
        info[b"name"] = unicodedata.normalize("NFC", info[b"name"].decode("utf-8")).encode("utf-8")

    with open(torrent, "wb") as f:
        f.write(bencodepy.encode(data))

    print(f"Normalized torrent metadata in: {torrent}")

def make_torrent(input_dir: str, output_dir: str, tracker: str, passkey: str, source: str | None) -> str:
    torrent = os.path.join(output_dir, path.basename(input_dir)) + ".torrent"
    if not path.exists(path.dirname(torrent)):
        os.makedirs(path.dirname(torrent))
    tracker_url = f"{tracker}{passkey}/announce"
    if source == None:
        command = ["mktorrent", "-p", "-a", tracker_url, "-o", torrent, input_dir]
    else:
        command = ["mktorrent", "-p", "-s", source, "-a", tracker_url, "-o", torrent, input_dir]
    subprocess.check_output(command, stderr=subprocess.STDOUT)

    # Normalization needed on MacOS, see https://github.com/pobrn/mktorrent/issues/14
    normalize_torrent_metadata(torrent)
    return torrent