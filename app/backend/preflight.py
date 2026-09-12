"""Chequeo pre-vuelo del modo real.

Verifica que la app y el nodo esten "en sintonia" antes/al arrancar una mision
real: herramienta de escaneo, web del FILE-SERVER, y sobre todo que las
CREDENCIALES coincidan (SSH real) y que la clave este en el wordlist. Es
advisory (nunca bloquea): devuelve una lista de (estado, texto) que la terminal
imprime en verde/ambar. Corre en un hilo (usa timeouts cortos).
"""
from __future__ import annotations

import shutil


def run_checks(cfg) -> list[tuple[str, str]]:
    res: list[tuple[str, str]] = []

    # 1) Config puro (sin red): la clave del fileserver debe estar en el wordlist
    if cfg.creds.leak_pass in cfg.creds.wordlist:
        res.append(("ok", "wordlist contiene la clave del FILE-SERVER"))
    else:
        res.append(("warn", "la clave del FILE-SERVER NO esta en [creds].wordlist "
                            "-> 'exploit hydra' no la va a encontrar"))

    # 2) Herramienta de escaneo disponible
    if shutil.which("nmap") or (cfg.network.scan_tool == "arp-scan" and shutil.which("arp-scan")):
        res.append(("ok", "herramienta de escaneo disponible (scan/inspect)"))
    else:
        res.append(("warn", "nmap no esta instalado -> 'scan'/'inspect' fallaran "
                            "(instalalo, o usa scan_tool='arp-scan' en Linux)"))

    # 3) Web del FILE-SERVER responde
    try:
        import requests
        r = requests.get(cfg.fileserver.url, timeout=3)
        res.append(("ok", "web del FILE-SERVER responde (" + str(r.status_code) + ") en "
                          + cfg.fileserver.url))
    except Exception:
        res.append(("warn", "la web del FILE-SERVER no responde en " + cfg.fileserver.url
                            + " -> revisa el nodo (docker compose up) y la IP/puerto"))

    # 4) SSH: usuario/clave coinciden con el nodo (lo que usan ls/read/cd)
    try:
        import paramiko
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            cli.connect(cfg.fileserver.ip, port=cfg.fileserver.ssh_port,
                        username=cfg.fileserver.ssh_user, password=cfg.creds.leak_pass,
                        timeout=5, allow_agent=False, look_for_keys=False)
            res.append(("ok", "SSH " + cfg.fileserver.ssh_user + "@" + cfg.fileserver.ip
                              + " OK (credenciales coinciden con el nodo)"))
        except paramiko.AuthenticationException:
            res.append(("warn", "SSH: usuario/clave NO coinciden con el nodo -> ls/read fallaran. "
                                "Sincroniza [creds].leak_pass con LAB_PASS y [fileserver].ssh_user"))
        except Exception:
            res.append(("warn", "SSH: no se pudo conectar a " + cfg.fileserver.ip + ":"
                                + str(cfg.fileserver.ssh_port) + " -> revisa el nodo/SSH"))
        finally:
            try:
                cli.close()
            except Exception:
                pass
    except Exception:
        res.append(("warn", "paramiko no disponible: no se pudo chequear SSH"))

    return res
