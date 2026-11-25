"""Windows Service host for the Django PoC: hypercorn (ASGI) inside a pywin32 ServiceFramework.

Install (elevated):   python winservice.py --startup auto install
Account:              sc.exe config MimamsaPocDjango obj= "NT SERVICE\\MimamsaPocDjango"  (virtual account)
Environment:          HKLM\\SYSTEM\\CurrentControlSet\\Services\\MimamsaPocDjango\\Environment (REG_MULTI_SZ)

Notes (PoC findings, NOT yet validated on Windows):
- psycopg's async mode does not work on the default ProactorEventLoop on Windows, so a SelectorEventLoop is used.
- One process = one GIL. Multi-worker hypercorn inside pythonservice.exe needs multiprocessing.set_executable();
  this PoC runs a single worker. Scaling out means several services/ports behind a reverse proxy, or IIS.
"""
import asyncio
import os
import sys
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

HERE = Path(__file__).resolve().parent


class MimamsaDjangoService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MimamsaPocDjango"
    _svc_display_name_ = "Mimamsa PoC (Django + hypercorn)"
    _svc_description_ = "Mimamsa offline research platform: Django ASGI PoC service."

    def __init__(self, args):
        super().__init__(args)
        self.stop_handle = win32event.CreateEvent(None, 0, 0, None)
        self.loop = None
        self.shutdown = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.loop and self.shutdown:
            self.loop.call_soon_threadsafe(self.shutdown.set)
        win32event.SetEvent(self.stop_handle)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ""))
        os.chdir(HERE)
        sys.path.insert(0, str(HERE))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mimamsa_poc.settings")
        from hypercorn.asyncio import serve
        from hypercorn.config import Config
        from mimamsa_poc.asgi import application

        cfg = Config()
        cfg.bind = [os.environ.get("MIMAMSA_BIND", "127.0.0.1:5082")]
        cfg.accesslog = None
        cfg.errorlog = str(Path(os.environ.get("MIMAMSA_LOG_DIR", HERE)) / "hypercorn-error.log")
        self.loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(self.loop)
        self.shutdown = asyncio.Event()
        self.loop.run_until_complete(serve(application, cfg, shutdown_trigger=self.shutdown.wait))
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STOPPED, (self._svc_name_, ""))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MimamsaDjangoService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(MimamsaDjangoService)
