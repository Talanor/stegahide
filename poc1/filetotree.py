#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import argparse
import re
import os
import os.path
import time
import progressbar


def read_chunk(f, chunk_size):
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        yield data


def make_tree(path, fh, count=8, width=10, byteorder='big'):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass

    root_dirs = []
    for c in range(width):
        root_dirs.append(os.open(path, os.O_RDONLY))

    first = True
    i = 0
    statinfo = os.fstat(fh.fileno())
    size = 0
    with progressbar.ProgressBar() as bar:
        for chunk in read_chunk(fh, count * width):
            names = [chunk[i:i + count] for i in range(0, len(chunk), count)]
            for name in names:
                name = (
                    "%X" % int.from_bytes(name, byteorder=byteorder)
                ).rjust(
                    len(name) * 2, '0'
                )
                if i < width:
                    prefix = "%d" % (i)
                    prefix = prefix.rjust(len("%d" % (width - 1)), '0')
                    name = "%s-%s" % (prefix, name)

                os.fchdir(root_dirs[i % width])
                os.mkdir(name)
                os.close(root_dirs[i % width])
                root_dirs[i % width] = os.open(name, os.O_RDONLY)
                i += 1
            size += len(chunk)
            bar.update((size * 100.0) / statinfo.st_size)
            time.sleep(0.100)

    for root_dir in root_dirs:
        os.close(root_dir)


def make_file(path, fh, byteorder='big'):
    root_dirs = []
    for name in sorted(os.listdir(path)):
        root_dirs.append(
            (os.open(os.path.join(path, name), os.O_RDONLY), name)
        )
    width = len(root_dirs)

    pattern = re.compile("^(?P<prefix>[0-9]+)-(?P<bytes>[0-9A-Fa-f]+)$")
    i = 0
    while True:
        os.fchdir(root_dirs[i % width][0])
        name = root_dirs[i % width][1]
        if i < width:
            m = pattern.match(name)
            payload = int(m.group("bytes"), 16).to_bytes(
                length=int((len(m.group("bytes")) + 1) / 2),
                byteorder=byteorder
            )
        else:
            payload = int(name, 16).to_bytes(
                length=int((len(name) + 1) / 2), byteorder=byteorder
            )
        fh.write(payload)
        dirs = os.listdir(".")
        if len(dirs) > 0:
            os.close(root_dirs[i % width][0])
            root_dirs[i % width] = (os.open(dirs[0], os.O_RDONLY), dirs[0])
        else:
            break
        i += 1

    for root_dir in root_dirs:
        os.close(root_dir[0])


def main(args):
    parser = argparse.ArgumentParser(
        description='Make a tree out of a file.'
    )
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_hide = subparsers.add_parser('hide', help='hide command help')
    parser_hide.add_argument(
        '--path', '-p',
        required=True,
        help='The path of the tree to generate'
    )
    parser_hide.add_argument(
        '--file', '-f',
        required=True,
        help='The path of the file to hide'
    )
    parser_hide.add_argument(
        '--byteorder', '-b',
        required=False, default='big',
        help='bytes order, "little" or "big" (default)'
    )
    parser_hide.add_argument(
        '--count', '-c',
        required=True, type=int,
        help='Number of bytes per folder'
    )
    parser_hide.add_argument(
        '--width', '-w',
        required=True, type=int,
        help='Number of folders per level'
    )

    parser_unhide = subparsers.add_parser('unhide', help='unhide command help')
    parser_unhide.add_argument(
        '--path', '-p',
        required=True,
        help='The path of the tree generated'
    )
    parser_unhide.add_argument(
        '--file', '-f',
        required=True,
        help='The path of the recovered file'
    )
    parser_unhide.add_argument(
        '--byteorder', '-b',
        required=False, default='big',
        help='bytes order, "little" or "big" (default)'
    )

    args = parser.parse_args()

    if not hasattr(args, 'file') or not hasattr(args, 'path'):
        parser.print_help()
        sys.exit(1)

    args.path = os.path.realpath(args.path)

    if hasattr(args, 'byteorder'):
        assert(args.byteorder in ("little", "big"))
    else:
        args.byteorder = 'big'

    if hasattr(args, 'width'):
        assert(args.width > 0)
        assert(args.count > 0)

        with open(args.file, 'rb') as f:
            make_tree(args.path, f, args.count, args.width, args.byteorder)
    else:
        with open(args.file, 'wb') as f:
            make_file(args.path, f, args.byteorder)

if __name__ == '__main__':
    main(sys.argv)
