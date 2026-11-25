"""Async views mirroring the ASP.NET PoC. One psycopg AsyncConnectionPool per worker process."""
import asyncio
import os
import re

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from psycopg_pool import AsyncConnectionPool

POOL = None
_POOL_LOCK = asyncio.Lock()


async def pool():
    global POOL
    if POOL is None:
        async with _POOL_LOCK:
            if POOL is None:
                p = AsyncConnectionPool(settings.MIMAMSA_DB, min_size=2, max_size=settings.MIMAMSA_POOL_MAX, open=False)
                await p.open()
                POOL = p
    return POOL


class AuthStubMiddleware:
    """Fixed bearer token on /api/*; placeholder for Windows Integrated Auth / local accounts."""
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request):
        if request.path.startswith("/api/") and request.headers.get("Authorization") != f"Bearer {settings.MIMAMSA_DEV_TOKEN}":
            return HttpResponse(status=401)
        return await self.get_response(request)


async def health(request):
    return HttpResponse("ok", content_type="text/plain")


SEARCH_SQL = """
WITH q AS (SELECT replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery AS q)
SELECT u.doc_id, max(ts_rank(u.tsv, q.q)) AS s FROM units u, q
WHERE u.tsv @@ q.q GROUP BY u.doc_id ORDER BY s DESC LIMIT %s"""


async def search(request):
    q = request.GET.get("q", "")
    lim = max(1, min(50, int(request.GET.get("limit", 10))))
    p = await pool()
    async with p.connection() as conn:
        cur = await conn.execute(SEARCH_SQL, (q, lim))
        rows = await cur.fetchall()
    return JsonResponse({"q": q, "results": [{"doc_id": d, "score": float(s)} for d, s in rows]})


async def document(request, doc_id):
    p = await pool()
    async with p.connection() as conn:
        cur = await conn.execute("SELECT meta::text FROM documents WHERE doc_id = %s", (doc_id,))
        row = await cur.fetchone()
    if not row:
        return HttpResponse(status=404)
    return HttpResponse(row[0], content_type="application/json")


RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


async def _file_iter(path, start, length, chunk=64 * 1024):
    # blocking file reads are pushed to a thread so the event loop is not stalled
    f = await asyncio.to_thread(open, path, "rb")
    try:
        await asyncio.to_thread(f.seek, start)
        remaining = length
        while remaining > 0:
            data = await asyncio.to_thread(f.read, min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data
    finally:
        f.close()


async def pdf(request, doc_id):
    p = await pool()
    async with p.connection() as conn:
        cur = await conn.execute("SELECT pdf_file FROM documents WHERE doc_id = %s", (doc_id,))
        row = await cur.fetchone()
    if not row or not row[0]:
        return HttpResponse(status=404)
    root = settings.MIMAMSA_PDF_ROOT
    full = (root / row[0]).resolve()
    if root not in full.parents or not full.is_file():
        return HttpResponse(status=404)
    size = full.stat().st_size
    # Django's FileResponse has no Range support; PDF.js relies on it for large files, so it is done here.
    m = RANGE_RE.match(request.headers.get("Range", ""))
    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            start = int(m.group(1)); end = int(m.group(2)) if m.group(2) else size - 1
        else:
            start = max(0, size - int(m.group(2))); end = size - 1
        if start >= size or end < start:
            r = HttpResponse(status=416); r["Content-Range"] = f"bytes */{size}"; return r
        end = min(end, size - 1)
        resp = StreamingHttpResponse(_file_iter(full, start, end - start + 1), status=206, content_type="application/pdf")
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
        resp["Content-Length"] = str(end - start + 1)
    else:
        resp = StreamingHttpResponse(_file_iter(full, 0, size), content_type="application/pdf")
        resp["Content-Length"] = str(size)
    resp["Accept-Ranges"] = "bytes"
    return resp
