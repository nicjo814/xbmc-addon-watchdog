# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import settings
from polling import PollerBase, FileSnapshot, MtimeSnapshot, hidden
from utils import encode_path, decode_path


def _walk(path):
    path = encode_path(path)
    for root, dirs, files in os.walk(path):
        if dirs or files:
            for d in dirs:
                if hidden(d):
                    dirs.remove(d)
            dirs = (decode_path(os.path.join(root, d)) for d in dirs)
            files = (decode_path(os.path.join(root, f)) for f in files if not hidden(f))
            yield dirs, files


def _get_mtime(path):
    return os.stat(encode_path(path)).st_mtime


class LocalPoller(PollerBase):
    polling_interval = 1
    recursive = settings.RECURSIVE

    def _take_snapshot(self):
        if self.recursive:
            return FileSnapshot(self.watch.path, _walk)
        return MtimeSnapshot(self.watch.path, _get_mtime)
