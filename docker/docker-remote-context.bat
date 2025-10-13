docker context use default
docker context rm remote-msi-cloudflared

docker context create remote-msi-cloudflared --docker "host=http://docker2.youmti.net"
docker --context remote-msi-cloudflared ps


docker context use remote-msi-cloudflared


$env:CF_ACCESS_CLIENT_ID="77c75d20b45c38ac5e6f5dd59a5fe1b5.access"
$env:CF_ACCESS_CLIENT_SECRET="6b289bf21eb07ee499e23ce3648e894bf4801c7b518e915df4a33d121e5910d5"


cloudflared access tcp --hostname docker.youmrabti.com --service-token-id "77c75d20b45c38ac5e6f5dd59a5fe1b5.access" --service-token-secret "6b289bf21eb07ee499e23ce3648e894bf4801c7b518e915df4a33d121e5910d5"
