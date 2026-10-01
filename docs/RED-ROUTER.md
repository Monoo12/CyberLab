# Configuración de la red — router y switches

Guía para dejar la red del laboratorio lista para Cyber Lab, con el hardware:
**router TP-Link AX3000 WiFi 6** (familia **Archer** por panel web, o **Deco** mesh por app) +
**2× switch TL-SG1008D**.

**Objetivo:** router en `192.168.10.1`, con IPs fijas para cada equipo (las del `config.toml`),
WiFi apagado y la red **aislada de internet** (el nodo es vulnerable a propósito).

## Identificá tu modelo primero

"AX3000" es la **velocidad WiFi**, no un modelo: TP-Link vende varios con ese número y se dividen en
dos familias con interfaces distintas. **Mirá la etiqueta en la base del router** (dice `Model: ...`)
o la caja:

| Si dice… | Familia | Se configura con | Guía |
|---|---|---|---|
| **Archer AX3000 / AX53 / AX55 / AX55 Pro** | Router clásico | **Panel web** (`tplinkwifi.net`) | Sección **A** (abajo) |
| **Deco X50 / X55** | Mesh | **App Deco** (celular) | Sección **B** (al final) |

La familia **Archer** es lo más probable si lo compraste como "router" suelto; **Deco** se vende como
kit mesh ("sistema", 1–3 nodos). Los pasos de Archer son iguales en todos los modelos AX; el AX55 Pro
solo agrega un puerto de 2,5 Gbps (no cambia nada de esta guía).

## Switches TL-SG1008D → no se configuran (vale para ambas familias)

Son **no administrables** (unmanaged): no tienen IP, ni web, ni menú. Plug-and-play.

⚠️ **Regla de oro: cableá en árbol, sin bucles.** No conectes los 2 switches entre sí *y además*
ambos al router — eso arma un loop, y como estos switches **no tienen Spanning-Tree**, un loop genera
una tormenta de broadcast que tumba toda la red. La topología del tablero es un árbol, así que estás
bien mientras no cierres un anillo.

---

# A) Router Archer (AX3000 / AX53 / AX55 / AX55 Pro) — panel web

### Paso 0 — Conectarte al router
1. Cable de red de tu **PC a un puerto LAN** del router (los **amarillos**), **no** al puerto
   **WAN/Internet** (azul).
