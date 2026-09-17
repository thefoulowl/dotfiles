#!/usr/bin/env python3
"""
Tracks window focus order via i3's IPC and gives Alt+Tab Windows-style
cycling: hold Alt, tap Tab to step through windows in most-recently-used
order (Shift+Tab steps back), release Alt to land — maximized.

  --daemon   : run continuously, updating the history file on focus/close
  --tab      : step forward in the cycle  (Alt+Tab press)
  --tab-back : step backward in the cycle (Alt+Shift+Tab press)
  --release  : end the cycle             (Alt key release)
  --restore  : bring back the most recently minimized window, maximized
"""
import json
import os
import subprocess
import sys
import time

STATE_FILE = os.path.expanduser("~/.cache/i3_focus_stack")
CYCLE_FILE = os.path.expanduser("~/.cache/i3_cycle_state")
MAX_HISTORY = 20


def read_stack():
    try:
        with open(STATE_FILE) as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def write_stack(stack):
    # write to a temp file then rename, so a concurrent --prev never reads a
    # half-written (truncated) file
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(stack[:MAX_HISTORY]))
    os.replace(tmp, STATE_FILE)


def seed_stack_from_tree():
    """Every daemon start seeds fresh from whatever windows are currently
    open (ignoring any stale file left from a previous run — those con_ids
    may no longer exist), so Alt+Tab works immediately."""
    result = subprocess.run(["i3-msg", "-t", "get_tree"], capture_output=True, text=True)
    try:
        tree = json.loads(result.stdout)
    except json.JSONDecodeError:
        return
    windows = []
    focused_id = None

    def walk(node, in_dock=False):
        nonlocal focused_id
        # i3bar lives under a "dockarea" node and reports window_type
        # "unknown", so filter structurally — docks can't be focused
        in_dock = in_dock or node.get("type") == "dockarea"
        if node.get("window") and not in_dock:
            con_id = str(node["id"])
            windows.append(con_id)
            if node.get("focused"):
                focused_id = con_id
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            walk(child, in_dock)

    walk(tree)
    if focused_id and focused_id in windows:
        windows.remove(focused_id)
        windows.insert(0, focused_id)
    if windows:
        write_stack(windows)


