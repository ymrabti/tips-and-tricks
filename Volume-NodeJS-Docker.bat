docker volume create image_volume
docker run -d -v image_volume:/app/images my_node_app


const fs = require('fs');
const path = require('path');
// Function to save image buffer to a file
function saveImage(buffer, filename) {
const imagePath = path.join('/app/images', filename); // Path inside the container
fs.writeFile(imagePath, buffer, (err) => {
   if (err) {
      console.error('Error writing image:', err);
   } else {
      console.log('Image saved to', imagePath);
   }
});
}


docker run -d -v image_volume:/app/images my_node_app
docker run --rm -v image_volume:/data busybox ls /data
docker cp $(docker create -v image_volume:/data busybox):/data /path/on/host
docker run -d -v /path/on/host:/app/images my_node_app