2. Navegador → **`http://tplinkwifi.net`** (o `http://192.168.0.1`).
3. Iniciá sesión. Si es la primera vez, corré el asistente: **creá una contraseña de administrador**
   (anotala — la necesita el operador). En el paso de Internet elegí cualquier opción (ej. "IP
   Dinámica") y seguí; no importa, lo vamos a dejar sin internet.

### Paso 1 — Modo Router
**Advanced (Avanzado) > Operation Mode** (o `System Tools > Operation Mode` según firmware) → elegí
**Router** (no *Access Point*). Guardá (reinicia si lo cambia).

### Paso 2 — Cambiar la IP de LAN a `192.168.10.1`
**Advanced > Network > LAN**:
- **IP Address:** `192.168.10.1`
- **Subnet Mask:** `255.255.255.0` → **Save**

⚠️ El router **se reinicia y cambia de dirección**. Reconectá el navegador a **`http://192.168.10.1`**.
Tu PC toma sola una IP `192.168.10.x`. El rango de DHCP se reajusta solo a la nueva subred.

### Paso 3 — DHCP Server (rango)
**Advanced > Network > DHCP Server**:
- **DHCP Server:** *Enable*
- **IP Address Pool:** `192.168.10.100` – `192.168.10.199` (dejamos `.2`–`.99` libres para las IPs fijas)
- **Default Gateway:** `192.168.10.1` → **Save**

### Paso 4 — Reservas de IP (lo más importante) 🔑
Conseguí la **MAC** de cada equipo (con el equipo conectado):
- Windows: `ipconfig /all` → **"Dirección física"**
- Linux/Raspberry: `ip link`
- O más fácil: en el router, la lista **DHCP Client List** muestra los conectados con su MAC.

Luego **Advanced > Network > DHCP Server > Address Reservation → Add**, una por equipo:

| Equipo | IP a reservar |
|---|---|
| PC visitante (terminal) | `192.168.10.10` |
| Nodo **FILE-SERVER** | `192.168.10.20` |
| Decoy workstation *(opcional)* | `192.168.10.30` |
| Decoy security *(opcional)* | `192.168.10.40` |

Guardá y dejá el **Status en ON** en cada reserva. Después **reiniciá cada equipo** (o `ipconfig
/renew`) para que tome la IP reservada.

### Paso 5 — Apagar el WiFi (opcional, recomendado)
**Advanced > Wireless > Wireless Settings** → desactivá **2.4 GHz** y **5 GHz** (todo el lab va por
cable). Más prolijo y seguro.

### Paso 6 — Aislar de internet (recomendado)
**No conectes nada al puerto WAN (azul).** El nodo es vulnerable a propósito, así que conviene **sin
salida a internet**. Todo (`nmap`/`SSH`/`HTTP`) funciona igual porque es tráfico de LAN.

---

# B) Deco mesh (X50 / X55) — app Deco

Si tu equipo es un **Deco**, no hay panel web: todo se hace desde la **app Deco** (iOS/Android), con
el celular conectado al WiFi del Deco. Logramos lo mismo que en la sección A.

### Paso 0 — Deco en modo Router
En la app: **More (Más) > Advanced (Avanzado) > Operation Mode** → **Router** (no *Access Point*).
> Importante: en modo *Access Point* las opciones de LAN IP / DHCP / reservas **no aparecen** en la
> app (las maneja el otro router). Para este laboratorio el Deco tiene que estar en **Router**.

### Paso 1 — LAN IP a `192.168.10.1`
App Deco: **More > Advanced > LAN IP** → IP `192.168.10.1`, máscara `255.255.255.0` → **Save**.
(El Deco se reinicia y los equipos reciben IPs `192.168.10.x`.)

### Paso 2 — Reservas de IP (Address Reservation)
App Deco: **More > Advanced > Address Reservation** → **+** (arriba a la derecha) →
**Select from Client** (elegís un equipo conectado) o **Custom** (MAC + IP a mano). Asigná:

| Equipo | IP |
|---|---|
| PC visitante (terminal) | `192.168.10.10` |
| Nodo **FILE-SERVER** | `192.168.10.20` |
| Decoys *(opcional)* | `192.168.10.30` / `192.168.10.40` |

Guardá cada una. Después reiniciá los equipos (o `ipconfig /renew`) para que tomen la IP.

### Paso 3 — WiFi e internet
- WiFi: podés dejar la red del Deco o bajar la potencia; para el lab va todo por cable.
- Internet: dejá el **WAN del Deco sin conectar** (LAN aislada; el nodo es vulnerable a propósito).
- Puertos: en Deco los puertos Ethernet son LAN una vez en modo Router; cableá los switches a esos.

> El resto (cableado y verificación, abajo) es **igual** para Archer y Deco.

---

## Cableado (árbol, mapea al tablero y a los LEDs) — vale para ambas familias

```
Router LAN1 ───── Switch IZQUIERDO ──── PC visitante (.10)     -> rama LED 0
Router LAN2 ───── Switch DERECHO   ──── FILE-SERVER (.20)      -> rama LED 2
                                   ──── workstation (.30)      -> rama LED 3  (opcional)
                                   ──── security (.40)         -> rama LED 4  (opcional)
```
(2 cables del router, uno a cada switch — **no** conectar los switches entre sí.)
El micro de los LEDs **no va a la red** → va por **USB a la PC**.

## Verificación

Desde la PC visitante:
```bash
ipconfig                      # IP 192.168.10.10, gateway 192.168.10.1 (Windows)
ping 192.168.10.1             # router
ping 192.168.10.20            # nodo
nmap -sn 192.168.10.0/24      # deben aparecer .1, .10, .20 (+ .30/.40)
```
Como el `config.toml` ya usa ese esquema de IPs, **no tenés que cambiar nada** en la app si respetás
estas direcciones.

## Notas

- Para **modo real** solo necesitás sí o sí: router (`.1`), PC (`.10`) y nodo FILE-SERVER (`.20`).
  Los decoys `.30`/`.40` son opcionales (cualquier aparato que responda al ping sirve para que
  aparezca en el `scan`; si no, simplemente no salen y la misión igual apunta al `.20`).
- Usamos **2 switches** por la estética del tablero (izq/der) y para que cada rama de LED tenga su
  tramo; eléctricamente con uno alcanzaría.
- Anotá la **contraseña de admin del router** y guardala con el resto de credenciales del evento.

## Fuentes (TP-Link)
Archer (panel web):
- [Cambiar la IP LAN del router](https://www.tp-link.com/us/support/faq/67/)
- [Configurar Address Reservation (IP fija por MAC)](https://www.tp-link.com/us/support/faq/182/)

Deco (app):
- [Deco: cambiar la LAN IP](https://www.tp-link.com/us/support/faq/2331/)
- [Deco: DHCP / Address Reservation](https://www.tp-link.com/us/support/faq/1795/)
