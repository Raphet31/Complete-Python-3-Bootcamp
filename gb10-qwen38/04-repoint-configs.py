#!/usr/bin/env python3
"""Migra las referencias al modelo viejo para que apunten al alias estable.

El 00-inventory.sh te DICE que archivos nombran el modelo viejo. Este los
REESCRIBE, una sola vez, para que nombren el alias. A partir de ahi cambiar de
modelo ya no vuelve a tocar ningun config: solo se repunta el alias con
02-switch-model.sh.

    OLD_MODEL="llama3.1:70b"   ->   ALIAS="work-default"

Por defecto es SIMULACRO: enseña el diff y no escribe nada. Hay que pasar
--apply explicitamente. Cada archivo modificado se respalda antes, y --restore
lo deja todo como estaba.

Uso:
    ./04-repoint-configs.py --path ~/proyectos          # simulacro, ve el diff
    ./04-repoint-configs.py --path ~/proyectos --apply  # escribe (con backup)
    ./04-repoint-configs.py --restore                   # deshace el ultimo apply
    ./04-repoint-configs.py --list-backups
"""

import argparse
import difflib
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "models.conf")
BACKUP_ROOT = os.path.join(HERE, ".config-backups")

# Nunca entrar aqui: control de versiones, dependencias, y el almacen de pesos
# de ollama (los blobs son binarios enormes y contienen el nombre del modelo).
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".cache", ".mypy_cache", ".pytest_cache", "blobs", "manifests",
    ".ollama", "site-packages", "dist", "build", ".terraform",
    # Worktrees de git: son ramas de trabajo vivas. Reescribir dentro deja 8
    # ramas con diffs espurios que nadie pidio. La rama activa se migra sola.
    "worktrees",
}

# Extensiones que jamas son config de texto.
SKIP_EXT = {
    ".gguf", ".bin", ".safetensors", ".pt", ".pth", ".onnx", ".so", ".dylib",
    ".dll", ".zip", ".tar", ".gz", ".bz2", ".xz", ".jpg", ".jpeg", ".png",
    ".gif", ".pdf", ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".wav",
}

MAX_BYTES = 2 * 1024 * 1024  # un config de >2MB no es un config

# Las cinco fuentes del drift validator de BF-OS v6 (regla R8). El validador
# las cruza al boot; si el nombre del modelo cambia en unas y no en otras, el
# boot sale ROJO. Reescribirlas automaticamente es justo la forma de romperlo,
# asi que quedan excluidas salvo que se pase --allow-drift-sources.
DRIFT_FILES = {"registry.yaml", "swarm_gpu_models.yaml", "MODEL_INVENTORY.md"}
DRIFT_DIRS = {"agents"}
DRIFT_MARKERS = ("CURATED_LOCAL", "AGENTS = {", "AGENTS={")


sys.path.insert(0, HERE)
from _conf import read_conf as _read_conf


def read_conf():
    return _read_conf(CONF)


def is_texty(path):
    """Heuristica barata: si el primer bloque tiene un NUL, es binario."""
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return False
    return b"\x00" not in chunk


def is_drift_source(path, text):
    """¿Es una de las cinco fuentes que el drift validator cruza al boot?"""
    name = os.path.basename(path)
    if name in DRIFT_FILES:
        return name
    parts = path.split(os.sep)
    if any(d in DRIFT_DIRS for d in parts[:-1]) and name.endswith((".yaml", ".yml")):
        return f"agents/{name}"
    for marker in DRIFT_MARKERS:
        if marker in text:
            return f"contiene {marker!r}"
    return None


def candidate_files(roots, needle, allow_drift=False):
    """Archivos de texto, razonables en tamaño, que contienen el modelo viejo."""
    seen = set()
    skipped_drift = []
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.exists(root):
            print(f"  aviso: {root} no existe, lo salto")
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # No tocar el propio toolkit: sus scripts mencionan el modelo a proposito.
            if os.path.abspath(dirpath).startswith(HERE):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                           and not d.startswith(".ollama")]
            for name in filenames:
                path = os.path.join(dirpath, name)
                if path in seen:
                    continue
                if os.path.splitext(name)[1].lower() in SKIP_EXT:
                    continue
                if os.path.islink(path):
                    continue
                try:
                    if os.path.getsize(path) > MAX_BYTES:
                        continue
                except OSError:
                    continue
                if not is_texty(path):
                    continue
                try:
                    with open(path, encoding="utf-8", errors="strict") as fh:
                        text = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                if needle not in text:
                    continue
                reason = is_drift_source(path, text)
                if reason and not allow_drift:
                    skipped_drift.append((path, reason))
                    continue
                seen.add(path)
                yield path, text
    if skipped_drift:
        print("\n  PROTEGIDOS (fuentes del drift validator, regla R8 de BF-OS):")
        for path, reason in skipped_drift:
            print(f"    - {path}  [{reason}]")
        print("  Estas NO se reescriben: cambiarlas parcialmente deja el boot ROJO.")
        print("  Actualizalas a mano, coherentemente en las cinco, o pasa")
        print("  --allow-drift-sources si sabes lo que haces.\n")


def show_diff(path, before, after):
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="antes",
        tofile="despues",
        n=1,
    )
    for line in diff:
        sys.stdout.write(line if line.endswith("\n") else line + "\n")


