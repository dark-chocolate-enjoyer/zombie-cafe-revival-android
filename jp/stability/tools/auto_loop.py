#!/usr/bin/env python3
"""Automated crash-reproduction loop on the A54 (2026-10-09).

  python3 auto_loop.py RUN_NAME ROUNDS

Each round: force-stop + launch the installed game, wait for the menu, tap Play, wait until the log
shows the player's cafe loaded, wait a random 0.3-3.0 s, tap Map, then classify the outcome from the
log: survived (map loaded), Scudo crash, GWP-ASan report, other crash, or no cafe (tap missed).
Writes logs/<date>_<RUN_NAME>_logcat.txt (full phone log) and logs/<date>_<RUN_NAME>_results.tsv.
Only ever taps Play (menu) and Map (cafe); coordinates for the 2340x1080 A54 in landscape.
"""
import os, random, re, subprocess, sys, time

ADB = '/mnt/c/platform-tools/adb.exe'
PKG = 'com.capcom.zombiecafeandroidJP'
PLAY, MAP = (1942, 825), (164, 175)
HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(os.path.dirname(HERE), 'logs')


def adb(*a, timeout=30):
    return subprocess.run([ADB, *a], capture_output=True, text=True, timeout=timeout).stdout


def tap(xy):
    adb('shell', 'input', 'swipe', str(xy[0]), str(xy[1]), str(xy[0]), str(xy[1]), '150')


def alive(p):
    """Is process p still running? (pidof can briefly list the launcher process under the game's name)"""
    return p in adb('shell', 'pidof', PKG).split()


def started_pid(logfile, offset, timeout=20):
    """The game's real process id, from ActivityManager's "Start proc <pid>:<package>" log line."""
    rx = re.compile(r'Start proc (\d+):' + re.escape(PKG) + '/')
    end = time.time() + timeout
    while time.time() < end:
        with open(logfile, errors='replace') as fh:
            fh.seek(offset)
            m = rx.search(fh.read())
        if m:
            return m.group(1)
        time.sleep(0.25)
    return ''


def wait_for(logfile, pattern, p, timeout, offset=0):
    """Wait until a line of process p matching pattern appears (reading from offset); True/False."""
    rx = re.compile(pattern)
    end = time.time() + timeout
    while time.time() < end:
        with open(logfile, errors='replace') as fh:
            fh.seek(offset)
            for line in fh:
                f = line.split()
                if len(f) > 4 and f[2] == p and rx.search(line):
                    return True
        if not alive(p):
            return False
        time.sleep(0.25)
    return False


def crash_summary(logfile, p, offset=0):
    """Cause/abort line and first game-library frames from the crash report of process p."""
    with open(logfile, errors='replace') as fh:
        fh.seek(offset)
        lines = fh.read().splitlines()
    start = next((i for i, l in enumerate(lines) if f'pid: {p}, tid:' in l and ' DEBUG ' in l), None)
    if start is None:
        return 'other', 'no crash report found (killed?)'
    block = lines[start:start + 120]
    cause = next((l.split('DEBUG   : ', 1)[1] for l in block if 'Abort message:' in l or 'Cause:' in l), '')
    frames = [m.group(1) for m in (re.search(r'libZombieCafeAndroid\.so \((.*)\)\s*(\(BuildId.*)?$', l) for l in block) if m][:4]
    kind = 'gwp-asan' if 'GWP-ASan' in cause else 'scudo' if 'Scudo' in cause else 'other'
    return kind, f"{cause} | {' <- '.join(frames)}"


def main():
    run, rounds = sys.argv[1], int(sys.argv[2])
    stamp = time.strftime('%Y-%m-%d')
    logfile = os.path.join(LOGS, f'{stamp}_{run}_logcat.txt')
    results = os.path.join(LOGS, f'{stamp}_{run}_results.tsv')
    adb('logcat', '-b', 'main,system,crash,events', '-c')
    adb('shell', 'svc', 'power', 'stayon', 'usb')                  # screen stays on while on USB; undone below
    cat = subprocess.Popen([ADB, 'logcat', '-b', 'all', '-v', 'threadtime'],
                           stdout=open(logfile, 'w'), stderr=subprocess.STDOUT)
    with open(results, 'w') as out:
        out.write('round\ttime\tpid\tdelay_s\toutcome\tdetail\n')
        for r in range(1, rounds + 1):
            adb('shell', 'am', 'force-stop', PKG)
            time.sleep(1)
            off = os.path.getsize(logfile)
            adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
            adb('shell', 'am', 'start', '--user', '0', '-n', f'{PKG}/.ZombieCafeAndroid')
            p = started_pid(logfile, off)
            wait_for(logfile, r'readFile :: images/menuTitleOffsets\.bin\.mid = ', p, 40, off)
            time.sleep(1.5)                                      # menu drawn
            tap(PLAY)
            if not wait_for(logfile, r'readFile :: playerCafe\.caf = ', p, 20, off):
                kind, detail = (crash_summary(logfile, p, off) if not alive(p) else ('no-cafe', 'cafe did not load'))
                delay = ''
            else:
                delay = round(random.uniform(0.3, 3.0), 2)
                time.sleep(delay)
                tap(MAP)
                if wait_for(logfile, r'readFile :: images/mapTiles\.cct\.mid = ', p, 8, off):
                    time.sleep(2)                                # a crash right after the map loads
                kind, detail = ('survived', 'map loaded') if alive(p) else crash_summary(logfile, p, off)
                if kind == 'survived':
                    k2, d2 = crash_summary(logfile, p, off)        # a report while still alive = recovered
                    if k2 != 'other':
                        kind, detail = k2 + ' (recovered)', d2
            row = f'{r}\t{time.strftime("%H:%M:%S")}\t{p}\t{delay}\t{kind}\t{detail}'
            out.write(row + '\n')
            out.flush()
            print(row, flush=True)
    adb('shell', 'am', 'force-stop', PKG)
    adb('shell', 'svc', 'power', 'stayon', 'false')
    cat.terminate()


if __name__ == '__main__':
    main()
