"""Run a trusted CLI job quietly on two low-priority logical processors."""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--log', required=True)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ['--'] else args.command
if not command:
    parser.error('a CLI command is required')
creation_flags = 0
processors = []
if os.name == 'nt':
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = C.c_void_p
    kernel.GetProcessAffinityMask.argtypes = [C.c_void_p, C.POINTER(C.c_size_t), C.POINTER(C.c_size_t)]
    kernel.SetProcessAffinityMask.argtypes = [C.c_void_p, C.c_size_t]
    kernel.SetPriorityClass.argtypes = [C.c_void_p, C.c_uint32]
    handle = kernel.GetCurrentProcess()
    if not kernel.SetPriorityClass(handle, 0x4000):
        raise C.WinError(C.get_last_error())
    process_mask, system_mask = C.c_size_t(), C.c_size_t()
    if not kernel.GetProcessAffinityMask(handle, C.byref(process_mask), C.byref(system_mask)):
        raise C.WinError(C.get_last_error())
    processors = [bit for bit in range(C.sizeof(C.c_size_t) * 8) if process_mask.value & (1 << bit)][-2:]
    if processors and not kernel.SetProcessAffinityMask(handle, sum(1 << bit for bit in processors)):
        raise C.WinError(C.get_last_error())
    creation_flags = 0x08000000 | 0x4000
log = Path(args.log)
log.parent.mkdir(parents=True, exist_ok=True)
with log.open('wb') as output:
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output,
                            stderr=subprocess.STDOUT, creationflags=creation_flags)
print(json.dumps({'exit_code': result.returncode, 'log': str(log),
                  'priority': 'below_normal', 'logical_processors': processors}))
raise SystemExit(result.returncode)
