"""Live check (real hardware): the dashboard must not keep an idle RTX GPU awake.

GPU load comes from tests/gpu_load.py, which needs PyTorch with CUDA. Point
NITROTUX_TORCH_PYTHON at an interpreter that has it (default: this one).
"""
import os, pty, select, struct, subprocess, sys, time, fcntl, termios

RT = "/sys/bus/pci/devices/0000:01:00.0/power/runtime_status"
rt = lambda: open(RT).read().strip()

pid, fd = pty.fork()
if pid == 0:
    os.environ.update(TERM="xterm-256color", NITROTUX_LANG="en")
    os.execvp(sys.executable, [sys.executable, "-m", "nitrotux"])
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
out = b""
def pump(sec):
    global out
    end = time.time() + sec
    while time.time() < end:
        if select.select([fd], [], [], 0.2)[0]:
            try: out += os.read(fd, 65536)
            except OSError: return

def phase(name, sec):
    states = []
    end = time.time() + sec
    while time.time() < end:
        pump(1); states.append(rt())
    print(f"{name:<34} {''.join('A' if s == 'active' else 's' for s in states)}")
    return states

print("A = active, s = suspended (1 char per second)")
print("start:", rt())
idle = phase("1) idle GPU, dashboard open 30 s", 30)
load = subprocess.Popen([os.environ.get("NITROTUX_TORCH_PYTHON", sys.executable),
                         os.path.join(os.path.dirname(__file__), "gpu_load.py"), "20"])
out = b""
busy = phase("2) GPU load 20 s", 22)
load.wait()
saw_watts = b" W / " in out
after = phase("3) load done, dashboard open 75 s", 75)
os.write(fd, b"q"); pump(1); os.waitpid(pid, 0)

print()
first = next((i for i, s in enumerate(idle) if s != "active"), None)
print("1) idle GPU slept and stayed asleep:  ",
      first is not None and all(s != "active" for s in idle[first:]),
      f"(asleep from second {first})")
print("2) dashboard showed GPU watts in load:", saw_watts)
print("3) GPU went back to sleep afterwards: ", "suspended" in after[-10:],
      f"(after ~{next((i for i, s in enumerate(after) if s != 'active'), None)} s)")
