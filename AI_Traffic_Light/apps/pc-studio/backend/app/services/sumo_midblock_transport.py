"""Private lean midblock worker transport.

A dedicated interpreter does not re-import the caller's FastAPI, OpenCV or
test harness entry point on Windows spawn. No socket, shell or public commands.
The worker and parent retain the same simulation and protected admission checks.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from pathlib import Path
from queue import Empty, Full, Queue
import subprocess
import sys
from threading import Thread

from app.services.sumo_shadow_adapter import ShadowAgent

MAX_MESSAGE=256*1024
_EOF=object()


def _encode(value):
    data=json.dumps(value,separators=(",",":"),allow_nan=False).encode("utf-8")+b"\n"
    if len(data)>MAX_MESSAGE:
        raise ValueError("Oversized midblock worker message")
    return data


def _read(stream):
    line=stream.readline(MAX_MESSAGE+1)
    if not line:
        raise EOFError("Midblock worker pipe closed")
    if len(line)>MAX_MESSAGE or not line.endswith(b"\n"):
        raise ValueError("Invalid midblock worker message boundary")
    return line


def _decode(line):
    def reject(value):
        raise ValueError("Nonfinite midblock worker number")
    return json.loads(line,parse_constant=reject)


class ChildWire:
    def __init__(self,reader,writer):
        self.reader,self.writer=reader,writer

    def recv(self):
        value=_decode(_read(self.reader))
        if value=="close":
            return value
        if not isinstance(value,list) or len(value)!=2 or value[0]!="step" or not isinstance(value[1],str):
            raise ValueError("Invalid private worker command")
        return tuple(value)

    def send(self,value):
        status,payload=value
        if status=="ok" and payload is not None:
            rows,arrived,persons,permission,new=payload
            payload=[list(map(asdict,rows)),list(arrived),list(persons),permission,list(new)]
        self.writer.write(_encode([status,payload]))
        self.writer.flush()

    def close(self):
        self.writer.close()


class ProcessHandle:
    """Minimal existing session process interface, backed by Popen."""
    def __init__(self,proc):
        self._proc=proc
        self.pid=proc.pid

    def is_alive(self):
        return self._proc.poll() is None

    def join(self,timeout):
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass

    def terminate(self):
        if self.is_alive():
            self._proc.terminate()

    def kill(self):
        if self.is_alive():
            self._proc.kill()


class ParentWire:
    def __init__(self,proc):
        self.proc=proc
        self.closed=False
        self._messages=Queue(maxsize=2)
        self._pending=None
        self._error=None
        self._reader=Thread(target=self._read_loop,name="mesh-midblock-wire",daemon=True)
        self._reader.start()

    def _read_loop(self):
        try:
            while True:
                try:
                    item=_read(self.proc.stdout)
                except EOFError:
                    item=_EOF
                self._messages.put_nowait(item)
                if item is _EOF:
                    return
        except (OSError,ValueError,Full) as exc:
            self._error=exc
            try:
                self._messages.put_nowait(_EOF)
            except Full:
                pass
        finally:
            self.proc.stdout.close()

    def send(self,value):
        if self.closed:
            raise EOFError("Closed midblock worker pipe")
        self.proc.stdin.write(_encode(value))
        self.proc.stdin.flush()

    def poll(self,timeout):
        if self._error:
            raise RuntimeError("Invalid midblock worker output") from self._error
        if self._pending is not None:
            return True
        try:
            self._pending=self._messages.get(timeout=timeout)
            return True
        except Empty:
            if self._error:
                raise RuntimeError("Invalid midblock worker output") from self._error
            return False

    def recv(self):
        line,self._pending=self._pending,None
        if self._error:
            raise RuntimeError("Invalid midblock worker output") from self._error
        if line is _EOF or line is None:
            raise EOFError("Midblock worker exited")
        message=_decode(line)
        if not isinstance(message,list) or len(message)!=2:
            raise ValueError("Invalid midblock worker response")
        status,payload=message
        if status=="error" and isinstance(payload,str):
            return status,payload
        if status!="ok":
            raise ValueError("Invalid midblock worker status")
        if payload is None:
            return status,None
        if not isinstance(payload,list) or len(payload)!=5:
            raise ValueError("Invalid midblock worker payload")
        rows,arrived,persons,permission,new=payload
        if not all(isinstance(x,list) for x in (rows,arrived,persons,new)) or not isinstance(permission,str):
            raise ValueError("Invalid midblock worker fields")
        if not all(isinstance(i,str) for i in arrived+persons):
            raise ValueError("Invalid arrival identity")
        if not all(isinstance(x,list) and len(x)==2 and isinstance(x[0],str)
                   and type(x[1]) in (float,int) and math.isfinite(x[1]) for x in new):
            raise ValueError("Invalid reentry payload")
        return status,(tuple(ShadowAgent(**row) for row in rows),tuple(arrived),tuple(persons),permission,[tuple(x) for x in new])

    def close(self):
        if not self.closed:
            self.closed=True
            try:
                self.proc.stdin.close()
            except OSError:
                pass  # broken child pipe must not prevent process reaping


def _launch(argv,cwd):
    proc=subprocess.Popen(argv,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL,shell=False,
                          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    try:
        return ParentWire(proc),ProcessHandle(proc)
    except BaseException:
        proc.kill()
        proc.wait(timeout=5)
        proc.stdin.close()
        proc.stdout.close()
        raise


def launch_midblock(root,seed):
    backend=Path(__file__).resolve().parents[2]
    # Explicit trusted import root, no caller __main__ re-import and no
    # user-supplied executable, code, arguments or network endpoint.
    code="import sys;sys.path.insert(0,sys.argv[1]);from app.services.sumo_midblock_transport import child_main;child_main(sys.argv[2],int(sys.argv[3]))"
    return _launch([sys.executable,"-I","-u","-c",code,str(backend),str(root),str(seed)],backend)


def child_main(root,seed):
    # Isolate protocol stdout from native library informational output.
    writer=os.fdopen(os.dup(sys.stdout.fileno()),"wb")
    os.dup2(sys.stderr.fileno(),sys.stdout.fileno())
    from app.services.sumo_midblock_session import _midblock_worker
    _midblock_worker(ChildWire(sys.stdin.buffer,writer),root,seed)
