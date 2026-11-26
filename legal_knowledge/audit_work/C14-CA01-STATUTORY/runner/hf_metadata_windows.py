"""Native, local NTFS sink for one private WP1 metadata receipt.

The owner pre-provisions a dedicated jobs directory with a protected DACL
for the running account and Windows SYSTEM. The account, SYSTEM and host
administrators are trusted. Opening this sink grants no network authority.
"""
from __future__ import annotations

import ctypes as ct
import os
import re
from contextlib import ExitStack, contextmanager
from ctypes import wintypes as wt
from pathlib import PureWindowsPath

RECEIPT_NAME = 'metadata_inventory.json'
MAX_RECEIPT_BYTES = 24_000_000
_TEMP_NAME = 'metadata_inventory.pending'
_INVALID_HANDLE = ct.c_void_p(-1).value
_SYSTEM_SID = 'S-1-5-18'

_FILE_READ_ATTRIBUTES = 0x80
_FILE_LIST_DIRECTORY = 0x01
_FILE_TRAVERSE = 0x20
_READ_CONTROL = 0x00020000
_DELETE = 0x00010000
_GENERIC_WRITE = 0x40000000
_FILE_SHARE_READ = 0x01
_FILE_SHARE_WRITE = 0x02
_CREATE_NEW = 1
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_DIRECTORY = 0x10
_FILE_ATTRIBUTE_NORMAL = 0x80
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_ALL_ACCESS = 0x001F01FF
_SE_DACL_PROTECTED = 0x1000


class _SecurityAttributes(ct.Structure):
    _fields_ = [('length', wt.DWORD), ('descriptor', ct.c_void_p), ('inherit_handle', wt.BOOL)]


class _AttributeTagInfo(ct.Structure):
    _fields_ = [('attributes', wt.DWORD), ('reparse_tag', wt.DWORD)]


class _AclSizeInformation(ct.Structure):
    _fields_ = [('count', wt.DWORD), ('used', wt.DWORD), ('free', wt.DWORD)]


class _AceHeader(ct.Structure):
    _fields_ = [('kind', ct.c_ubyte), ('flags', ct.c_ubyte), ('size', wt.WORD), ('mask', wt.DWORD)]


