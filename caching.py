import hashlib
import logging
import os
import pickle
import sys
from functools import wraps
from inspect import signature
from typing import List, Optional, Tuple


def init_logger():
    logger = logging.getLogger("caching")
    logger.setLevel(logging.INFO)
    fmt_str = "[%(asctime)s] - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt_str)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)


init_logger()
logger = logging.getLogger("caching")

_CACHE_DIR = None
_HASH = True


def set_cache_dir(cache_dir: str):
    logger.info(f"Setting cache directory to: {cache_dir}")
    global _CACHE_DIR
    _CACHE_DIR = cache_dir


def get_cache_dir():
    global _CACHE_DIR
    if _CACHE_DIR is None:
        raise Exception(
            "Cache directory has not been set yet. "
            "Please set it with set_cache_dir function."
        )
    return _CACHE_DIR


def set_log_level(log_level: int):
    logger = logging.getLogger("caching")
    logger.setLevel(level=log_level)


def set_hash(hash: bool):
    logger.info(f"Setting cache to use hash: {hash}")
    global _HASH
    _HASH = hash


def get_hash():
    global _HASH
    return _HASH


class CacheUsageError(Exception):
    pass


def hash_all(xs: List[str]) -> str:
    hashes = [hashlib.sha512(x.encode("utf-8")).hexdigest() for x in xs]
    return hashlib.sha512("".join(hashes).encode("utf-8")).hexdigest()


def cached(
    cache_keys: Optional[Tuple] = None,
    exclude_args: Optional[Tuple] = None,
):
    """
    Cache the wrapped function.

    The outputs of the wrapped function are cached by pickling them into a
    file whose path is determined by the function's name and it's arguments.
    By default all arguments are used to define the cache key, but a custom
    subset can be provided either via `cache_keys` by inclusion, or via
    `exclude_args` by exclusion.

    Args:
        cache_keys: What arguments to use for the hash key.
        exclude_args: What arguments to exclude from the hash key. E.g.
            n_processes, which does not affect the result of the function.
            If None, nothing will be excluded.
    """

    def f_res(func):
        @wraps(func)
        def r_res_res(*args, **kwargs):
            # Get caching hyperparameters
            cache_dir = get_cache_dir()
            hash = get_hash()

            s = signature(func)
            binding = s.bind(*args, **kwargs)
            binding.apply_defaults()
            # Check that all cache_keys are present - user might have a typo!
            if cache_keys is not None:
                for cache_key in cache_keys:
                    if cache_key not in binding.arguments:
                        raise CacheUsageError(
                            f"{cache_key} is not an argument to "
                            "{func.__name__}. Fix the cache_keys."
                        )
            # Check that all exclude_args are present - user might have a typo!
            if exclude_args is not None:
                for arg in exclude_args:
                    if arg not in binding.arguments:
                        raise CacheUsageError(
                            f"{arg} is not an argument to {func.__name__}. "
                            "Fix the exclude_args."
                        )
            # Only one of cache_keys and exclude_args can be provided
            if cache_keys is not None and exclude_args is not None:
                raise CacheUsageError(
                    "Only one of cache_keys and exclude_args can be provided"
                )
            if not hash:
                path = (
                    [cache_dir]
                    + [f"{func.__name__}"]
                    + [
                        f"{key}_{val}"
                        for (key, val) in binding.arguments.items()
                        if ((cache_keys is None) or (key in cache_keys))
                        and (
                            (exclude_args is None) or (key not in exclude_args)
                        )
                    ]
                    + ["result"]
                )
            else:
                path = (
                    [cache_dir]
                    + [f"{func.__name__}"]
                    + [
                        hash_all(
                            [
                                f"{key}_{val}"
                                for (key, val) in binding.arguments.items()
                                if ((cache_keys is None) or (key in cache_keys))
                                and (
                                    (exclude_args is None)
                                    or (key not in exclude_args)
                                )
                            ]
                        )
                    ]
                    + ["result"]
                )
            success_token_filename = os.path.join(*path) + ".success"
            filename = os.path.join(*path) + ".pickle"
            if os.path.isfile(success_token_filename):
                if not os.path.isfile(filename):
                    raise Exception(
                        "Success token is present but file is missing!: "
                        f"{filename}"
                    )
                with open(filename, "rb") as f:
                    try:
                        return pickle.load(f)
                    except:
                        raise Exception(
                            "Corrupt cache file due to unpickling error, even "
                            f"though success token was present!: {filename}"
                        )
            else:
                if os.path.isfile(filename):
                    assert not os.path.isfile(
                        success_token_filename
                    )  # Should be true because we are in the else statement
                    logger.info(
                        "Success token missing but pickle file is present. "
                        "Thus pickle file is most likely corrupt. "
                        f"Will have to recompute: {filename}"
                    )
                logger.debug(f"Calling {func.__name__}")
                res = func(*args, **kwargs)
                os.makedirs(os.path.join(*path[:-1]), exist_ok=True)
                with open(filename, "wb") as f:
                    pickle.dump(res, f)
                    f.flush()
                with open(success_token_filename, "w") as f:
                    f.write("SUCCESS\n")
                    f.flush()
                return res

        return r_res_res

    return f_res
