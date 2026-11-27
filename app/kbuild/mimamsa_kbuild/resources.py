"""Shared-host resource budget (B02 spec section 4, SG-6, RC-9).

The build host is shared with Codex's OCR. The spec carries a MEASURED budget; this module
- measures the host (logical CPUs, physical memory, free disk);
- computes the effective budget: the spec's limits, further capped on a shared host at half of what is measured NOW
  (a spec measured on a bigger machine can never take more than half of this one);
- applies it to the build process and every child it starts:
    Windows: a Job Object holding the build process (children inherit membership) with a hard job-wide memory limit,
             a hard CPU-rate cap of max_workers/logical_cpus of the machine and a below-normal priority class for
             every process in the job; the build process's I/O priority is set to LOW or VERY_LOW;
    POSIX:   nice only; the memory hard stop (a cgroup) and I/O priority are recorded as not applied;
- reads every setting back from the OS, so the build record states what was actually applied, not what was asked;
- checks disk: the build tree may not exceed max_disk_bytes and the volume keeps a free-space floor.
Memory and disk limits are hard stops: the build fails rather than starve the co-tenant. These are development
defaults and configurable, not final production decisions.
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .errors import BuildRefused

IS_WINDOWS = sys.platform == "win32"
MIN_FREE_DISK_BYTES = 5 << 30   # floor kept free on the output volume for the co-tenant (configurable via env)

# Windows constants
_BELOW_NORMAL, _IDLE, _NORMAL = 0x4000, 0x40, 0x20
_PRIORITY = {"BELOW_NORMAL": _BELOW_NORMAL, "IDLE": _IDLE, "NORMAL": _NORMAL}
_PRIORITY_NAME = {v: k for k, v in _PRIORITY.items()}
_IO_PRIORITY = {"VERY_LOW": 0, "LOW": 1, "NORMAL": 2}
_IO_NAME = {v: k for k, v in _IO_PRIORITY.items()}


@dataclass
class HostMeasurement:
    logical_cpus: int
    memory_bytes: int
    free_disk_bytes: int | None = None


@dataclass
class Budget:
    shared_host: bool
    workers: int
    memory_bytes: int
    disk_bytes: int
    cpu_priority: str
    io_priority: str
    measured_now: dict = field(default_factory=dict)
    applied: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def _windows_memory() -> int:
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    return int(st.ullTotalPhys)


def measure_host(path: Path | None = None) -> HostMeasurement:
    cpus = os.cpu_count() or 1
    if IS_WINDOWS:
        mem = _windows_memory()
    else:
        mem = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    free = None
    if path is not None:
        p = Path(path)
        while not p.exists() and p.parent != p:
            p = p.parent
        free = shutil.disk_usage(p).free
    return HostMeasurement(cpus, int(mem), free)


def effective_budget(spec: dict, host: HostMeasurement) -> Budget:
    r = spec["resources"]
    workers, memory = r["max_workers"], r["max_memory_bytes"]
    if r["shared_host"]:
        workers = min(workers, max(1, host.logical_cpus // 2))
        memory = min(memory, host.memory_bytes // 2)
    return Budget(shared_host=r["shared_host"], workers=max(1, workers), memory_bytes=memory, disk_bytes=r["max_disk_bytes"],
                  cpu_priority=r["cpu_priority"], io_priority=r["io_priority"], measured_now=asdict(host))


def stage_workers(spec: dict, stage_id: str, budget: Budget) -> int:
    s = next(x for x in spec["stages"] if x["stage_id"] == stage_id)
    return max(1, min(s["max_workers"], budget.workers))


# ------------------------------------------------------------------ Windows job object

_JOB = None   # keep the handle for the life of the process


def _win_apply(budget: Budget) -> dict:
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.GetPriorityClass.argtypes = [wintypes.HANDLE]
    ntdll.NtSetInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG]
    ntdll.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG, ctypes.c_void_p]

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IOC(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class EXT(ctypes.Structure):
        _fields_ = [("Basic", BASIC), ("Io", IOC), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class CPURATE(ctypes.Structure):
        _fields_ = [("ControlFlags", wintypes.DWORD), ("CpuRate", wintypes.DWORD)]

    JOB_MEMORY, PRIORITY_CLASS = 0x200, 0x20
    EXTENDED, CPU_RATE = 9, 15
    ENABLE, HARD_CAP = 0x1, 0x4
    global _JOB
    out: dict = {"platform": "windows"}
    me = k32.GetCurrentProcess()
    prio = _PRIORITY[budget.cpu_priority]
    k32.SetPriorityClass(me, prio)
    io = ctypes.c_ulong(_IO_PRIORITY[budget.io_priority])
    out["io_priority_set_status"] = ntdll.NtSetInformationProcess(me, 33, ctypes.byref(io), 4)

    job = k32.CreateJobObjectW(None, None)
    if not job:
        out["job"] = f"CreateJobObject failed ({ctypes.get_last_error()})"
    else:
        ext = EXT()
        ext.Basic.LimitFlags = JOB_MEMORY | PRIORITY_CLASS
        ext.Basic.PriorityClass = prio
        ext.JobMemoryLimit = budget.memory_bytes
        ok_ext = k32.SetInformationJobObject(job, EXTENDED, ctypes.byref(ext), ctypes.sizeof(ext))
        rate = CPURATE(ENABLE | HARD_CAP, max(1, min(10000, int(10000 * budget.workers / max(1, budget.measured_now.get("logical_cpus", 1))))))
        ok_cpu = k32.SetInformationJobObject(job, CPU_RATE, ctypes.byref(rate), ctypes.sizeof(rate))
        ok_assign = k32.AssignProcessToJobObject(job, me)
        out["job"] = {"set_limits": bool(ok_ext), "set_cpu_rate": bool(ok_cpu), "assigned": bool(ok_assign),
                      "error": None if ok_assign else ctypes.get_last_error()}
        if ok_assign:
            _JOB = job
            back = EXT()
            k32.QueryInformationJobObject(job, EXTENDED, ctypes.byref(back), ctypes.sizeof(back), None)
            rb = CPURATE()
            k32.QueryInformationJobObject(job, CPU_RATE, ctypes.byref(rb), ctypes.sizeof(rb), None)
            out["job"].update(job_memory_limit_bytes=int(back.JobMemoryLimit),
                              priority_class=_PRIORITY_NAME.get(back.Basic.PriorityClass, hex(back.Basic.PriorityClass)),
                              cpu_rate_hard_cap_percent=(rb.CpuRate / 100.0) if rb.ControlFlags & HARD_CAP else None)
    got = k32.GetPriorityClass(me)
    io_back = ctypes.c_ulong(99)
    ntdll.NtQueryInformationProcess(me, 33, ctypes.byref(io_back), 4, None)
    out["process_priority_class"] = _PRIORITY_NAME.get(got, hex(got))
    out["process_io_priority"] = _IO_NAME.get(io_back.value, str(io_back.value))
    return out


def _posix_apply(budget: Budget) -> dict:
    out: dict = {"platform": sys.platform}
    try:
        cur = os.nice(0)
        target = 19 if budget.cpu_priority == "IDLE" else 10 if budget.cpu_priority == "BELOW_NORMAL" else 0
        if target > cur:
            os.nice(target - cur)
        out["nice"] = os.nice(0)
    except OSError as exc:
        out["nice"] = f"not applied: {exc}"
    # RLIMIT_AS is not used: the .NET runtime reserves far more address space than it commits, so an address-space cap
    # breaks the S6 helper. A hard memory stop on Linux needs a cgroup (e.g. systemd-run --scope -p MemoryMax=...);
    # here the .NET child is bounded by DOTNET_GCHeapHardLimit only. Recorded, not hidden.
    out["memory_hard_limit"] = "not applied on this platform (use a cgroup); .NET child bounded by DOTNET_GCHeapHardLimit"
    out["process_io_priority"] = "not applied on this platform"
    return out


def apply_budget(budget: Budget) -> Budget:
    """Apply the budget to this process (and, through the job / inheritance, to every child). Idempotent per process."""
    if budget.applied:
        return budget
    budget.applied = _win_apply(budget) if IS_WINDOWS else _posix_apply(budget)
    check_applied(budget)
    return budget


def check_applied(budget: Budget) -> None:
    """Fail closed when a shared-host build is not actually running bounded."""
    if not budget.shared_host:
        return
    a = budget.applied
    if IS_WINDOWS:
        job = a.get("job") if isinstance(a.get("job"), dict) else {}
        problems = []
        if a.get("process_priority_class") not in ("BELOW_NORMAL", "IDLE"):
            problems.append("process priority is not below normal")
        if a.get("process_io_priority") not in ("LOW", "VERY_LOW"):
            problems.append("process I/O priority is not low")
        if not job.get("assigned") or job.get("job_memory_limit_bytes") != budget.memory_bytes:
            problems.append("job-wide memory limit not in force")
        if job.get("cpu_rate_hard_cap_percent") is None:
            problems.append("CPU-rate hard cap not in force")
        if problems:
            raise BuildRefused("BUILD_RESOURCES_NOT_APPLIED", "; ".join(problems))


def child_env(budget: Budget, workers: int) -> dict:
    """Environment for a .NET child: bounded processors and GC heap; never server GC."""
    env = dict(os.environ)
    env.update({
        "DOTNET_PROCESSOR_COUNT": str(workers),
        "DOTNET_gcServer": "0",
        "DOTNET_GCHeapHardLimit": hex(max(256 << 20, budget.memory_bytes // 2)),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_NOLOGO": "1",
    })
    return env


def child_creationflags(budget: Budget) -> int:
    if not IS_WINDOWS:
        return 0
    return _PRIORITY.get(budget.cpu_priority, _BELOW_NORMAL) if budget.cpu_priority != "NORMAL" else 0


def check_disk(budget: Budget, build_root: Path, stage: str) -> dict:
    used = sum(p.stat().st_size for p in build_root.rglob("*") if p.is_file()) if build_root.exists() else 0
    free = shutil.disk_usage(build_root if build_root.exists() else build_root.parent).free
    floor = int(os.environ.get("MIMAMSA_KBUILD_MIN_FREE_BYTES", MIN_FREE_DISK_BYTES))
    if used > budget.disk_bytes:
        raise BuildRefused("BUILD_DISK_BUDGET", f"build tree uses {used} bytes, over max_disk_bytes {budget.disk_bytes}", stage)
    if free < floor:
        raise BuildRefused("BUILD_DISK_FLOOR", f"free space {free} below the co-tenant floor {floor}", stage)
    return {"build_tree_bytes": used, "volume_free_bytes": free}
