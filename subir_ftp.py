#!/usr/bin/env python3
"""Sube los datos generados del Mundial 2026 al FTP de la empresa.

Las credenciales NO se escriben aqui: se leen de variables de entorno para no
dejarlas en el repositorio ni en el codigo.

Variables de entorno:
  FTP_HOST   host del FTP (obligatorio)
  FTP_USER   usuario (obligatorio)
  FTP_PASS   contrasena (obligatorio)
  FTP_DIR    carpeta destino en el FTP (opcional, por defecto la raiz "/")
  FTP_PORT   puerto (opcional, por defecto 21)
  FTP_TLS    "1" para usar FTPS (FTP sobre TLS) si el servidor lo soporta;
             "0" para FTP plano. Por defecto "1".

Uso:
  python subir_ftp.py
  python subir_ftp.py --files data/mundial_2026_clubes.js data/mundial_2026_clubes.json
"""
import argparse
import ftplib
import os
import sys
from pathlib import Path

DEFAULT_FILES = [
    "data/mundial_2026_clubes.js",
    "data/mundial_2026_clubes.json",
]


def connect():
    host = os.environ.get("FTP_HOST")
    user = os.environ.get("FTP_USER")
    password = os.environ.get("FTP_PASS")
    if not host or not user or password is None:
        sys.exit("Faltan credenciales FTP. Define FTP_HOST, FTP_USER y FTP_PASS.")

    port = int(os.environ.get("FTP_PORT", "21"))
    use_tls = os.environ.get("FTP_TLS", "1") != "0"

    if use_tls:
        ftp = ftplib.FTP_TLS()
        ftp.connect(host, port, timeout=60)
        ftp.login(user, password)
        ftp.prot_p()  # cifra tambien el canal de datos
    else:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=60)
        ftp.login(user, password)
    return ftp


def ensure_dir(ftp, remote_dir):
    if not remote_dir or remote_dir == "/":
        return
    for part in remote_dir.strip("/").split("/"):
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def main():
    parser = argparse.ArgumentParser(description="Sube los datos del Mundial 2026 al FTP.")
    parser.add_argument("--files", nargs="*", default=DEFAULT_FILES, help="Ficheros locales a subir.")
    args = parser.parse_args()

    missing = [f for f in args.files if not Path(f).exists()]
    if missing:
        sys.exit("No existen estos ficheros (ejecuta antes actualizar_mundial_2026.py): " + ", ".join(missing))

    ftp = connect()
    try:
        ensure_dir(ftp, os.environ.get("FTP_DIR", "/"))
        for local in args.files:
            name = Path(local).name
            with open(local, "rb") as handle:
                ftp.storbinary(f"STOR {name}", handle)
            print(f"OK: subido {local} -> {name}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    main()
