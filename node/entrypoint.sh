#!/usr/bin/env bash
# Prepara el arbol de archivos, el usuario SSH y arranca sshd + Flask.
set -e

# 1) Arbol de archivos del "servidor" (lo que veran ls/read)
mkdir -p "$LAB_BASE"/public "$LAB_BASE"/users "$LAB_BASE"/logs "$LAB_BASE"/restricted
cp -f /app/files/restricted/secret.txt "$LAB_BASE"/restricted/secret.txt
echo "<html><body>FILE-SERVER</body></html>" > "$LAB_BASE"/public/index.html
echo "Servidor de archivos del laboratorio." > "$LAB_BASE"/public/readme.txt
echo "admin" > "$LAB_BASE"/users/admin
echo "guest" > "$LAB_BASE"/users/guest
echo "conexiones recientes..." > "$LAB_BASE"/logs/access.log
echo "intentos de login..." > "$LAB_BASE"/logs/auth.log

# 2) Usuario ctf para SSH (clave debil = LAB_PASS)
if ! id ctf >/dev/null 2>&1; then
    useradd -m -s /bin/bash ctf
fi
echo "ctf:$LAB_PASS" | chpasswd
chown -R ctf:ctf "$LAB_BASE"

# 3) sshd
mkdir -p /run/sshd
ssh-keygen -A 2>/dev/null || true   # genera host keys si faltan (si no, sshd no arranca)
/usr/sbin/sshd

# 4) Base de datos vulnerable + servidor web (proceso principal)
python /app/seed_db.py
exec python /app/app.py
