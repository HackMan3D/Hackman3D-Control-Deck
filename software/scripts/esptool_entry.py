from __future__ import annotations

import sys

import esptool


if __name__ == "__main__":
    esptool.main(sys.argv[1:])
