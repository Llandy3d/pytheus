import mmap
import os
import tempfile
import struct

import pytest

from pytheus.mmap import (
    FixedSizeMmapDictTypeBackend,
    StrMmapDictTypeBackend,
    STRUCT_INT_FORMAT,
    STRUCT_FLOAT_FORMAT,
    STRUCT_BOOL_FORMAT,
    MmapDict,
)


@pytest.fixture
def mmap_handle():
    try:
        tmp_file_handle_ = tempfile.NamedTemporaryFile(mode="w+b")
        tmp_file_handle_.truncate(1 << 10)  # 1 Kilobyte
        file_handle_ = open(tmp_file_handle_.name, mode="r+b")
        mmap_handle_ = mmap.mmap(file_handle_.fileno(), 0)
        yield mmap_handle_
    finally:
        mmap_handle_.close()
        file_handle_.close()
        tmp_file_handle_.close()


def test_mmap_dict_type_backend_base(mmap_handle):
    type_backend = FixedSizeMmapDictTypeBackend(
        mmap=mmap_handle,
        struct_format_str=STRUCT_INT_FORMAT,
        size=4,
    )
    mmap_handle[2:14] = b"Hello world!"
    assert mmap_handle[2:14] == b"Hello world!"
    assert len(mmap_handle) == 1 << 10
    type_backend.move_left_and_pad(4, 6)
    assert mmap_handle[2:14] == b"Herld!\x00\x00\x00\x00\x00\x00"
    assert len(mmap_handle) == 1 << 10
    type_backend.move_right_and_pad(5, 4)
    assert mmap_handle[2:14] == b"Her\x00\x00\x00\x00ld!\x00\x00"
    assert len(mmap_handle) == 1 << 10


def test_int_mmap_dict_type_backend(mmap_handle):
    type_backend = FixedSizeMmapDictTypeBackend(
        mmap=mmap_handle,
        struct_format_str=STRUCT_INT_FORMAT,
        size=4,
    )
    type_backend.set_(0, 22)
    assert type_backend.get_(0) == 22
    assert mmap_handle[0:4] == b"\x16\x00\x00\x00"
    assert type_backend.size_(22) == 4


def test_float_mmap_dict_type_backend(mmap_handle):
    type_backend = FixedSizeMmapDictTypeBackend(
        mmap=mmap_handle,
        struct_format_str=STRUCT_FLOAT_FORMAT,
        size=8,
    )
    type_backend.set_(0, 22.0)
    assert type_backend.get_(0) == 22.0
    assert mmap_handle[0:8] == b"\x00\x00\x00\x00\x00\x006@"
    assert type_backend.size_(22.0) == 8


def test_bool_mmap_dict_type_backend(mmap_handle):
    type_backend = FixedSizeMmapDictTypeBackend(
        mmap=mmap_handle,
        struct_format_str=STRUCT_BOOL_FORMAT,
        size=1,
    )
    type_backend.set_(0, True)
    assert type_backend.get_(0) is True
    assert mmap_handle[0:4] == b"\x01\x00\x00\x00"
    assert type_backend.size_(True) == 4


@pytest.mark.parametrize(
    "expected_size,text",
    [
        (4, ""),
        (8, "He!"),
        (8, "Hey!"),
        (12, "Hello!"),
        (16, "Hello you!"),
        (16, "Hello world!"),
    ],
)
def test_str_mmap_dict_type_backend(mmap_handle, expected_size, text):
    type_backend = StrMmapDictTypeBackend(
        mmap=mmap_handle,
        encoding="utf-8",
    )
    type_backend.set_(0, text)
    assert type_backend.get_(0) == text
    encoded_text = text.encode("utf-8")
    encoded_text_length = len(encoded_text)
    assert mmap_handle[0:expected_size] == \
        struct.pack("i", encoded_text_length) + \
        encoded_text + \
        b"\0" * (expected_size - encoded_text_length - 4)
    assert type_backend.size_(text) == expected_size


