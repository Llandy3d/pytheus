import abc
import collections
import mmap
import os
import struct
import typing

# See https://docs.python.org/3/library/struct.html#format-characters
StructFormatString = typing.Literal["i", "d", "?", "s"]
StructFormatType = typing.Union[int, float, bool, str]

STRUCT_INT_FORMAT: StructFormatString = "i"
STRUCT_FLOAT_FORMAT: StructFormatString = "d"
STRUCT_BOOL_FORMAT: StructFormatString = "?"
STRUCT_STR_FORMAT: StructFormatString = "s"

BYTE_ALIGNMENT = 4

DEFAULT_BACKEND = "DEFAULT_BACKEND"


class MmapDictTypeBackend(abc.ABC):
    def __init__(self, mmap: mmap.mmap) -> None:
        self._mmap = mmap

    def move_right_and_pad(self, position: int, count: int):
        """ Move a section of the array to the right and pad zeros in the gap """
        self._mmap[position:] = b"\0" * count + self._mmap[position:-count]

    def move_left_and_pad(self, position: int, count: int):
        """ Move a section of the array to the left and pad zeros at the end """
        self._mmap[position:] = self._mmap[position+count:] + b"\0" * count

    @abc.abstractmethod
    def get_(self, position: int) -> StructFormatType:
        ...

    @abc.abstractmethod
    def set_(self, position: int, value: StructFormatType) -> None:
        ...

    @abc.abstractmethod
    def size_(self, value: StructFormatType) -> int:
        ...


class FixedSizeMmapDictTypeBackend(MmapDictTypeBackend):
    def __init__(
        self, mmap: mmap.mmap,
        struct_format_str: StructFormatString,
        size: int,
    ) -> None:
        super().__init__(mmap)
        self._struct_format_str = struct_format_str
        self._size = size
        self._padding = b""
        remainder = self._size % BYTE_ALIGNMENT
        if self._size < BYTE_ALIGNMENT:
            self._aligned_size = BYTE_ALIGNMENT
            if remainder != 0:
                self._padding = b"\0" * (BYTE_ALIGNMENT - remainder)
        else:
            self._aligned_size = self._size
            if remainder != 0:
                self._aligned_size += BYTE_ALIGNMENT
                self._padding = b"\0" * (BYTE_ALIGNMENT - remainder)

    def get_(self, position: int) -> StructFormatType:
        return struct.unpack(self._struct_format_str, self._mmap[position:position+self._size])[0]

    def set_(self, position: int, value: StructFormatType) -> None:
        self._mmap[position:position+self._aligned_size] = \
            struct.pack(self._struct_format_str, value) + self._padding

    def size_(self, value: StructFormatType) -> int:
        return self._aligned_size


class StrMmapDictTypeBackend(MmapDictTypeBackend):
    def __init__(
        self, mmap: mmap.mmap,
        encoding: str,
    ) -> None:
        super().__init__(mmap)
        self._encoding = encoding

    def get_(self, position: int) -> str:
        offset_position = position + 4
        return self._mmap[offset_position:offset_position+self._size_by_position(position)].decode(
            self._encoding
        )

    def set_(self, position: int, value: str) -> None:  # type: ignore[override]
        size = self._size_by_value(value)
        padding = b""
        remainder = size % BYTE_ALIGNMENT
        if remainder != 0:
            padding = b"\0" * (BYTE_ALIGNMENT - remainder)
        offset_position = position + 4
        self._mmap[position:offset_position] = struct.pack(STRUCT_INT_FORMAT, size)
        self._mmap[offset_position:offset_position+size+len(padding)] = \
            value.encode(self._encoding) + padding

    def size_(self, value: str) -> int:  # type: ignore[override]
        size_by_value = self._size_by_value(value)
        combined_size = 4 + size_by_value
        if combined_size < BYTE_ALIGNMENT:
            return BYTE_ALIGNMENT
        else:
            remainder = combined_size % BYTE_ALIGNMENT
            if remainder:
                return combined_size + BYTE_ALIGNMENT - remainder
            else:
                return combined_size

    def _size_by_position(self, position: int) -> int:
        return struct.unpack(STRUCT_INT_FORMAT, self._mmap[position:position+4])[0]

    def _size_by_value(self, value: str) -> int:
        return len(value.encode(self._encoding))


