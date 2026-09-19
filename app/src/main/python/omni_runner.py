import os
import queue
import threading
import importlib.util
import sys

_input_queue=queue.Queue()
_output_queue=queue.Queue()
_running=False
_thread=None
_module=None

def prepare(files_dir):
    os.makedirs(files_dir,exist_ok=True)

def _load(script):
    global _module
    spec=importlib.util.spec_from_file_location("universal_crt_v4",script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Universal CRT V4")
    module=importlib.util.module_from_spec(spec)
    sys.modules["universal_crt_v4"]=module
    spec.loader.exec_module(module)
    _module=module
    return module

def _input():
    while _running:
        try:
            return _input_queue.get(timeout=0.25)
        except queue.Empty:
            continue
    return "q"

def _output(value):
    if value:
        _output_queue.put(str(value))

def start(script,width=112,height=32):
    global _thread,_running
    if _thread is not None and _thread.is_alive():
        return

    _running=True

    def worker():
        global _running
        try:
            module=_load(script)
            module.android_main(_input,_output,width,height)
        except BaseException as exc:
            _output(
                "\n[PYTHON ERROR] %s: %s\n"
                % (type(exc).__name__,exc)
            )
        finally:
            _running=False

    _thread=threading.Thread(
        target=worker,
        name="UniversalCRT",
        daemon=True
    )
    _thread.start()

def send_key(key):
    if key:
        _input_queue.put(str(key))

def read_output():
    parts=[]
    while True:
        try:
            parts.append(_output_queue.get_nowait())
        except queue.Empty:
            return "".join(parts)

def running():
    return bool(_running)

def stop():
    global _running
    _running=False
    _input_queue.put("q")
