"""Library log/warning suppression for the noisy ML/audio dependency stack."""
import contextlib
import logging
import os
import sys
import warnings


def silence_warnings():
    """Suppress noisy library warnings that don't affect runtime behaviour.

    Call once, very early — before importing torch, transformers, TTS, etc.
    Things left un-suppressed: our own [tag] prints, real errors, and the
    objc dyld duplicate-class messages (which print from C before Python
    can install a filter — only stderr-fd redirection would catch them).
    """
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
    # jieba (pulled in by Coqui TTS) imports the deprecated pkg_resources API.
    warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
    logging.getLogger("transformers").setLevel(logging.ERROR)


def allow_xtts_checkpoint_unpickling():
    """Allowlist the config classes bundled inside Coqui's XTTS-v2 checkpoint.

    PyTorch 2.6 flipped torch.load's default to weights_only=True; Coqui TTS
    (unmaintained since 2023) never adopted the new safe-loading API, so the
    checkpoint's embedded config objects get rejected as unpickling-unsafe.
    The checkpoint is Coqui's own official release, downloaded via the TTS
    package itself — safe to trust. Call before the first Speaker() load.
    """
    import torch
    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsArgs, XttsAudioConfig

    torch.serialization.add_safe_globals(
        [XttsConfig, XttsAudioConfig, XttsArgs, BaseDatasetConfig]
    )


@contextlib.contextmanager
def silenced_stdout():
    """Redirect stdout at the fd level for the duration of the block.

    Needed for libraries that bypass Python's print() / logging and write
    straight to fd 1 (Coqui TTS prints '> Using model: xtts' this way).
    """
    saved = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        sys.stdout.flush()
        os.dup2(devnull, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(devnull)
        os.close(saved)
