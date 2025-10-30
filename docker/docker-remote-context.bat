docker context use default
docker context rm remote-msi-cloudflared

docker context create remote-msi-cloudflared --docker "host=http://docker.youmti.net"
docker --context remote-msi-cloudflared ps


docker context use remote-msi-cloudflared

ssh-keygen -f "/root/.ssh/known_hosts" -R "192.168.1.77"
docker context create remote-msi-windows --docker "host=ssh://root@192.168.1.77"
docker --context remote-msi-windows ps

docker run --rm -v majal-ecosystem-win_sql_data:/data -v C:\Users\majal\Dev\backups\pgsql:/host_data alpine sh -c "cp -r /host_data/* /data/"

C:\Users\majal\Dev\backups>

ssh-keygen -f "/root/.ssh/known_hosts" -R "192.168.1.77"
ssh-keygen -f "%USERPROFILE%\.ssh\known_hosts" -R "192.168.1.77"
ssh root@192.168.1.77
