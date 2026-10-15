#!/system/bin/sh
# Starts the game with GWP-ASan on top of the normal allocator (Scudo). Packed only into the
# GWP_ASAN test APK (make_debug_apk.py --mode gwp); Android runs it at launch because that APK is debuggable.
# A sampled block gets its own page, flush against a no-access guard page (left or right at random),
# so an overflow, underflow or use-after-free on it faults at the instruction itself. The crash
# report says "Cause: [GWP-ASan]: ...".
#   GWP_ASAN_PROCESS_SAMPLING=1   enable in every launch (apps default to a small fraction of launches)
#   GWP_ASAN_SAMPLE_RATE=24       sample 1 in 24 allocations on average (production uses 1 in thousands);
#                                 the game has ~590k live allocations in the cafe, 590k/24 fits in the slots
#   GWP_ASAN_MAX_ALLOCS=26000     sampled blocks alive at once: 2 memory regions each (slot + guard),
#                                 ~52k + the game's ~3k stays under the kernel's 65,530-region limit;
#                                 16384 were all used up during startup (2026-10-09)
#   GWP_ASAN_RECOVERABLE=true     report, then let the game continue, so one session can report more
export GWP_ASAN_PROCESS_SAMPLING=1
export GWP_ASAN_SAMPLE_RATE=24
export GWP_ASAN_MAX_ALLOCS=26000
export GWP_ASAN_RECOVERABLE=true
# libc ignores these variables in programs named app_process* (so they can't leak from the Zygote into
# every app), and $1 is /system/bin/app_process32. exec -a starts it under another name (argv[0]).
exec -a zc_gwpasan_app32 "$@"