def run_daemon():
    import select

    seed_stack_from_tree()
    proc = subprocess.Popen(
        ["i3-msg", "-t", "subscribe", "-m", '["window"]'],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    while True:
        # wake at least once a second even with no events, so a stuck cycle
        # (e.g. the Alt-release bind occasionally missing its event when a
        # window switch happens mid-hold) gets cleared within ~1s instead of
        # waiting for the next incidental focus change to trigger the check
        ready, _, _ = select.select([proc.stdout], [], [], 1.0)
        if not ready:
            cycle_in_progress()  # no-op unless stale; self-heals as a side effect
            continue
        line = proc.stdout.readline()
        if not line:
            break
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        change = event.get("change")
        # title/fullscreen_mode/move/floating/urgent/mark events must not touch
        # the stack — a terminal whose title spinner flips constantly would
        # otherwise be evicted from history every few milliseconds
        if change not in ("focus", "close"):
            continue
        container = event.get("container", {})
        if container.get("window_type") == "dock":
            continue
        con_id = str(container.get("id"))
        if not con_id or con_id == "None":
            continue
        # while an Alt+Tab cycle is in progress, windows we merely step
        # through must not be promoted — only the one landed on (handled
        # by end_cycle) — otherwise the MRU order gets scrambled
        if change == "focus" and cycle_in_progress():
            continue
        stack = read_stack()
        if con_id in stack:
            stack.remove(con_id)
        if change == "focus":
            stack.insert(0, con_id)
        write_stack(stack)
        if change == "close":
            # whatever inherits focus after a close is a plain tiled window,
            # which would expose the split layout — keep it one-window-at-a-time
            subprocess.run(["i3-msg", "fullscreen enable"], capture_output=True)


def focus_and_maximize(con_id):
    subprocess.run(["i3-msg", "fullscreen disable"])
    result = subprocess.run(
        ["i3-msg", f"[con_id={con_id}] focus, fullscreen enable"],
        capture_output=True, text=True,
    )
    try:
        return json.loads(result.stdout)[0].get("success", False)
    except (json.JSONDecodeError, IndexError, KeyError, AttributeError):
        return False


def read_cycle():
    try:
        with open(CYCLE_FILE) as f:
            snapshot_line, index_line, ts_line = f.read().splitlines()
        return snapshot_line.split(","), int(index_line), float(ts_line)
    except (FileNotFoundError, ValueError):
        return None, None, None


def write_cycle(snapshot, index):
    with open(CYCLE_FILE, "w") as f:
        f.write(",".join(snapshot) + "\n" + str(index) + "\n" + str(time.time()))


# X auto-repeat fires every ~30ms; deliberate taps are far slower. Ignore
# steps closer together than this so holding Tab doesn't race through.
REPEAT_GUARD_SEC = 0.15

# If the Alt-release bind ever fails to fire (e.g. Alt held through some
# other chord), a leftover cycle file would block ALL focus tracking forever.
# Nobody pauses this long mid-cycle, so treat anything older as abandoned.
CYCLE_STALE_SEC = 3.0


def cycle_in_progress():
    snapshot, index, last_ts = read_cycle()
    if snapshot is None:
        return False
    if time.time() - last_ts > CYCLE_STALE_SEC:
        end_cycle()
        return False
    return True


def step_cycle(direction):
    cycle_in_progress()  # discards (and commits) a stale cycle first
    snapshot, index, last_ts = read_cycle()
    if snapshot is None:
        # first tap: freeze the current MRU order for the whole cycle
        snapshot = read_stack()
        if len(snapshot) < 2:
            return
        index = 0
    elif time.time() - last_ts < REPEAT_GUARD_SEC:
        return
    # step, skipping any window that has since closed
    for _ in range(len(snapshot)):
        index = (index + direction) % len(snapshot)
        if focus_and_maximize(snapshot[index]):
            write_cycle(snapshot, index)
            return
    end_cycle()


def end_cycle():
    snapshot, index, _ = read_cycle()
    if snapshot is None:
        return
    os.remove(CYCLE_FILE)
    # promote only the window we landed on
    landed = snapshot[index]
    stack = read_stack()
    if landed in stack:
        stack.remove(landed)
    stack.insert(0, landed)
    write_stack(stack)


def restore_from_scratchpad():
    """Bring back the most recently minimized window, maximized. Unlike a
    bare `scratchpad show` this never hides anything — it only restores."""
    result = subprocess.run(["i3-msg", "-t", "get_tree"], capture_output=True, text=True)
    try:
        tree = json.loads(result.stdout)
    except json.JSONDecodeError:
        return
    hidden = []

    def walk(node, in_scratch=False):
        in_scratch = in_scratch or node.get("name") == "__i3_scratch"
        if node.get("window") and in_scratch:
            hidden.append(str(node["id"]))
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            walk(child, in_scratch)

    walk(tree)
    if not hidden:
        return
    # prefer the one minimized most recently (highest in focus history)
    stack = read_stack()
    target = next((c for c in stack if c in hidden), hidden[0])
    subprocess.run(["i3-msg", "fullscreen disable"])
    # the scratchpad turns windows floating; put it back in the tiling layer
    # on the way out, otherwise it'd sit above every tiled window forever
    subprocess.run(["i3-msg", f"[con_id={target}] scratchpad show, floating disable, fullscreen enable"])


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    elif "--tab" in sys.argv:
        step_cycle(+1)
    elif "--tab-back" in sys.argv:
        step_cycle(-1)
    elif "--release" in sys.argv:
        end_cycle()
    elif "--restore" in sys.argv:
        restore_from_scratchpad()
