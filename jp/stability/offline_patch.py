#!/usr/bin/env python3
"""Make the game believe it has no internet, so it stops calling Capcom's dead servers (2026-10-09).

  python3 offline_patch.py SMALI_DIR

SMALI_DIR = an `apktool d -r` decode of the APK. Rewrites `URLManager.a(Context)` (the one connectivity
check: it asks Android for the active network and sets the "connected" flag `ZombieCafeAndroid.b`) to
always clear the flag and answer "not connected". `ZombieCafeAndroid.isConnected()`, the native side's
`fromNative_IsConnected()` and every `URLManager` request method go through it, so the game takes
Capcom's own no-internet path: the native code skips requests that check first, and `URLManager`
answers the rest at once with a failure ("Internet IS NOT CONNECTING!") without touching the network.

Not covered (no connectivity check of their own): `CC_Android.OpenHttpConnection`,
`ZombieCafeAndroid.DownloadFromUrlForPurchase` (buying), `ZombieCafeAndroid.sendRegistrationIdToBackend`
(push registration). None is part of the burst of requests at every cafe load.
"""
import os, re, sys

PKG = 'com/capcom/zombiecafeandroidJP'
SIG = '.method public a(Landroid/content/Context;)Z'
NEW = f'''{SIG}
    .locals 1

    # offline_patch.py: always "not connected" (was: ConnectivityManager.getActiveNetworkInfo())
    const/4 v0, 0x0

    sput-boolean v0, L{PKG}/ZombieCafeAndroid;->b:Z

    return v0
.end method'''


def main():
    path = os.path.join(sys.argv[1], 'smali', PKG, 'URLManager.smali')
    s = open(path).read()
    pat = re.compile(re.escape(SIG) + r'\n.*?\n\.end method', re.S)
    assert len(pat.findall(s)) == 1, 'URLManager.a(Context) not found exactly once'
    assert 'getActiveNetworkInfo' in pat.search(s).group(0), 'unexpected body: already patched?'
    open(path, 'w').write(pat.sub(lambda m: NEW, s))
    print('URLManager.a(Context) -> always "not connected"')


if __name__ == '__main__':
    main()
