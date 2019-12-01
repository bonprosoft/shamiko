from typing import List


class BufferedReader:

    def __init__(self):
        # type: () -> None
        self._buffer = ""

    def write(self, data):
        # type: (str) -> None
        self._buffer += data

    def clear(self):
        # type: () -> None
        self._buffer = ""

    def readlines(self):
        # type: () -> List[str]
        truncated = not self._buffer.endswith("\n")
        sp = self._buffer.splitlines()

        if truncated:
            self._buffer = sp[-1]
            sp = sp[:-1]
        else:
            self._buffer = ""

        return sp
