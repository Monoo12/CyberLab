# FILE-SERVER vulnerable a proposito: Flask (web) + OpenSSH (para ls/read).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
    && rm -rf /var/lib/apt/lists/*

# SSH: permitir password auth (para paramiko y, en avanzado, hydra-ssh)
RUN sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

ENV LAB_USER=admin \
    LAB_PASS=S3cr3t-2024! \
    LAB_BASE=/srv/lab \
    LAB_DB=/tmp/lab.db \
    PORT=80

EXPOSE 80 22
ENTRYPOINT ["/app/entrypoint.sh"]
