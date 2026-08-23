#!/usr/bin/env python3
"""Verifica que la migracion no viole las reglas de BF-OS v6 antes de tocar nada.

Este toolkit se escribio sin conocer BF-OS. Al leer el PLAN COLIBRI v1.1
aparecieron tres reglas marcadas SAGRADO que la migracion, tal como estaba,
habría roto. Esta puerta las comprueba y aborta si alguna falla.

  R7  Ningun modelo se baja sin entrada previa en MODEL_INVENTORY.md con rol
      asignado. Regla permanente de MODEL-AUDIT-1: "se acabo bajar por probar".

  R8  El drift validator cruza CINCO fuentes al boot (AGENTS dict, agents/*.yaml,
      registry.yaml, picker CURATED_LOCAL, swarm_gpu_models.yaml). Reescribir el
      nombre del modelo en unas y no en otras deja el boot en ROJO.

  R4  Memoria unificada compartida (121 GB) con OLLAMA_MAX_LOADED_MODELS=1.
      Ya hubo un crash por 53 GB de pesos pineados. Cargar dos modelos a la vez
      para un A/B es exactamente ese riesgo.

Uso:
    ./07-bfos-gate.py --bfos ~/BELLA_FLOR_OS
    ./07-bfos-gate.py --bfos ~/BELLA_FLOR_OS --model qwen3.8:27b-nvfp4

Salida: 0 puede continuar   1 hay violaciones   2 no pude verificar
"""

import argparse
import json
import os
import re
import subprocess
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _conf import read_conf

# Las cinco fuentes del drift validator (R8). 04-repoint-configs.py NO debe
# tocarlas: cambiar el nombre del modelo en unas y no en otras deja boot ROJO.
DRIFT_SOURCES = [
    "registry.yaml",
    "swarm_gpu_models.yaml",
    "agents",                 # agents/*.yaml
    "CURATED_LOCAL",          # el picker
    "AGENTS",                 # el dict en codigo
]


def find(root, names):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "node_modules", ".venv", "__pycache__"}]
        for fn in filenames:
            if fn in names:
                hits.append(os.path.join(dirpath, fn))
    return hits


def main():
    conf = read_conf(os.path.join(HERE, "models.conf"))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bfos", default=os.path.expanduser("~/BELLA_FLOR_OS"),
                    help="raiz del repo BELLA_FLOR_OS")
    ap.add_argument("--model", default=conf.get("NEW_MODEL", ""),
                    help="modelo que se quiere introducir")
    ap.add_argument("--old", default=conf.get("OLD_MODEL", ""))
    args = ap.parse_args()

    problems, warnings, unknown = [], [], []
    print("=" * 66)
    print("PUERTA BF-OS v6  —  R7 / R8 / R4")
    print("=" * 66)

    if not os.path.isdir(args.bfos):
        print(f"\n  No encuentro {args.bfos}")
        print("  Sin el repo no puedo verificar nada. Corre esto EN la GB10,")
        print("  o pasa la ruta con --bfos.")
        return 2

    # ---------------------------------------------------------------- R7
    print("\n[R7]  Entrada en MODEL_INVENTORY.md antes de descargar")
    inv = find(args.bfos, {"MODEL_INVENTORY.md"})
    if not inv:
        problems.append("No existe MODEL_INVENTORY.md — R7 no se puede cumplir.")
        print("      MODEL_INVENTORY.md NO encontrado.")
    else:
        path = inv[0]
        print(f"      {path}")
        text = open(path, encoding="utf-8", errors="replace").read()
        base = args.model.split(":")[0]
        if args.model in text or (base and base in text):
            print(f"      OK — '{args.model}' ya aparece.")
        else:
            problems.append(
                f"'{args.model}' NO tiene entrada en MODEL_INVENTORY.md. "
                "R7 es SAGRADO: la entrada con rol asignado va ANTES de bajar."
            )
            print(f"      FALTA la entrada de '{args.model}'.")

        # de paso: el modelo viejo, ¿existe de verdad?
        if args.old:
            if args.old in text or args.old.split(":")[0] in text:
                print(f"      OK — el modelo viejo '{args.old}' figura en el inventario.")
            else:
                unknown.append(
                    f"'{args.old}' no aparece en MODEL_INVENTORY.md. "
                    "Verifica que sea de verdad el modelo que estas reemplazando."
                )
                print(f"      AVISO — '{args.old}' no figura en el inventario.")

    # ---------------------------------------------------------------- R8
    print("\n[R8]  Fuentes del drift validator (deben quedar coherentes)")
    found = find(args.bfos, {"registry.yaml", "swarm_gpu_models.yaml"})
    agents_dirs = [os.path.join(dp, "agents")
                   for dp, dn, _ in os.walk(args.bfos) if "agents" in dn]
    for f in found:
        print(f"      {f}")
    for d in agents_dirs[:3]:
        print(f"      {d}/*.yaml")
    if not found and not agents_dirs:
        unknown.append("No localice las fuentes del drift validator.")
        print("      no localizadas — verifica a mano antes de reescribir configs.")
    else:
        warnings.append(
            "04-repoint-configs.py NO debe reescribir estas fuentes: cambiar el "
            "nombre del modelo en unas y no en otras deja el boot en ROJO. "
            "La proteccion ya esta activa por defecto; solo se desactiva "
            "pasando --allow-drift-sources a mano."
        )
        print("      Estas rutas quedan EXCLUIDAS de la reescritura automatica.")

    # ---------------------------------------------------------------- R4
    print("\n[R4]  Arbitraje de memoria unificada")
    if shutil.which("ollama"):
        try:
            out = subprocess.run(["ollama", "ps"], capture_output=True,
                                 text=True, timeout=15).stdout
            loaded = [l.split()[0] for l in out.splitlines()[1:] if l.strip()]
        except (subprocess.SubprocessError, OSError):
            loaded = []
        if loaded:
            print(f"      cargados ahora: {', '.join(loaded)}")
            problems.append(
                f"Hay {len(loaded)} modelo(s) cargado(s). El A/B carga dos mas. "
                "R4 exige lock exclusivo: drena Ollama antes de medir. "
                "Precedente: crash por 53 GB pineados."
            )
        else:
            print("      nada cargado. OK para medir.")
    else:
        unknown.append("ollama no esta en PATH; no pude comprobar R4.")
        print("      ollama no disponible — no verificado.")

    mx = os.environ.get("OLLAMA_MAX_LOADED_MODELS")
    if mx == "1":
        print("      OLLAMA_MAX_LOADED_MODELS=1 — el A/B NO puede co-cargar.")
        warnings.append(
            "Con OLLAMA_MAX_LOADED_MODELS=1 el A/B alterna modelos y cada cambio "
            "paga una recarga completa. Los tiempos incluiran ese coste."
        )

    # ------------------------------------------------------------ veredicto
    print("\n" + "=" * 66)
    if problems:
        print(f"BLOQUEADO — {len(problems)} violacion(es)\n")
        for p in problems:
            print(f"  x  {p}\n")
    if warnings:
        print("Avisos:\n")
        for w in warnings:
            print(f"  !  {w}\n")
    if unknown:
        print("No verificado:\n")
        for u in unknown:
            print(f"  ?  {u}\n")
    if not problems:
        print("Sin violaciones detectadas. Puedes continuar.")
    print("=" * 66)
    return 1 if problems else (2 if unknown and not problems else 0)


if __name__ == "__main__":
    sys.exit(main())