def test_mmap_dict_core():
    path_1 = "test1.mmap"
    path_2 = "test2.mmap"
    mmap_dict_kwargs = dict(
        file_path=path_1,
        key_format_string="s",
        value_format_string="d",
        block_size=1 << 6,  # 64 bytes
        encoding="utf-8",
    )
    m_1 = MmapDict(**mmap_dict_kwargs)
    try:
        # 1. Check initial state
        assert len(m_1) == 0
        assert m_1.total_size == 64
        assert m_1.used_size == 8  # 2 * 4 control ints
        assert m_1.is_index_usable
        assert m_1.index == {}
        # 2. Add a couple of entries
        m_1["key_1"] = 1.0
        m_1["key_2"] = 2.0
        assert len(m_1) == 2
        assert m_1.total_size == 64
        assert m_1.used_size == 48  # 2 * 4 control ints + 2 * 12 keys + 2 * 8 doubles
        assert m_1.is_index_usable
        assert m_1.index == {"key_1": 8, "key_2": 28}
        assert m_1["key_1"] == 1.0
        assert m_1["key_2"] == 2.0
        # 3. Writing an existing entry does not increase the size
        m_1["key_1"] = 3.0
        assert len(m_1) == 2
        assert m_1.total_size == 64
        assert m_1.used_size == 48  # 2 * 4 control ints + 2 * 12 keys + 2 * 8 doubles
        assert m_1.is_index_usable
        assert m_1.index == {"key_1": 8, "key_2": 28}
        assert m_1["key_1"] == 3.0
        assert m_1["key_2"] == 2.0
        # 4. Adding another key forces a new block
        m_1["key_3"] = 3.0
        assert len(m_1) == 3
        assert m_1.total_size == 128
        assert m_1.used_size == 68  # 2 * 4 control ints + 3 * 12 keys + 3 * 8 doubles
        assert m_1.is_index_usable
        assert m_1.index == {"key_1": 8, "key_2": 28, "key_3": 48}
        assert m_1["key_1"] == 3.0
        assert m_1["key_2"] == 2.0
        assert m_1["key_3"] == 3.0
        # 5. Delete an entry
        del m_1["key_2"]
        assert len(m_1) == 2
        assert m_1.total_size == 128
        assert m_1.used_size == 48  # 2 * 4 control ints + 2 * 12 keys + 2 * 8 doubles
        assert m_1.is_index_usable
        assert m_1.index == {"key_1": 8, "key_3": 28}
        assert m_1["key_1"] == 3.0
        assert m_1["key_3"] == 3.0
        # 6. Re-open file as context manager and rebuild cache
        with MmapDict(**mmap_dict_kwargs) as m_2:
            m_2.initialize_cache()
            assert len(m_2) == 2
            assert m_2.total_size == 128
            assert m_2.used_size == 48  # 2 * 4 control ints + 2 * 12 keys + 2 * 8 doubles
            assert m_2.is_index_usable
            assert m_2.index == {"key_1": 8, "key_3": 28}
            assert m_2["key_1"] == 3.0
            assert m_2["key_3"] == 3.0
        # 7. Create a third dict on a different file path to test str overwrite values
        with MmapDict(**dict(mmap_dict_kwargs, file_path=path_2, value_format_string="s")) as m_3:
            m_3["key_1"] = "Hello "
            m_3["key_2"] = "world!"
            assert len(m_3) == 2
            assert m_3.total_size == 64
            assert m_3.used_size == 56  # 2 * 4 control ints + 2 * 12 key + 2 * 12 value
            assert m_3.is_index_usable
            assert m_3.index == {"key_1": 8, "key_2": 32}
            assert m_3["key_1"] == "Hello "
            assert m_3["key_2"] == "world!"
            m_3["key_2"] = "you!"
            assert len(m_3) == 2
            assert m_3.total_size == 64
            assert m_3.used_size == 52  # 2 * 4 control ints + 2 * 12 key + 1 * 12 + 1 * 8 value
            assert m_3.is_index_usable
            assert m_3.index == {"key_1": 8, "key_2": 32}
            assert m_3["key_1"] == "Hello "
            assert m_3["key_2"] == "you!"
            m_3["key_2"] = "dear person!"
            assert len(m_3) == 2
            assert m_3.total_size == 64
            assert m_3.used_size == 60  # 2 * 4 control ints + 2 * 12 key + 1 * 12 + 1 * 16 value
            assert m_3.is_index_usable
            assert m_3.index == {"key_1": 8, "key_2": 32}
            assert m_3["key_1"] == "Hello "
            assert m_3["key_2"] == "dear person!"
    finally:
        m_1.close()
        os.remove(path_1)
        if os.path.exists(path_2):
            os.remove(path_2)
