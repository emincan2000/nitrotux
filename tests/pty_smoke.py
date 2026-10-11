"""Start the real curses UI in a pseudo-terminal, press keys, check it exits cleanly."""
import os, pty, select, struct, sys, time, fcntl, termios

def run(keys, cols=100, rows=30, env_extra=None, wait=2.5):
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.update({"TERM": "xterm-256color", **(env_extra or {})})
        os.execvp(sys.executable, [sys.executable, "-m", "nitrotux"])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    out = b""
    def pump(t):
        nonlocal out
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.1)
            if r:
                try: out += os.read(fd, 65536)
                except OSError: return
    pump(wait)
    for k in keys:
        os.write(fd, k); pump(0.8)
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status), out.decode("utf-8", "replace")

if __name__ == "__main__":
    code, out = run([b"q"], env_extra={"NITROTUX_LANG": "tr"})
    print("exit:", code)
    for word in ("Nitrotux", "Sessiz", "Dengeli", "Performans", "RPM", "Traceback"):
        print(f"  {word!r}: {'VAR' if word in out else 'yok'}")
