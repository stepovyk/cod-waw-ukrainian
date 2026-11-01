"""Знімає EIP найзавантаженішого потоку 32-бітного процесу кілька разів (діагностика зависань)."""
import ctypes, ctypes.wintypes as wt, sys, time, collections

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
TH32CS_SNAPTHREAD = 4
THREAD_ALL = 0x1FFFFF


class THREADENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD), ('th32ThreadID', wt.DWORD),
                ('th32OwnerProcessID', wt.DWORD), ('tpBasePri', ctypes.c_long), ('tpDeltaPri', ctypes.c_long),
                ('dwFlags', wt.DWORD)]


class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [('ContextFlags', wt.DWORD), ('pad', ctypes.c_byte * (0xB8 - 4)), ('Eip', wt.DWORD),
                ('rest', ctypes.c_byte * (0x2CC - 0xBC))]


def threads(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    te = THREADENTRY32(); te.dwSize = ctypes.sizeof(te)
    out = []
    ok = k32.Thread32First(snap, ctypes.byref(te))
    while ok:
        if te.th32OwnerProcessID == pid:
            out.append(te.th32ThreadID)
        ok = k32.Thread32Next(snap, ctypes.byref(te))
    k32.CloseHandle(snap)
    return out


def cpu(h):
    c, e, k, u = (wt.FILETIME() for _ in range(4))
    k32.GetThreadTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u))
    return (u.dwHighDateTime << 32 | u.dwLowDateTime) + (k.dwHighDateTime << 32 | k.dwLowDateTime)


pid = int(sys.argv[1])
hs = {t: k32.OpenThread(THREAD_ALL, False, t) for t in threads(pid)}
t0 = {t: cpu(h) for t, h in hs.items()}
time.sleep(2)
load = sorted(hs, key=lambda t: cpu(hs[t]) - t0[t], reverse=True)
for tid in load[:int(sys.argv[2]) if len(sys.argv) > 2 else 4]:
    h = hs[tid]
    c = collections.Counter()
    for _ in range(100):
        k32.Wow64SuspendThread(h)
        ctx = WOW64_CONTEXT(); ctx.ContextFlags = 0x10001  # CONTEXT_i386 | CONTROL
        k32.Wow64GetThreadContext(h, ctypes.byref(ctx))
        k32.ResumeThread(h)
        c[ctx.Eip] += 1
        time.sleep(0.005)
    print('потік', tid, 'cpu', (cpu(h) - t0[tid]) // 10000, 'мс:', ' '.join(f'{e:x}:{n}' for e, n in c.most_common(6)))
