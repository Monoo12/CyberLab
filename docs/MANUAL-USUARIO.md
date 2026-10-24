# Manual de usuario — operador de la estación

Guía para quien opera la estación Cyber Lab durante la muestra. No hace falta saber programar.

## 1. Encender y arrancar

1. Prendé la PC de la estación y, si corresponde, el equipo del nodo (FILE-SERVER).
2. Abrí la app:
   - Bundle: doble clic en `CyberLab` (carpeta `dist/CyberLab/`).
   - Desde código: `python -m app.main`.
3. Aparece el **menú de configuración** con tres opciones. Elegí y tocá **COMENZAR**.

Para que arranque sola sin menú (kiosco), poné `autostart = true` en `config.toml` o corré con
`--autostart`.

## 2. Los 4 modos de juego (el operador elige según el visitante)

El selector **Modo de juego** del menú decide *cómo entra* el visitante. Es una rampa de
accesibilidad: de "no sé nada" a "sé de redes".

| Modo | Para quién | Cómo juega |
|---|---|---|
| 🟦 **Tarjetas** | No sabe nada de redes | **Sin teclado.** Toca un botón grande por paso; el único botón activo es el próximo paso. No se puede perder; el tablero y el "suspenso" hacen el show. |
| 🟩 **Guiado** | Se anima un poco | La terminal, pero el próximo comando aparece **ya escrito** en el renglón: alcanza apretar **Enter**. Narra en lenguaje simple qué hizo. Tampoco se pierde. |
| 🟥 **Experto** | Sabe de redes | La terminal real, sin ayuda, con sus 4 dificultades. Es el modo clásico. Acá **sí** se puede no llegar. |
| 🧩 **Reto** | Reto / grupos | Escape room: acertijos con cronómetro donde el **tablero y los componentes** (router, switches, cable/canaleta) dan las pistas. Se responde eligiendo o tipeando. |

> En **Tarjetas** y **Guiado** el objetivo siempre se logra (con suspenso); la **Lección** rota o se fija
> abajo. En **Reto**, si el reloj llega a 0 no se escapa.

### Opciones del menú de setup

| Opción | Qué hace |
|---|---|
| **Modo de juego** | Tarjetas / Guiado / Experto / Reto (ver tabla de arriba). |
| **Lección** | *(solo Tarjetas/Guiado)* qué enseñanza se lleva el visitante en el paso de "entrar": **Clave débil**, **Dato expuesto**, **Truco login**, o **Rotar** (una distinta por ronda). |
| **Panel visual** | On: muestra el mapa de red animado al costado. Off: más liviano. |
| **Motor** | **Simulado**: nada toca la red real (ensayo o fallback). **Real**: los comandos corren de verdad. |
| **Dificultad** | *(solo Experto)* **Fácil**: comando + IP. **Medio**: por concepto. **Difícil**: comandos reales (`nmap`, `hydra`, `curl`) sin IP. **Pro**: sin pistas. |
| **Modo libre** | *(Experto/Guiado)* **Misión**: objetivo FILE-SERVER, 5 min. **Libre**: tiempo infinito, todos los dispositivos hackeables (cada uno con su FLAG). |

> El menú **habilita solo lo que aplica** al modo elegido (la dificultad se activa en Experto; la lección,
> en Tarjetas/Guiado). Para **volver al menú desde cualquier modo**: `Ctrl+M` (o el comando `menu` en la
> terminal, o `[M]` al terminar).

> En **cualquier** dificultad podés escribir tanto los comandos guiados (`scan`, `inspect <ip>`…)
> como la sintaxis real de las herramientas (`nmap`, `hydra`, `curl`). La dificultad solo cambia
> cuánto te ayuda la terminal, no qué acepta. En **Difícil** y **Pro**, el `exploit hydra` intenta el binario
> `hydra` real si está instalado.

## 3. La misión, paso a paso (lo que ve el visitante)

> Esto describe los modos con **terminal** (Experto y Guiado). En **Guiado**, cada paso llega con el
> comando ya escrito: el visitante solo aprieta **Enter**. Para **Tarjetas** y **Reto**, ver 3.b y 3.c.

0. **Pantalla de espera** con efecto "matrix". Cualquier tecla arranca.
1. **Briefing**: mensaje de misión + cronómetro de 5 minutos.
2. `scan` → descubre los dispositivos de la red (tabla NETWORK DISCOVERY; se encienden los LEDs).
3. `inspect <ip>` → puertos abiertos del objetivo (se ilumina su tramo).
4. `connect <ip:80>` → abre el **navegador real** con la web del servidor.
5. `exploit <ip>` → ataca el login del host indicado (hay que dar la IP del FILE-SERVER); animación intensa de LEDs y da acceso.
6. `ls` / `cd <carpeta>` → explora las carpetas del servidor (con directorio actual).
7. `read /restricted/secret.txt` → obtiene el archivo secreto (animación de transferencia).
8. **Mission Complete**: resumen + explicación.
   - **Enter** (o clic) → jugar de nuevo. **M** → volver al menú (cambiar dificultad).

