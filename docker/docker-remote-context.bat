docker context use default
docker context rm remote-msi-cloudflared

docker context create remote-msi-cloudflared --docker "host=http://docker.youmti.net"
docker --context remote-msi-cloudflared ps


docker context use remote-msi-cloudflared

ssh-keygen -f "/root/.ssh/known_hosts" -R "192.168.1.77"
docker context create remote-msi-windows --docker "host=ssh://root@192.168.1.77"
docker --context remote-msi-windows ps

ssh-keygen -f "/root/.ssh/known_hosts" -R "192.168.1.77"
ssh root:MSI_ROOT_2025@192.168.1.77
