# Despliegue en modo Real

Guía para pasar del modo Simulado (default, sin hardware) al **modo Real**, donde los comandos
(`scan`, `inspect`, `connect`, `exploit`, `ls`, `read`…) ejecutan de verdad contra la red del
laboratorio y el nodo FILE-SERVER. Pensada para el armado antes del evento.

> El modo Simulado no necesita nada de esto. Usá Real solo con la red y el nodo montados, y tené
> siempre el Simulado como **fallback** por si algo se cae en vivo.

## 1. Requisitos

**En la PC de la muestra:**
- **`nmap` instalado y en el PATH** (para `scan`/`inspect`).
  - En **Windows**: instalá nmap con **Npcap** (viene en el instalador) y corré la app **como
    administrador** — `nmap -sn` necesita Npcap/privilegios para el barrido ARP.
  - En **Linux**: `sudo apt install nmap`. Alternativa liviana: `arp-scan` + `scan_tool = "arp-scan"`
    en `config.toml`.
- Python o el bundle PyInstaller (ver README).
- Un navegador (Chrome/Edge/Chromium) para el paso `connect`.

**En el equipo del nodo (FILE-SERVER):**
- **Docker** + Docker Compose.

## 2. ⚠️ Las credenciales deben coincidir (lo que más rompe en vivo)

El modo real usa credenciales en **dos lados** que tienen que estar sincronizados. Si no, `ls`/`read`
o `exploit hydra` fallan **en silencio**:

| Qué | En la app (`config.toml`) | En el nodo (`node/docker-compose.yml`) | Regla |
|---|---|---|---|
| Clave del server | `[creds].leak_pass` | `LAB_PASS` | **deben ser iguales** |
| Usuario SSH | `[fileserver].ssh_user` | usuario `ctf` (fijo en el `entrypoint`) | `ssh_user = "ctf"` |
| Diccionario | `[creds].wordlist` | — | debe **contener** `leak_pass` |
| IP / puertos | `[fileserver].ip/http_port/ssh_port` + `[[hosts]]` | `ports` del compose + IP fija del equipo | **deben coincidir** |

Los defaults ya coinciden (`admin` / `S3cr3t-2024!`). Si cambiás la clave, cambiala en **los dos**
lados. **El pre-flight (sección 4) te avisa si no matchean.**

## 3. Levantar el nodo y la app

```bash
# En el equipo del nodo:
cd node
docker compose up -d --build          # levanta Flask (web) + SSH en el contenedor
docker exec cyberlab-fileserver id ctf   # sanity: el usuario ctf existe

# En la PC de la muestra (ajustá config.toml a las IPs reales primero):
nmap -sn 192.168.10.0/24              # sanity: nmap descubre el nodo
ssh ctf@192.168.10.20                 # sanity: SSH entra con la clave del config
python -m app.main --engine real --difficulty medio
```

Reset entre visitantes: `node/reset.sh` (recrea el contenedor y deja el estado limpio).

## 4. Pre-flight automático (chequeo al iniciar)

Al arrancar una misión **en modo real**, la terminal corre un **PREFLIGHT** en segundo plano (no
bloquea) y muestra en verde/ámbar:

- `[OK]/[!]` la clave del FILE-SERVER está (o no) en el `wordlist` → si falta, `exploit hydra` no la encuentra.
- `[OK]/[!]` `nmap`/`arp-scan` disponible → si no, `scan`/`inspect` fallan.
- `[OK]/[!]` la **web** del FILE-SERVER responde en la URL configurada.
- `[OK]/[!]` **SSH** con `ssh_user`/`leak_pass` conecta → si falla, las credenciales no coinciden con el nodo (`ls`/`read` fallarán).

Si ves algún `[!]`, arreglalo (o reiniciá en **Simulado** como fallback).

## 5. Troubleshooting

| Síntoma | Causa probable / arreglo |
|---|---|
| `scan` devuelve "no devolvió hosts" | `nmap` no instalado, sin Npcap/admin (Windows), o IPs fuera del CIDR de `config.toml`. |
| `exploit` (leak/sqli/hydra) falla | La web del nodo no responde (`docker compose up`), o IP/puerto mal en `config.toml`. |
| `exploit hydra` no encuentra la clave | `leak_pass` no está en `[creds].wordlist`, o `LAB_PASS` del nodo ≠ `leak_pass`. |
| `ls`/`read` fallan tras exploit | SSH: `ssh_user`/`leak_pass` no coinciden con el `ctf`/`LAB_PASS` del nodo, o sshd no arrancó. |
| El contenedor no arranca | Si lo buildeaste en **Windows**, revisá que `entrypoint.sh` quedó en **LF** (lo fuerza `.gitattributes`; un `\r` da `bad interpreter: ^M`). |
| `traceroute` tarda mucho (Windows) | `tracert` espera a hosts que no responden; en el lab (pocos saltos) es rápido. No cuelga la GUI. |

## 6. Nota sobre Modo Libre + Real

Los dispositivos "ricos" (router / workstation / security con su propia FLAG y filesystem) **solo
existen en modo Simulado**. En **Real**, solo el **FILE-SERVER** es hackeable de verdad; `exploit`
contra otros hosts falla limpio (no hay servicio vulnerable ahí). Para la experiencia sandbox completa
de Modo Libre, usá el motor **Simulado**.

## 7. Seguridad

- El nodo es **inseguro por diseño** (web + SSH vulnerables a propósito): usalo **solo** en la red
  aislada del laboratorio, nunca expuesto a internet.
- El input del visitante nunca llega a una shell: el parser valida con lista blanca y las rutas SSH se
  escapan con `shlex.quote` (ver `docs/ARQUITECTURA.md`).