**Otros comandos** en la terminal: `ping <ip>`, `pwd`, `whoami`, `clear`, `menu`.
**Recon extra** (desde nivel **Medio**, y en Modo Libre — en **Fácil no aparecen**): `telnet <ip> [puerto]`,
`traceroute <ip>`, `arp`, `netstat`, e `inspect -v <ip>` (versiones de servicios).

**Como consola real:** **TAB** autocompleta comandos, IPs y rutas; **↑/↓** navegan el historial; **Ctrl+L** limpia.

Si el visitante queda inactivo (~40 s configurable), la terminal ofrece una **pista** según el paso
y la dificultad. También puede escribir `hint` o `help` cuando quiera.

### 3.b. Modo Tarjetas (sin teclado)

Un botón grande por paso; el visitante solo toca. Recorrido en 4 toques:

1. **ESCANEAR LA RED** → se encienden los aparatos en el tablero y dice cuántos hay.
2. **ENTRAR AL SERVIDOR** → arranca el **suspenso** (cuenta regresiva + miles de claves probándose +
   barra de "intrusión detectada", todo en rojo) y **siempre** termina en *ACCESO CONCEDIDO*; aparece la
   enseñanza de la lección.
3. **BUSCAR EL ARCHIVO** → abre las carpetas del servidor.
4. **LLEVARSE EL SECRETO** → copia el archivo → **Misión cumplida** con la enseñanza. Tocar para jugar de nuevo.

### 3.c. Modo Reto (escape room)

4 acertijos con un reloj; el **tablero** da las pistas. Se responde eligiendo una opción o tipeando un
número. Una respuesta equivocada **descuenta tiempo**; el botón **PISTA** vuelve a mostrar la clave en
las luces. Los acertijos: contar los nodos que titilan, encontrar **el cable roto** (el LED quemado del
tablero), contar los destellos del **router**, y seguir la señal por la **canaleta** hasta su destino.
Si el reloj llega a 0, no se escapa (tocar para reintentar).

## 4. Las 3 formas de entrar (chuleta del operador)

El objetivo es el login del FILE-SERVER. Hay **tres** maneras de vencerlo; con cualquiera alcanza:

1. **Credenciales filtradas en el HTML** — en el paso `connect`, click derecho → *Inspeccionar*:
   el usuario y la clave están en un comentario del HTML y en un campo oculto (`admin` / la clave de
   `config.toml`). Luego se loguea con esas credenciales, o corre `exploit <ip> leak`.
2. **SQL injection** — en el login, poner en *usuario* `' OR '1'='1' -- ` (cualquier clave). O correr
   `exploit <ip> sqli`. O el `curl` con ese payload (funciona en cualquier dificultad).
3. **Fuerza bruta (Hydra)** — `exploit <ip> hydra` prueba un mini-diccionario hasta acertar. En Difícil/Pro
   se escribe el comando `hydra ...` real.

`exploit <ip>` requiere la IP del objetivo; sin método usa el default (hydra). Métodos: `exploit <ip> leak | sqli | hydra`. Atacar la IP equivocada falla (no es vulnerable).

## 5. Reset entre visitantes

- La app se resetea sola al terminar (limpia la terminal, cierra el navegador, apaga los LEDs).
- El nodo se deja en estado limpio recreando el contenedor: en el equipo del nodo, `node/reset.sh`
  (o `docker compose down && docker compose up -d`). Conviene correrlo si alguien dejó una sesión
  abierta o modificó algo.

## 6. Si algo falla en vivo (fallback)

> En **modo Real**, al iniciar la misión la terminal corre un **PREFLIGHT** que chequea
> nodo/red/credenciales y avisa con `[OK]`/`[!]`. Si ves un `[!]`, mirá
> [docs/DESPLIEGUE-REAL.md](DESPLIEGUE-REAL.md) o reiniciá en Simulado.

- **La red o el nodo no responden** (errores rojos en la terminal): reiniciá la app y en el menú
  elegí **Motor: Simulado**. La experiencia sigue igual, guionada, sin que el público note la
  diferencia. (O arrancá con `--engine simulated`.)
- **Los LEDs no prenden**: no afecta la misión; la app sigue. Ver `docs/GUIA-HARDWARE.md`.
- **El navegador no abre en `connect`**: verificá que haya Chrome/Edge instalado; igual se puede
  resolver por `exploit` desde la terminal.
- **La interfaz se ve trabada**: nunca debería congelarse (las tareas de red corren en segundo
  plano); si pasa, reiniciá la app.

## 7. Atajos

| Tecla | Acción |
|---|---|
| `F11` | Pantalla completa on/off |
| `Esc` | Salir de pantalla completa |
| cualquier tecla en espera/fin | Arranca / reinicia la misión |
