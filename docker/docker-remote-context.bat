docker context create remote-msi-cloudflared --docker "host=http://docker.youmti.net"
docker context use remote-msi-cloudflared

docker context use default
docker context rm remote-msi-cloudflared
