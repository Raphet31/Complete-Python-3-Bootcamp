"""Lectura compartida de models.conf para los scripts de Python.

models.conf lo consumen dos mundos: los .sh lo hacen `source` (y el shell
expande las variables) y los .py lo parsean. Si el parseo no expande, un valor
tan normal como

    OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

llega a Python como la cadena literal '${OLLAMA_HOST:-http://localhost:11434}'
y todas las peticiones fallan. Este modulo existe para que las dos lecturas
coincidan, y para que la logica viva en un solo sitio.
"""

import os
import re

_ASSIGN = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?([^"#\n]*)"?')
_VAR = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}|\$([A-Za-z_][A-Za-z0-9_]*)')


def expand(value, extra=None):
    """Expande ${VAR}, ${VAR:-default} y $VAR como haria el shell."""
    env = dict(os.environ)
    if extra:
        env.update({k: v for k, v in extra.items() if v})

    def sub(m):
        if m.group(4):                      # forma $VAR
            return env.get(m.group(4), "")
        name, default = m.group(1), m.group(3)
        val = env.get(name)
        if val:
            return val
        return default if default is not None else ""

    # varias pasadas por si un valor referencia a otro; tope para no colgarse
    for _ in range(5):
        new = _VAR.sub(sub, value)
        if new == value:
            break
        value = new
    return value


def read_conf(path):
    """Devuelve models.conf como dict, con las variables ya expandidas."""
    conf = {}
    if not os.path.exists(path):
        return conf
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.lstrip().startswith("#"):
                continue
            m = _ASSIGN.match(line)
            if m:
                conf[m.group(1)] = expand(m.group(2).strip(), conf)
    return conf