def _location(jobs_root, job_name):
    raw = os.fspath(jobs_root)
    if not isinstance(raw, str):
        raise ValueError('canonical local Windows jobs root required')
    root = PureWindowsPath(raw)
    if (not re.fullmatch(r'[A-Za-z]:', root.drive) or not root.is_absolute()
            or len(root.parts) < 2 or raw != str(root)
            or any(part in ('.', '..') or part[-1] in ' .' or PureWindowsPath(part).is_reserved()
                   or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in part) for part in root.parts[1:])):
        raise ValueError('canonical local Windows jobs root required')
    if (not isinstance(job_name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', job_name)
            or PureWindowsPath(job_name).is_reserved()):
        raise ValueError('safe single-component job name required')
    if len(str(root / job_name / RECEIPT_NAME).encode('utf-16-le')) >= 2 * 260:
        raise ValueError('Windows job path exceeds supported length')
    return root, job_name


def _bind(library, name, result, *arguments):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = arguments
    return function


def _fail(label, code=None):
    error = ct.get_last_error() if code is None else code
    kind = FileExistsError if error in (80, 183) else PermissionError if error == 5 else OSError
    raise kind(None, label, None, error)


class _Windows:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('native Windows private receipt support is required')
        kernel = ct.WinDLL('kernel32', use_last_error=True)
        security = ct.WinDLL('advapi32', use_last_error=True)
        pointer = ct.c_void_p
        pointer_ref = ct.POINTER(pointer)
        dword_ref = ct.POINTER(wt.DWORD)
        self.close = _bind(kernel, 'CloseHandle', wt.BOOL, wt.HANDLE)
        self.free = _bind(kernel, 'LocalFree', pointer, pointer)
        self.current_process = _bind(kernel, 'GetCurrentProcess', wt.HANDLE)
        self.open_file = _bind(kernel, 'CreateFileW', wt.HANDLE, wt.LPCWSTR, wt.DWORD, wt.DWORD,
                               ct.POINTER(_SecurityAttributes), wt.DWORD, wt.DWORD, wt.HANDLE)
        self.create_dir = _bind(kernel, 'CreateDirectoryW', wt.BOOL, wt.LPCWSTR, ct.POINTER(_SecurityAttributes))
        self.get_attribute_tag = _bind(kernel, 'GetFileInformationByHandleEx', wt.BOOL, wt.HANDLE,
                                       ct.c_int, pointer, wt.DWORD)
        self.final_path = _bind(kernel, 'GetFinalPathNameByHandleW', wt.DWORD,
                                wt.HANDLE, wt.LPWSTR, wt.DWORD, wt.DWORD)
        self.drive_type = _bind(kernel, 'GetDriveTypeW', wt.UINT, wt.LPCWSTR)
        self.volume_info = _bind(kernel, 'GetVolumeInformationByHandleW', wt.BOOL, wt.HANDLE,
                                 wt.LPWSTR, wt.DWORD, dword_ref, dword_ref, dword_ref, wt.LPWSTR, wt.DWORD)
        self.write = _bind(kernel, 'WriteFile', wt.BOOL, wt.HANDLE, pointer, wt.DWORD, dword_ref, pointer)
        self.flush = _bind(kernel, 'FlushFileBuffers', wt.BOOL, wt.HANDLE)
        self.set_file_info = _bind(kernel, 'SetFileInformationByHandle', wt.BOOL, wt.HANDLE,
                                   ct.c_int, pointer, wt.DWORD)
        self.open_token = _bind(security, 'OpenProcessToken', wt.BOOL, wt.HANDLE, wt.DWORD, pointer_ref)
        self.token_info = _bind(security, 'GetTokenInformation', wt.BOOL, wt.HANDLE,
                                ct.c_int, pointer, wt.DWORD, dword_ref)
        self.sid_to_string = _bind(security, 'ConvertSidToStringSidW', wt.BOOL, pointer, pointer_ref)
        self.security_descriptor = _bind(security, 'ConvertStringSecurityDescriptorToSecurityDescriptorW',
                                         wt.BOOL, wt.LPCWSTR, wt.DWORD, pointer_ref, dword_ref)
        self.security_info = _bind(security, 'GetSecurityInfo', wt.DWORD, wt.HANDLE, ct.c_int,
                                   wt.DWORD, pointer_ref, pointer_ref, pointer_ref, pointer_ref, pointer_ref)
        self.descriptor_control = _bind(security, 'GetSecurityDescriptorControl', wt.BOOL, pointer,
                                        ct.POINTER(wt.WORD), dword_ref)
        self.acl_info = _bind(security, 'GetAclInformation', wt.BOOL, pointer, pointer, wt.DWORD, ct.c_int)
        self.get_ace = _bind(security, 'GetAce', wt.BOOL, pointer, wt.DWORD, pointer_ref)
        self.owner_sid = self._process_sid()
        self.trusted_sids = {self.owner_sid, _SYSTEM_SID}

    def _sid_string(self, sid):
        string = ct.c_void_p()
        if not self.sid_to_string(sid, ct.byref(string)):
            _fail('could not verify Windows security principal')
        try:
            return ct.wstring_at(string)
        finally:
            self.free(string)

    def _process_sid(self):
        token = wt.HANDLE()
        if not self.open_token(self.current_process(), 0x0008, ct.byref(token)):  # TOKEN_QUERY
            _fail('could not open Windows process token')
        try:
            size = wt.DWORD()
            self.token_info(token, 1, None, 0, ct.byref(size))  # TokenUser
            if not 0 < size.value <= 4096:
                raise OSError('unexpected Windows process token size')
            data = ct.create_string_buffer(size.value)
            if not self.token_info(token, 1, data, size, ct.byref(size)):
                _fail('could not verify Windows process token')
            return self._sid_string(ct.c_void_p.from_buffer(data))
        finally:
            self.close(token)

    @contextmanager
    def private_attributes(self, *, directory):
        flags = 'OICI' if directory else ''
        entries = ''.join(f'(A;{flags};FA;;;{sid})' for sid in sorted(self.trusted_sids))
        descriptor = ct.c_void_p()
        if not self.security_descriptor(f'O:{self.owner_sid}D:P{entries}', 1, ct.byref(descriptor), None):
            _fail('could not build protected Windows ACL')
        try:
            yield _SecurityAttributes(ct.sizeof(_SecurityAttributes), descriptor, False)
        finally:
            self.free(descriptor)

    def verify_private(self, handle):
        owner, dacl, descriptor = ct.c_void_p(), ct.c_void_p(), ct.c_void_p()
        error = self.security_info(handle, 1, 5, ct.byref(owner), None, ct.byref(dacl), None,
                                   ct.byref(descriptor))  # SE_FILE_OBJECT, OWNER | DACL
        if error:
            _fail('could not read Windows object ACL', error)
        try:
            control, revision = wt.WORD(), wt.DWORD()
            if not self.descriptor_control(descriptor, ct.byref(control), ct.byref(revision)):
                _fail('could not verify Windows ACL protection')
            if (not owner or not dacl or not control.value & _SE_DACL_PROTECTED
                    or self._sid_string(owner) != self.owner_sid):
                raise PermissionError('owning account and protected Windows ACL required')
            info = _AclSizeInformation()
            if not self.acl_info(dacl, ct.byref(info), ct.sizeof(info), 2):  # AclSizeInformation
                _fail('could not inspect Windows ACL entries')
            if info.count != len(self.trusted_sids):
                raise PermissionError('private Windows ACL requires only the owning account and SYSTEM')
            seen = set()
            for i in range(info.count):
                ace = ct.c_void_p()
                if not self.get_ace(dacl, i, ct.byref(ace)):
                    _fail('could not inspect Windows ACL entry')
                header = _AceHeader.from_address(ace.value)
                # Ordinary explicit full-access allow entries only. OI/CI are
                # permitted on directories; inherited/inherit-only are denied.
                if header.kind != 0 or header.flags & ~0x03 or header.mask != _FILE_ALL_ACCESS:
                    raise PermissionError('unexpected Windows private ACL entry')
                seen.add(self._sid_string(ace.value + ct.sizeof(_AceHeader)))
            if seen != self.trusted_sids:
                raise PermissionError('private Windows ACL requires only the owning account and SYSTEM')
        finally:
            self.free(descriptor)

    def verify_type(self, handle, *, directory):
        info = _AttributeTagInfo()
        if not self.get_attribute_tag(handle, 9, ct.byref(info), ct.sizeof(info)):  # FileAttributeTagInfo
            _fail('could not inspect Windows handle attributes')
        if (info.attributes & _FILE_ATTRIBUTE_REPARSE_POINT
                or bool(info.attributes & _FILE_ATTRIBUTE_DIRECTORY) != directory):
            raise PermissionError('unexpected Windows object type or reparse point')

    def verify_location(self, handle, path):
        final = ct.create_unicode_buffer(512)
        length = self.final_path(handle, final, len(final), 0)  # normalized path, DOS volume name
        if not length:
            _fail('could not verify Windows handle path')
        expected = '\\\\?\\' + str(path)
        actual = final.value
        if (length >= len(final) or actual[:6].upper() != expected[:6].upper()
                or actual[6:] != expected[6:]):
            raise PermissionError('noncanonical Windows handle path')

    def verify_volume(self, root, handle):
        if self.drive_type(root.anchor) != 3:  # DRIVE_FIXED
            raise PermissionError('local fixed Windows volume required')
        flags = wt.DWORD()
        filesystem = ct.create_unicode_buffer(32)
        if not self.volume_info(handle, None, 0, None, None, ct.byref(flags), filesystem, len(filesystem)):
            _fail('could not verify Windows filesystem')
        if filesystem.value != 'NTFS' or not flags.value & 0x08:  # FILE_PERSISTENT_ACLS
            raise PermissionError('local NTFS with persistent ACLs required')

    def pin_directory(self, stack, path, *, private=False, receiving=False):
        # FILE_TRAVERSE makes the handle participate in read sharing. An
        # attributes-only open does not establish the write/delete share lock.
        access = _FILE_READ_ATTRIBUTES | _FILE_TRAVERSE
        if private:
            access |= _READ_CONTROL | _FILE_LIST_DIRECTORY
        share = _FILE_SHARE_READ
        if receiving:
            # The private child must admit the rename's destination write.
            # No directory permits delete sharing while it is pinned.
            share |= _FILE_SHARE_WRITE
        handle = self.open_file(str(path), access, share, None, _OPEN_EXISTING,
                                _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT, None)
        if handle == _INVALID_HANDLE:
            _fail('could not pin Windows directory')
        stack.callback(self.close, handle)
        self.verify_type(handle, directory=True)
        self.verify_location(handle, path)
        if private:
            self.verify_private(handle)
        return handle

    def create_private_directory(self, path):
        with self.private_attributes(directory=True) as attributes:
            if not self.create_dir(str(path), ct.byref(attributes)):
                _fail('could not create fresh private Windows job directory')

    def commit_receipt(self, directory, raw):
        pending = directory / _TEMP_NAME
        access = _GENERIC_WRITE | _DELETE | _READ_CONTROL | _FILE_READ_ATTRIBUTES
        with self.private_attributes(directory=False) as attributes:
            handle = self.open_file(str(pending), access, 0, ct.byref(attributes), _CREATE_NEW,
                                    _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT, None)
            if handle == _INVALID_HANDLE:
                _fail('could not create exclusive Windows receipt staging file')
        staged = False
        try:
            self.verify_type(handle, directory=False)
            self.verify_location(handle, pending)
            self.verify_private(handle)
            written = wt.DWORD()
            if not self.write(handle, ct.c_char_p(raw), len(raw), ct.byref(written), None):
                _fail('could not write Windows receipt')
            if written.value != len(raw):
                raise OSError('incomplete Windows receipt write')
            if not self.flush(handle):
                _fail('could not flush Windows receipt')
            staged = True
        finally:
            if not staged:
                delete_on_close = ct.c_ubyte(1)
                self.set_file_info(handle, 4, ct.byref(delete_on_close), ct.sizeof(delete_on_close))
            self.close(handle)
        try:
            # Windows os.rename is same-volume and fails if the destination
            # exists. Only the owning account and SYSTEM can access either
            # name inside the private, still-pinned child.
            os.rename(pending, directory / RECEIPT_NAME)
        except OSError:
            pending.unlink(missing_ok=True)
            raise


class _ReceiptJob:
    def __init__(self, native, path, handle):
        self._native = native
        self._path = path
        self._handle = handle
        self._published = False

    def write_receipt(self, raw):
        if self._handle is None:
            raise RuntimeError('Windows receipt job is closed')
        if self._published:
            raise FileExistsError('Windows receipt already published')
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RECEIPT_BYTES:
            raise ValueError('bounded nonempty receipt bytes required')
        self._native.commit_receipt(self._path, raw)
        self._published = True


@contextmanager
def private_receipt_job(jobs_root, job_name):
    """Pin an owner-provisioned root and exclusively create a private child."""
    root, name = _location(jobs_root, job_name)
    native = _Windows()
    with ExitStack() as stack:
        # Walk from the drive down so each next open traverses already pinned
        # directories. The private child alone permits destination write sharing.
        for parent in reversed(root.parents):
            native.pin_directory(stack, parent)
        root_handle = native.pin_directory(stack, root, private=True)
        native.verify_volume(root, root_handle)
        path = root / name
        native.create_private_directory(path)
        child = native.pin_directory(stack, path, private=True, receiving=True)
        job = _ReceiptJob(native, path, child)
        try:
            yield job
        finally:
            job._handle = None
