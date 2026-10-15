#!/system/bin/sh
# Starts the game under bionic malloc debug. Packed only into the MALLOC_DEBUG test APK
# (make_debug_apk.py); Android runs it at launch because that APK is debuggable.
#   guard=64        64-byte guard zones before and after every block: an overflow lands in the
#                   writer's own guard and is reported (size, bad bytes, stack that frees it)
#   free_track=16384 keep the last 16384 freed blocks (the maximum) filled with 0xef: a later read of a
#                   freed pointer crashes on 0xefefefef at the line that uses it; writes are reported
#   free_track_backtrace_num_frames=0, no "backtrace": per-allocation stacks use libc's unwinder,
#                   which calls the game's own 2016 __gxx_personality_v0 and crashes at startup (run 1)
#   backtrace_full  error reports unwind with libunwindstack (as the crash reporter does), which
#                   reads the game's unwind tables without calling its personality routine
#   verify_pointers report frees of pointers malloc never returned
#   verbose         log "malloc debug enabled" at start, so we can confirm it is active
LIBC_DEBUG_MALLOC_OPTIONS="guard=64 free_track=16384 free_track_backtrace_num_frames=0 backtrace_full verify_pointers verbose" exec "$@"
