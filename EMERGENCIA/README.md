# EMERGENCIA — Restaurar el lab desde cero

Para cuando **alguien borra o formatea una de las PCs del lab**. El lab tiene
**dos equipos** y cada uno tiene su script de restauración en esta carpeta:

| PC | Rol | Usuario | Script |
|----|-----|---------|--------|
| **FILE-SERVER** | Nodo vulnerable dockerizado | `MUESTRANOBORRAR_SERVER` | `restaurar.sh` |
| **TERMINAL** | Estación del visitante (GUI + kiosco) | `MUESTRANOBORRAR` | `restaurar-terminal.sh` |

Corré en cada PC **el script de su rol** (logueado con el usuario de esa PC).
La parte de abajo de este README es la del **FILE-SERVER**; la de la
**TERMINAL** está más abajo, en su propia sección.

---

## FILE-SERVER (`restaurar.sh`)

Reinstala y deja el nodo **FILE-SERVER** de CyberLab *exactamente* como estaba:
Docker rootless, el contenedor vulnerable, arranque automático al boot, el
cartel de estado en el login y la config real.

> Es **solo** para el equipo que hace de **FILE-SERVER** (usuario
> `MUESTRANOBORRAR_SERVER`). No toca la red ni el sistema del usuario `alumno`.

## Uso

```bash
# 1) Recuperar el repo (si ya lo tenés, saltá este paso)
git clone https://github.com/Monoo12/CyberLab ~/CyberLab
#    (o copialo de un backup; tiene que incluir esta carpeta EMERGENCIA/)

# 2) Logueado como MUESTRANOBORRAR_SERVER, correr:
bash ~/CyberLab/EMERGENCIA/restaurar.sh
```

Te va a pedir la **contraseña de `MUESTRANOBORRAR_SERVER`** (sudo) para los pasos
de sistema. Es **idempotente**: podés correrlo las veces que quieras, salta lo
que ya esté hecho.

## Qué deja montado

| Componente | Detalle |
|---|---|
| Paquetes apt | `uidmap slirp4netns dbus-user-session fuse-overlayfs python3-paramiko` |
| Docker rootless | binarios estáticos **29.9.2** en `~/bin` |
| Compose v2 | **v2.40.3** en `~/.docker/cli-plugins/` |
| Puerto 80 | `setcap cap_net_bind_service=ep ~/bin/rootlesskit` |
| Arranque al boot | `systemd --user` docker.service + `linger` ON + contenedor `unless-stopped` |
| Cartel de login | bloque CyberLab en `~/.bashrc` (env + `cyberlab_status`) |
| Config real | restaura `config.toml` desde `config.example.toml` (apunta a `192.168.10.20`) |
| Nodo | levanta `cyberlab-fileserver` (web :80, SSH :2222, healthy) |

## Archivos de esta carpeta

- `restaurar.sh` — el instalador. **Editá las versiones del encabezado** si en el
  futuro actualizás Docker/Compose, para que el snapshot siga fiel.
- `bashrc-cyberlab.snippet` — el bloque que va al `~/.bashrc`.

> **config.toml:** no se versiona (patrón en `.gitignore`). El script lo restaura
> desde `../config.example.toml`, que hoy es idéntico al real salvo comentarios y
> ya apunta a `192.168.10.20`. Si en el futuro tu `config.toml` difiere del
> example y querés una copia fiel, dejá un `EMERGENCIA/config.toml.snapshot`
> local (está en `.gitignore`, no se sube): el script lo prioriza si existe.

## Pendientes que **no** dependen de esta PC

El script no puede rehacer lo que vive fuera del equipo. Después de restaurar,
verificá:

- **Reserva DHCP en el router** para la MAC de `enp2s0` → IP fija `192.168.10.20`.
- **Red aislada del lab** `192.168.10.0/24` (router/DHCP en `.1`).

Si la IP que muestra el cartel no es `.20`, es por esto (no por el software).

---

## TERMINAL (`restaurar-terminal.sh`)

Reinstala y deja **esta PC = la TERMINAL** (estación del visitante)
*exactamente* como estaba: dependencias del sistema, venv de Python, `config.toml`
en **modo REAL**, acceso al **ESP** de la tira LED por USB, y arranque automático
del **kiosco en pantalla completa** con autologin.

> Es **solo** para el equipo que hace de **TERMINAL** (usuario `MUESTRANOBORRAR`).
> **No** instala el nodo vulnerable (`node/`) — eso es del FILE-SERVER.

### Uso

```bash
# 1) Recuperar el repo (si ya lo tenés, saltá este paso)
git clone https://github.com/Monoo12/CyberLab ~/CyberLab
#    (o copialo de un backup; tiene que incluir esta carpeta EMERGENCIA/)

# 2) Logueado como MUESTRANOBORRAR, correr:
bash ~/CyberLab/EMERGENCIA/restaurar-terminal.sh

# 3) REINICIAR -> la terminal arranca sola en el menú de setup, pantalla completa.
```

Te va a pedir la **contraseña de `MUESTRANOBORRAR`** (sudo) para los pasos de
sistema. Es **idempotente**: podés correrlo las veces que quieras, salta lo que
ya esté hecho.

### Qué deja montado

| Componente | Detalle |
|---|---|
| Paquetes apt | `python3-venv python3-tk python3-dev nmap arp-scan hydra git curl` |
| Navegador | `google-chrome` (fallback `chromium`) para el paso `connect` |
| venv | `~/CyberLab/.venv` con `requirements.txt` (customtkinter fijado **<6** → 5.2.x) |
| `config.toml` | **modo real**: `engine="real"`, `interface="enp2s0"`, serie `/dev/ttyUSB0`, `fullscreen=true` |
| Serie (LEDs) | usuario agregado al grupo `dialout` (ESP en `/dev/ttyUSB0`) |
| Kiosco al boot | `~/.config/autostart/cyberlab.desktop` → `run-terminal.sh --menu --fullscreen` |
| Autologin | drop-in `/etc/sddm.conf.d/95-cyberlab-autologin.conf` (User=MUESTRANOBORRAR) |

> **config.toml:** no se versiona (patrón en `.gitignore`). El script lo escribe
> con los valores reales de la terminal. Si alguna vez tu `config.toml` difiere y
> querés una copia fiel, dejá un `EMERGENCIA/config.toml.snapshot` local (está en
> `.gitignore`, no se sube): el script lo prioriza si existe.

### Pendientes que **no** dependen de esta PC

Después de restaurar y reiniciar, verificá:

- **Red del lab** `192.168.10.0/24`: esta PC debería tomar `192.168.10.10`.
- El **FILE-SERVER** (`192.168.10.20`) tiene que estar **encendido** para el modo
  real; si no, la app cae a simulado como fallback.
- El **ESP** de la tira LED enchufado por USB (aparece como `/dev/ttyUSB0`).
- El **nombre de sesión** de sddm (`Session=plasma`): si al bootear no entra solo,
  revisá `ls /usr/share/wayland-sessions /usr/share/xsessions` y ajustá el drop-in.
