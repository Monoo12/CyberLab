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

## 2. Los tres modos (menú de setup)

| Opción | Qué hace |
|---|---|
| **Panel visual** | On: muestra el mapa de red animado junto a la terminal. Off: solo terminal (más liviano). |
| **Motor** | **Simulado**: nada toca la red real (para ensayar o como fallback). **Real**: los comandos corren de verdad. |
| **Dificultad** | **Fácil**: comando simple + la IP concreta. **Medio**: te orienta por concepto, sin comandos obvios ni IP. **Difícil**: pistas con los comandos **reales** (`nmap`, `hydra`, `curl`) sin las IP. **Pro**: sin comandos ni pistas concretas. |

> En **cualquier** dificultad podés escribir tanto los comandos guiados (`scan`, `inspect <ip>`…)
> como la sintaxis real de las herramientas (`nmap`, `hydra`, `curl`). La dificultad solo cambia
> cuánto te ayuda la terminal, no qué acepta. En **Difícil** y **Pro**, el `exploit hydra` intenta el binario
> `hydra` real si está instalado.

## 3. La misión, paso a paso (lo que ve el visitante)

0. **Pantalla de espera** con efecto "matrix". Cualquier tecla arranca.
1. **Briefing**: mensaje de misión + cronómetro de 5 minutos.
2. `scan` → descubre los dispositivos de la red (tabla NETWORK DISCOVERY; se encienden los LEDs).
3. `inspect <ip>` → puertos abiertos del objetivo (se ilumina su tramo).
4. `connect <ip:80>` → abre el **navegador real** con la web del servidor.
5. `exploit` → vence el login (animación intensa de LEDs) y da acceso.
6. `ls` / `cd <carpeta>` → explora las carpetas del servidor (con directorio actual).
7. `read /restricted/secret.txt` → obtiene el archivo secreto (animación de transferencia).
8. **Mission Complete**: resumen + explicación.
   - **Enter** (o clic) → jugar de nuevo. **M** → volver al menú (cambiar dificultad).

**Otros comandos** disponibles en la terminal: `ping <ip>`, `pwd`, `whoami`, `clear`, y `menu`
(volver al menú de configuración en cualquier momento).

Si el visitante queda inactivo (~40 s configurable), la terminal ofrece una **pista** según el paso
y la dificultad. También puede escribir `hint` o `help` cuando quiera.

## 4. Las 3 formas de entrar (chuleta del operador)

El objetivo es el login del FILE-SERVER. Hay **tres** maneras de vencerlo; con cualquiera alcanza:

1. **Credenciales filtradas en el HTML** — en el paso `connect`, click derecho → *Inspeccionar*:
   el usuario y la clave están en un comentario del HTML y en un campo oculto (`admin` / la clave de
   `config.toml`). Luego se loguea con esas credenciales, o corre `exploit leak`.
2. **SQL injection** — en el login, poner en *usuario* `' OR '1'='1' -- ` (cualquier clave). O correr
   `exploit sqli`. O el `curl` con ese payload (funciona en cualquier dificultad).
3. **Fuerza bruta (Hydra)** — `exploit hydra` prueba un mini-diccionario hasta acertar. En Difícil/Pro
   se escribe el comando `hydra ...` real.

`exploit` sin argumento usa el método por defecto (hydra). Métodos: `exploit leak | sqli | hydra`.

## 5. Reset entre visitantes

- La app se resetea sola al terminar (limpia la terminal, cierra el navegador, apaga los LEDs).
- El nodo se deja en estado limpio recreando el contenedor: en el equipo del nodo, `node/reset.sh`
  (o `docker compose down && docker compose up -d`). Conviene correrlo si alguien dejó una sesión
  abierta o modificó algo.

## 6. Si algo falla en vivo (fallback)

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
