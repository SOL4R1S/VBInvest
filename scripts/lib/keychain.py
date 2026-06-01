from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass, field
from typing import Mapping, Protocol


KEYCHAIN_SERVICE = "VBinvest"


class SecretStore(Protocol):
    def get(self, account: str) -> str:
        ...


class SecretWriteStore(SecretStore, Protocol):
    def set(self, account: str, value: str) -> None:
        ...


class CommandRunner(Protocol):
    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        ...


class WindowsCredentialBackend(Protocol):
    def read(self, target_name: str) -> str:
        ...

    def write(self, target_name: str, value: str) -> None:
        ...


def _run_security(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


@dataclass(frozen=True, slots=True)
class KeychainSecretStore:
    service: str = KEYCHAIN_SERVICE
    runner: CommandRunner = field(default=_run_security, repr=False)

    def get(self, account: str) -> str:
        command = ["security", "find-generic-password", "-a", account, "-s", self.service, "-w"]
        try:
            result = self.runner(command)
        except FileNotFoundError:
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def set(self, account: str, value: str) -> None:
        command = ["security", "add-generic-password", "-U", "-a", account, "-s", self.service, "-w", value]
        result = self.runner(command)
        if result.returncode != 0:
            raise RuntimeError(f"failed to save {account} to macOS Keychain")


@dataclass(frozen=True, slots=True)
class WindowsCredentialStore:
    service: str = KEYCHAIN_SERVICE
    backend: WindowsCredentialBackend = field(default_factory=lambda: WindowsCredentialApi(), repr=False)

    def get(self, account: str) -> str:
        return self.backend.read(self._target_name(account))

    def set(self, account: str, value: str) -> None:
        self.backend.write(self._target_name(account), value)

    def _target_name(self, account: str) -> str:
        return f"{self.service}:{account}"


class WindowsCredentialApi:
    def read(self, target_name: str) -> str:
        import ctypes
        from ctypes import wintypes

        credential_pointer = ctypes.POINTER(_windows_credential_struct())()
        ok = ctypes.windll.advapi32.CredReadW(target_name, 1, 0, ctypes.byref(credential_pointer))
        if not ok:
            return ""
        try:
            credential = credential_pointer.contents
            blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return blob.decode("utf-16-le")
        finally:
            ctypes.windll.advapi32.CredFree(wintypes.LPVOID(credential_pointer))

    def write(self, target_name: str, value: str) -> None:
        import ctypes

        credential_type = _windows_credential_struct()
        blob_bytes = value.encode("utf-16-le")
        blob = ctypes.create_string_buffer(blob_bytes)
        credential = credential_type()
        credential.Type = 1
        credential.TargetName = target_name
        credential.CredentialBlobSize = len(blob_bytes)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = 2
        credential.UserName = KEYCHAIN_SERVICE
        ok = ctypes.windll.advapi32.CredWriteW(ctypes.byref(credential), 0)
        if not ok:
            raise RuntimeError(f"failed to save {target_name} to Windows Credential Manager")


def _windows_credential_struct():
    import ctypes
    from ctypes import wintypes

    class Credential(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", wintypes.LPVOID),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    return Credential


@dataclass(frozen=True, slots=True)
class EmptySecretStore:
    def get(self, account: str) -> str:
        return ""

    def set(self, account: str, value: str) -> None:
        raise RuntimeError("secure secret storage is not available on this platform")


def platform_secret_store(system_name: str | None = None) -> SecretWriteStore:
    system = system_name or platform.system()
    match system:
        case "Darwin":
            return KeychainSecretStore()
        case "Windows":
            return WindowsCredentialStore()
        case _:
            return EmptySecretStore()


def resolve_secret(
    environ: Mapping[str, str],
    keychain_account: str,
    *,
    aliases: tuple[str, ...] = (),
    system_name: str | None = None,
    store: SecretStore | None = None,
) -> str:
    system = system_name or platform.system()
    secret_store = store or platform_secret_store(system)
    if system in {"Darwin", "Windows"}:
        keychain_value = secret_store.get(keychain_account)
        if keychain_value:
            return keychain_value
    for name in (keychain_account, *aliases):
        value = environ.get(name, "").strip()
        if value:
            return value
    return ""
