docker save -o <image_name>.tar <image_name>
scp <image_name>.tar user@remote-server:/path/to/destination/
docker load -i <image_name>.tar
docker run --rm -d --name <new_container_name> <image_name>
