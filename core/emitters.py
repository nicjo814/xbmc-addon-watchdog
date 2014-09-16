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

import re
import os
import sys
import subprocess
from watchdog.observers.api import BaseObserver
from watchdog.observers.api import ObservedWatch
from polling_local import LocalPoller
from polling_xbmc import VFSPoller, VFSPollerNonRecursive


try:
    from watchdog.observers.inotify import InotifyEmitter as NativeEmitter
except:
    try:
        from watchdog.observers.kqueue import KqueueEmitter as NativeEmitter
    except:
        try:
            from watchdog.observers.read_directory_changes import WindowsApiEmitter as NativeEmitter
        except:
            NativeEmitter = LocalPoller


class MultiEmitterObserver(BaseObserver):
    def __init__(self):
        BaseObserver.__init__(self, None)

    def schedule(self, event_handler, path, emitter_cls=None):
        with self._lock:
            watch = ObservedWatch(path, True)
            emitter = emitter_cls(self.event_queue, watch, self.timeout)
            if self.is_alive():
                emitter.start()
            self._add_handler_for_watch(event_handler, watch)
            self._add_emitter(emitter)
            self._watches.add(watch)
            return watch


def select_emitter(path):
    import xbmcvfs
    import settings
    from utils import log

    if re.match(r'^[A-z]+://', path):
        if xbmcvfs.exists(path):
            if settings.RECURSIVE:
                return path, VFSPoller
            return path, VFSPollerNonRecursive
        raise IOError("No such directory: '%s'" % path)

    if os.path.exists(path):
        if settings.POLLING:
            return path, LocalPoller
        elif _is_remote_filesystem(path):
            log("select_observer: path <%s> identified as remote filesystem" % path)
            return path, LocalPoller
        return path, NativeEmitter

    # try using fs encoding
    fsenc = sys.getfilesystemencoding()
    if fsenc:
        try:
            path_alt = path.decode('utf-8').encode(fsenc)
        except UnicodeEncodeError:
            path_alt = None
        if path_alt and os.path.exists(path_alt):
            if settings.POLLING:
                return path_alt, LocalPoller
            return path_alt, NativeEmitter

    raise IOError("No such directory: '%s'" % path)


def _is_remote_filesystem(path):
    from utils import log
    from watchdog.utils import platform
    if not platform.is_linux():
        return False

    remote_fs_types = ['cifs', 'smbfs', 'nfs', 'nfs4']
    escaped_path = path.rstrip('/').replace(' ', '\\040')
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                _, mount_point, fstype = line.split()[:3]
                if mount_point == escaped_path:
                    log("[fstype] type is \"%s\" '%s' " % (fstype, path))
                    return fstype in remote_fs_types
        log("[fstype] path not in /proc/mounts '%s' " % escaped_path)
        return False

    except (IOError, ValueError) as e:
        log("[fstype] failed to read /proc/mounts. %s, %s" % (type(e), e))
        return False