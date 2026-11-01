"""Small Windows process-memory adapter. No DLL injection or remote threads."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path


class ProcessEntry(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('pid', W.DWORD),
                ('heap', C.c_size_t), ('module', W.DWORD), ('threads', W.DWORD),
                ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD),
                ('exe', W.WCHAR * 260)]


class ModuleEntry(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('module', W.DWORD), ('pid', W.DWORD),
                ('global_usage', W.DWORD), ('usage', W.DWORD), ('base', C.c_void_p),
                ('size', W.DWORD), ('handle', W.HMODULE), ('name', W.WCHAR * 256),
                ('path', W.WCHAR * 260)]


def kernel():
    k = C.WinDLL('kernel32', use_last_error=True)
    bindings = {
        'CreateToolhelp32Snapshot': ([W.DWORD, W.DWORD], W.HANDLE),
        'Process32FirstW': ([W.HANDLE, C.POINTER(ProcessEntry)], W.BOOL),
        'Process32NextW': ([W.HANDLE, C.POINTER(ProcessEntry)], W.BOOL),
        'Module32FirstW': ([W.HANDLE, C.POINTER(ModuleEntry)], W.BOOL),
        'Module32NextW': ([W.HANDLE, C.POINTER(ModuleEntry)], W.BOOL),
        'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        'CloseHandle': ([W.HANDLE], W.BOOL),
        'ReadProcessMemory': ([W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)], W.BOOL),
        'WriteProcessMemory': ([W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)], W.BOOL),
        'GetExitCodeProcess': ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
    }
    for name, (args, result) in bindings.items():
        fn = getattr(k, name)
        fn.argtypes, fn.restype = args, result
    return k


class ProcessMemory:
    def __init__(self, expected_path, writable=False):
        self.k = kernel()
        self.handle = None
        self.writable = writable
        snapshot = self.k.CreateToolhelp32Snapshot(2, 0)
        if snapshot == C.c_void_p(-1).value:
            raise C.WinError(C.get_last_error())
        found = []
        try:
            entry = ProcessEntry(dwSize=C.sizeof(ProcessEntry))
            ok = self.k.Process32FirstW(snapshot, C.byref(entry))
            while ok:
                if entry.exe.casefold() == 'nms.exe':
                    found.append(entry.pid)
                ok = self.k.Process32NextW(snapshot, C.byref(entry))
        finally:
            self.k.CloseHandle(snapshot)
        if len(found) != 1:
            raise RuntimeError('Tek bir NMS.exe açık olmalı. Oyunu açıp kayıt içine girin.')
        self.pid = found[0]
        snapshot = self.k.CreateToolhelp32Snapshot(0x18, self.pid)
        if snapshot == C.c_void_p(-1).value:
            raise C.WinError(C.get_last_error())
        try:
            module = ModuleEntry(dwSize=C.sizeof(ModuleEntry))
            ok = self.k.Module32FirstW(snapshot, C.byref(module))
            if not ok or Path(module.path).resolve() != Path(expected_path).resolve():
                raise RuntimeError('Açık oyun bu kurulumla eşleşmiyor.')
            self.base, self.size = module.base, module.size
        finally:
            self.k.CloseHandle(snapshot)
        rights = 0x1000 | 0x10 | (0x28 if writable else 0)
        self.handle = self.k.OpenProcess(rights, False, self.pid)
        if not self.handle:
            raise C.WinError(C.get_last_error())

    def alive(self):
        code = W.DWORD()
        return bool(self.handle and self.k.GetExitCodeProcess(self.handle, C.byref(code)) and code.value == 259)

    def read(self, address, size):
        if not self.alive():
            raise RuntimeError('Oyun oturumu kapandı; yeniden bağlanın.')
        buffer = C.create_string_buffer(size)
        count = C.c_size_t()
        if not self.k.ReadProcessMemory(self.handle, address, buffer, size, C.byref(count)) or count.value != size:
            raise C.WinError(C.get_last_error())
        return buffer.raw

    def write(self, address, data):
        if not self.writable or not self.alive():
            raise RuntimeError('Yazılabilir oyun bağlantısı yok.')
        buffer = C.create_string_buffer(data)
        count = C.c_size_t()
        if not self.k.WriteProcessMemory(self.handle, address, buffer, len(data), C.byref(count)) or count.value != len(data):
            raise C.WinError(C.get_last_error())

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None