class MmapDict(collections.abc.MutableMapping):
    """ Python dictionary that streams its data to a memory-mapped file.

    ############
    # Features #
    ############

    - It only support basic types: int, float, bool and string.

    - It is not thread-safe for writing, which means only a single process should be writing.

    - Index access will work in these two cases:

        - In the write process, provided there is only one.

        - In any read-only process, provided there is no write process running at the same time.

    - Index cache is built in these two ways:

        - As part of the initial write process as keys get inserted.

        - If you open the file later on in a separate process for reading or further writing, the
          cache can be rebuilt with self.initialize_cache() or by just iterating through the keys.

    ######################
    # How data is stored #
    ######################

    - First 4 bytes have an integer with the position of the next new entry that would be inserted.

    - Next 4 bytes have an integer with the number of entries stored so far.

    - Each new key/value pair gets appended to the file sequentially after it, and we keep an
      internal in-memory index cache of what position each key is located, to enable index access.

    - Each type is stored in the following way:

        - Integers(4 bytes) and doubles(8 bytes) use that fixed amount of space.

        - Booleans(1 byte) add padding to fill the 4 byte alignment.

        - Strings(x bytes) use 4 initial bytes that hold an integer with the size of the string,
          then we store the string itself and add padding to fill the 4 byte alignment.
    """
    # Control integer positions
    NEXT_WRITE_POSITION_CONTROL_INT = 0
    LENGTH_CONTROL_INT = 4

    def __init__(
        self,
        file_path: str,
        value_format_string: StructFormatString,
        key_format_string: StructFormatString = "s",
        block_size: int = 1 << 20,  # 1 Megabyte
        encoding: str = "utf-8",
    ) -> None:
        super().__init__()
        self._file_path = file_path
        self._value_format_string: StructFormatString = value_format_string
        self._key_format_string: StructFormatString = key_format_string
        self._block_size = block_size
        self._encoding = encoding
        # Initialize file descriptors, type backends and control bytes
        file_exists = os.path.exists(file_path) and os.path.isfile(file_path)
        if not file_exists:
            with open(file_path, mode="w+b") as file_handler:
                file_handler.truncate(block_size)
            self._set_file_descriptors()
            self._set_type_backends()
            self._next_write_position = 8
            self._length = 0
        else:
            self._set_file_descriptors()
            self._set_type_backends()
        self._total_size = os.stat(file_path).st_size
        # Initialize cache
        self.index: collections.OrderedDict[StructFormatType, int] = collections.OrderedDict()

    def __getitem__(self, key: StructFormatType) -> StructFormatType:
        key_position = self._get_index_position(key)
        return self._type_backends[self._value_format_string].get_(
            key_position + self._get_key_size(key)
        )

    def __setitem__(self, key: StructFormatType, value: StructFormatType) -> None:

        def _extend_file_if_needed(required_new_size: int):
            while True:
                if self._total_size < self._next_write_position + required_new_size:
                    self._extend_file()
                else:
                    break

        key_offset = self._get_key_size(key)
        value_offset = self._get_value_size(value)
        total_offset = key_offset + value_offset
        try:
            key_position = self._get_index_position(key)
            value_position = key_position + key_offset
            old_value_offset = self._get_value_size(self[key])
            required_new_size = value_offset - old_value_offset
            _extend_file_if_needed(required_new_size)
            if required_new_size < 0:
                self._type_backends[DEFAULT_BACKEND].move_left_and_pad(
                    position=value_position+old_value_offset,
                    count=-required_new_size,
                )
                self._move_index_keys(key, required_new_size)
            elif required_new_size > 0:
                self._type_backends[DEFAULT_BACKEND].move_right_and_pad(
                    position=value_position+old_value_offset,
                    count=required_new_size
                )
                self._move_index_keys(key, required_new_size)
        except KeyError:
            key_position = self._next_write_position
            value_position = key_position + key_offset
            required_new_size = total_offset
            _extend_file_if_needed(required_new_size)
            self._length += 1
            self.index[key] = key_position
        self._type_backends[self._key_format_string].set_(key_position, key)
        self._type_backends[self._value_format_string].set_(value_position, value)
        self._next_write_position += required_new_size

    def __delitem__(self, key: StructFormatType) -> None:
        key_position = self._get_index_position(key)
        total_offset = self._get_key_size(key) + self._get_value_size(self[key])
        self._type_backends[DEFAULT_BACKEND].move_left_and_pad(key_position, total_offset)
        self._next_write_position -= total_offset
        self._length -= 1
        self._move_index_keys(key, -total_offset)
        del self.index[key]

    def __iter__(self) -> typing.Iterable[StructFormatType]:  # type: ignore
        key_position = 8  # After the two control bytes
        for _ in range(len(self)):  # Iterate all keys and build the cache
            key = self._type_backends[self._key_format_string].get_(key_position)
            self.index[key] = key_position
            key_position += self._get_key_size(key) + self._get_value_size(self[key])
            yield key

    def __len__(self) -> int:
        return self._length

    def __enter__(self) -> "MmapDict":
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        self.close()

    def _set_file_descriptors(self) -> None:
        self._file = open(self._file_path, mode="r+b")
        self._mmap = mmap.mmap(self._file.fileno(), 0)

    def _set_type_backends(self) -> None:
        self._type_backends: dict[str, MmapDictTypeBackend] = {
            STRUCT_INT_FORMAT: FixedSizeMmapDictTypeBackend(self._mmap, STRUCT_INT_FORMAT, 4),
            STRUCT_FLOAT_FORMAT: FixedSizeMmapDictTypeBackend(self._mmap, STRUCT_FLOAT_FORMAT, 8),
            STRUCT_BOOL_FORMAT: FixedSizeMmapDictTypeBackend(self._mmap, STRUCT_BOOL_FORMAT, 1),
            STRUCT_STR_FORMAT: StrMmapDictTypeBackend(self._mmap, self._encoding),
        }
        self._type_backends[DEFAULT_BACKEND] = self._type_backends[STRUCT_INT_FORMAT]

    def _extend_file(self) -> None:
        self.close()
        with open(self._file_path, mode="a+b") as file_handler:
            file_handler.write(b"\0" * self._block_size)
        self._total_size += self._block_size
        self._set_file_descriptors()
        self._set_type_backends()

    def _get_index_position(self, key: StructFormatType) -> int:
        if key not in self.index:
            raise KeyError(
                f"Key '{key}' is missing. It could also be that some other process is writing to "
                "the file and the cache is not being properly updated, which is not supported."
            )
        return self.index[key]

    def _move_index_keys(self, after_key: StructFormatType, diff: int):
        key_found = False
        for cached_index, cached_key in enumerate(self.index):
            if after_key == cached_key:
                key_found = True
                continue
            if key_found:
                self.index[cached_key] += diff

    def _get_key_size(self, key: StructFormatType) -> int:
        return self._type_backends[self._key_format_string].size_(key)

    def _get_value_size(self, value: StructFormatType) -> int:
        return self._type_backends[self._value_format_string].size_(value)

    @property
    def _next_write_position(self) -> int:
        return self._type_backends[STRUCT_INT_FORMAT].get_(self.NEXT_WRITE_POSITION_CONTROL_INT)  # type: ignore # noqa: E501

    @_next_write_position.setter
    def _next_write_position(self, position: int) -> None:
        self._type_backends[STRUCT_INT_FORMAT].set_(self.NEXT_WRITE_POSITION_CONTROL_INT, position)

    @property
    def _length(self) -> int:
        return self._type_backends[STRUCT_INT_FORMAT].get_(self.LENGTH_CONTROL_INT)  # type: ignore

    @_length.setter
    def _length(self, length: int) -> None:
        self._type_backends[STRUCT_INT_FORMAT].set_(self.LENGTH_CONTROL_INT, length)

    @property
    def total_size(self) -> int:
        return self._total_size

    @property
    def used_size(self) -> int:
        return self._next_write_position

    @property
    def is_index_usable(self) -> bool:
        return len(self.index) == len(self)

    def initialize_cache(self) -> None:
        for _ in iter(self):
            pass

    def close(self) -> None:
        if self._mmap:
            self._mmap.close()
        if self._file:
            self._file.close()
