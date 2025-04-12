ffmpeg -i imta_yji_lmodir.mp4 -t 00:08:09.5 -c copy part1.mp4
ffmpeg -i imta_yji_lmodir.mp4 -ss 00:08:36 -c copy part2.mp4
ffmpeg -f concat -safe 0 -i files.txt -c copy abderraouf.mp4