def do_restore(stamp=None):
    if not os.path.isdir(BACKUP_ROOT):
        sys.exit("No hay backups: nunca se corrio con --apply.")
    stamps = sorted(os.listdir(BACKUP_ROOT))
    if not stamps:
        sys.exit("No hay backups.")
    stamp = stamp or stamps[-1]
    manifest_path = os.path.join(BACKUP_ROOT, stamp, "manifest.json")
    if not os.path.exists(manifest_path):
        sys.exit(f"Backup {stamp} sin manifest; no puedo restaurar con seguridad.")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    print(f"Restaurando backup {stamp} ({len(manifest['files'])} archivos)...")
    restored, failed = 0, 0
    for entry in manifest["files"]:
        src = os.path.join(BACKUP_ROOT, stamp, entry["backup"])
        dst = entry["original"]
        if not os.path.exists(src):
            print(f"  FALTA el backup de {dst}")
            failed += 1
            continue
        try:
            shutil.copy2(src, dst)
            print(f"  restaurado  {dst}")
            restored += 1
        except OSError as exc:
            print(f"  FALLO {dst}: {exc}")
            failed += 1
    print(f"\n{restored} restaurados, {failed} fallidos.")
    return 1 if failed else 0


def main():
    conf = read_conf()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--path", action="append", default=[],
                    help="directorio a migrar (repetible). Por defecto: $HOME")
    ap.add_argument("--old", default=conf.get("OLD_MODEL", ""),
                    help="cadena a reemplazar (por defecto OLD_MODEL)")
    ap.add_argument("--alias", default=conf.get("ALIAS", "work-default"),
                    help="alias destino (por defecto ALIAS)")
    ap.add_argument("--apply", action="store_true",
                    help="escribir de verdad (por defecto solo simulacro)")
    ap.add_argument("--restore", nargs="?", const=True, default=False,
                    metavar="STAMP", help="deshacer; opcionalmente un backup concreto")
    ap.add_argument("--list-backups", action="store_true")
    ap.add_argument("--allow-drift-sources", action="store_true",
                    help="permitir reescribir registry.yaml / agents/*.yaml / "
                         "swarm_gpu_models.yaml / el picker. Rompe el drift "
                         "validator si no las actualizas TODAS a la vez.")
    args = ap.parse_args()

    if args.list_backups:
        if not os.path.isdir(BACKUP_ROOT):
            print("Sin backups.")
            return 0
        for stamp in sorted(os.listdir(BACKUP_ROOT)):
            mp = os.path.join(BACKUP_ROOT, stamp, "manifest.json")
            n = "?"
            if os.path.exists(mp):
                with open(mp, encoding="utf-8") as fh:
                    n = len(json.load(fh)["files"])
            print(f"  {stamp}   {n} archivo(s)")
        return 0

    if args.restore:
        return do_restore(None if args.restore is True else args.restore)

    if not args.old:
        sys.exit(
            "ERROR: OLD_MODEL esta vacio en models.conf y no pasaste --old.\n"
            "Corre ./00-inventory.sh para descubrir que modelo usas hoy."
        )
    if args.old == args.alias:
        sys.exit("ERROR: --old y --alias son iguales; no hay nada que migrar.")

    roots = args.path or [os.path.expanduser("~")]

    print(f"Reemplazar:  {args.old}")
    print(f"Por:         {args.alias}")
    print(f"Buscando en: {', '.join(roots)}")
    print(f"Modo:        {'APLICAR (escribe)' if args.apply else 'SIMULACRO (no escribe)'}")
    print("-" * 61)

    hits = list(candidate_files(roots, args.old, args.allow_drift_sources))
    if not hits:
        print("\nNingun archivo menciona el modelo viejo. Nada que hacer.")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    backup_dir = os.path.join(BACKUP_ROOT, stamp)
    manifest = {"created": stamp, "old": args.old, "alias": args.alias, "files": []}

    changed = 0
    for i, (path, before) in enumerate(hits):
        after = before.replace(args.old, args.alias)
        if after == before:
            continue
        n = before.count(args.old)
        print(f"\n{path}  ({n} ocurrencia{'s' if n != 1 else ''})")
        show_diff(path, before, after)

        if not args.apply:
            changed += 1
            continue

        os.makedirs(backup_dir, exist_ok=True)
        rel = f"{i:04d}-{os.path.basename(path)}"
        try:
            shutil.copy2(path, os.path.join(backup_dir, rel))
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(after)
        except OSError as exc:
            print(f"  FALLO al escribir: {exc}")
            continue
        manifest["files"].append({"original": path, "backup": rel})
        changed += 1

    print("\n" + "=" * 61)
    if args.apply and manifest["files"]:
        with open(os.path.join(backup_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        print(f"{changed} archivo(s) migrados. Backup: {backup_dir}")
        print("\nDeshacer:  ./04-repoint-configs.py --restore")
        print("\nOJO: reinicia los servicios que lean estos configs para que")
        print("     tomen el cambio (systemctl restart, recargar la app, etc).")
    elif args.apply:
        print("No se pudo escribir ningun archivo.")
    else:
        print(f"SIMULACRO: {changed} archivo(s) cambiarian. No se escribio nada.")
        print("\nSi el diff se ve bien, re-corre con --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
