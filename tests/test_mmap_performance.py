import functools
import json
import logging
import os
import pickle
import random
import string
import threading
import time
import typing

from pytheus.mmap import MmapDict

LOGGER = logging.getLogger(__name__)

WRITE_ITERATIONS = 2000
READ_ITERATIONS = 100


def test_indexed_writes():

    # 1. Generate samples

    samples = {}
    for _ in range(WRITE_ITERATIONS):
        count = random.randint(1, 50)
        samples["".join(random.sample(string.ascii_letters, count))] = random.uniform(0.0, 10.0)

    # 2. Assert speed

    time_results = {}

    def _timing(f):
        @functools.wraps(f)
        def wrap(*args, **kw):
            start = time.time()
            result = f(*args, **kw)
            elapsed_time = time.time()-start
            time_results[f.__name__] = elapsed_time
            LOGGER.info(f"Function {f.__name__} took {elapsed_time:.4f} seconds")
            return result
        return wrap

    def _launch_threads(*functions: typing.List[typing.Callable]):
        threads = [threading.Thread(target=f) for f in functions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    mmap_file_path = "test.mmap"
    json_file_path = "test.json"
    pickle_file_path = "test.pickle"
    mmap_dict_kwargs = dict(
        file_path=mmap_file_path,
        key_format_string="s",
        value_format_string="d",
        block_size=1 << 20,
        encoding="utf-8",
    )

    def _remove_files_if_present():
        for file_path in [mmap_file_path, json_file_path, pickle_file_path]:
            if os.path.exists(file_path):
                os.remove(file_path)

    _remove_files_if_present()

    mmap_dict_write = MmapDict(**mmap_dict_kwargs)
    json_dict = {}
    json_write_file_handle = open(json_file_path, "w")
    pickle_dict = {}
    pickle_write_file_handle = open(pickle_file_path, "wb")

    @_timing
    def _mmap_random_write():
        for key, value in samples.items():
            mmap_dict_write[key] = value

    @_timing
    def _json_random_write():
        for key, value in samples.items():
            json_dict[key] = value
            json_write_file_handle.write(json.dumps(json_dict, separators=(",", ":")))
            json_write_file_handle.seek(0)

    @_timing
    def _pickle_random_write():
        for key, value in samples.items():
            pickle_dict[key] = value
            pickle.dump(pickle_dict, pickle_write_file_handle, pickle.HIGHEST_PROTOCOL)
            pickle_write_file_handle.seek(0)

    _launch_threads(_mmap_random_write, _json_random_write, _pickle_random_write)

    assert time_results["_mmap_random_write"] < time_results["_json_random_write"]
    assert time_results["_mmap_random_write"] < time_results["_pickle_random_write"]

    # 3. Log file size

    mmap_file_size = os.stat(mmap_file_path).st_size
    json_file_size = os.stat(json_file_path).st_size
    pickle_file_size = os.stat(pickle_file_path).st_size
    LOGGER.info(f"{WRITE_ITERATIONS} write iterations, mmap file size => {mmap_file_size}")
    LOGGER.info(f"{WRITE_ITERATIONS} write iterations, json file size => {json_file_size}")
    LOGGER.info(f"{WRITE_ITERATIONS} write iterations, pickle file size => {pickle_file_size}")

    # 4. Assert speed when reading all keys

    @_timing
    def _mmap_random_read():
        with MmapDict(**mmap_dict_kwargs) as mmap_dict_read:
            for _ in range(READ_ITERATIONS):
                data = {key: value for key, value in mmap_dict_read.items()}
                assert data == samples

    @_timing
    def _json_random_read():
        with open(json_file_path) as f:
            for _ in range(READ_ITERATIONS):
                data = json.loads(f.read())
                assert data == samples
                f.seek(0)

    @_timing
    def _pickle_random_read():
        with open(pickle_file_path, "rb") as f:
            for _ in range(READ_ITERATIONS):
                data = pickle.loads(f.read())
                assert data == samples
                f.seek(0)

    _launch_threads(_mmap_random_read, _json_random_read, _pickle_random_read)

    assert time_results["_mmap_random_read"] < time_results["_json_random_read"]
    assert time_results["_mmap_random_read"] < time_results["_pickle_random_read"]

    # 5. Cleanup

    mmap_dict_write.close()
    json_write_file_handle.close()
    pickle_write_file_handle.close()
    _remove_files_if_present()
