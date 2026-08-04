"""Narrow Windows Job Object ownership adapter for probe subprocess trees."""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from typing import Protocol

_OWNERSHIP_ESTABLISH_FAILED = "Windows process ownership could not be established."
_OWNERSHIP_RELEASE_FAILED = "Windows process ownership could not be released."
_OWNERSHIP_UNAVAILABLE = "Windows process ownership is unavailable."

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_SET_QUOTA = 0x0100

    class _JobObjectBasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JobObjectExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JobObjectBasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]


class WindowsJobError(RuntimeError):
    """Report a finite Windows process ownership failure."""


class WindowsJobApi(Protocol):
    """Operations required to own one Windows subprocess tree."""

    def create_job(self) -> object: ...

    def configure_kill_on_close(self, job_handle: object) -> None: ...

    def assign_process(self, job_handle: object, pid: int) -> None: ...

    def close_handle(self, handle: object) -> None: ...


if os.name == "nt":

    class _CtypesWindowsJobApi:
        def __init__(self) -> None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._create_job = kernel32.CreateJobObjectW
            self._create_job.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            self._create_job.restype = wintypes.HANDLE
            self._set_information = kernel32.SetInformationJobObject
            self._set_information.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            self._set_information.restype = wintypes.BOOL
            self._open_process = kernel32.OpenProcess
            self._open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            self._open_process.restype = wintypes.HANDLE
            self._assign_process = kernel32.AssignProcessToJobObject
            self._assign_process.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            self._assign_process.restype = wintypes.BOOL
            self._close_handle = kernel32.CloseHandle
            self._close_handle.argtypes = [wintypes.HANDLE]
            self._close_handle.restype = wintypes.BOOL

        def create_job(self) -> object:
            handle = self._create_job(None, None)
            if not handle:
                raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED)
            return handle

        def configure_kill_on_close(self, job_handle: object) -> None:
            limits = _JobObjectExtendedLimitInformation()
            limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            configured = self._set_information(
                job_handle,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                ctypes.byref(limits),
                ctypes.sizeof(limits),
            )
            if not configured:
                raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED)

        def assign_process(self, job_handle: object, pid: int) -> None:
            process_handle = self._open_process(
                _PROCESS_SET_QUOTA | _PROCESS_TERMINATE,
                False,  # noqa: FBT003 - WinAPI positional BOOL parameter.
                pid,
            )
            if not process_handle:
                raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED)
            try:
                if not self._assign_process(job_handle, process_handle):
                    raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED)
            finally:
                if not self._close_handle(process_handle):
                    raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED) from None

        def close_handle(self, handle: object) -> None:
            if not self._close_handle(handle):
                raise WindowsJobError(_OWNERSHIP_RELEASE_FAILED)


@dataclass
class WindowsJobOwner:
    """Own a configured Job Object handle until probe cleanup completes."""

    _api: WindowsJobApi
    _handle: object | None

    @classmethod
    def create(cls, *, api: WindowsJobApi) -> WindowsJobOwner:
        try:
            handle = api.create_job()
        except Exception:  # noqa: BLE001 - the adapter emits one finite ownership failure.
            raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED) from None
        try:
            api.configure_kill_on_close(handle)
        except BaseException as error:
            with contextlib.suppress(Exception):
                api.close_handle(handle)
            if not isinstance(error, Exception):
                raise
            raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED) from None
        return cls(_api=api, _handle=handle)

    def assign(self, pid: int) -> None:
        handle = self._require_handle()
        try:
            self._api.assign_process(handle, pid)
        except Exception:  # noqa: BLE001 - the adapter emits one finite ownership failure.
            raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED) from None

    def close(self) -> None:
        handle = self._handle
        if handle is None:
            return
        self._handle = None
        try:
            self._api.close_handle(handle)
        except Exception:  # noqa: BLE001 - the adapter emits one finite ownership failure.
            raise WindowsJobError(_OWNERSHIP_RELEASE_FAILED) from None

    def _require_handle(self) -> object:
        if self._handle is None:
            raise WindowsJobError(_OWNERSHIP_UNAVAILABLE)
        return self._handle


def create_windows_job_owner(*, api: WindowsJobApi | None = None) -> WindowsJobOwner:
    """Create a configured owner without importing ctypes off Windows."""
    if api is None:
        if os.name != "nt":
            raise WindowsJobError(_OWNERSHIP_UNAVAILABLE)
        try:
            api = _CtypesWindowsJobApi()
        except Exception:  # noqa: BLE001 - native loader details stay behind the adapter.
            raise WindowsJobError(_OWNERSHIP_ESTABLISH_FAILED) from None
    return WindowsJobOwner.create(api=api)
