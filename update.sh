#!/bin/bash
ssh polina 'rm -r ~/python/miranda/miranda'
scp -pr config.ini  polina:~/python/miranda/
scp -pr miranda     polina:~/python/miranda/
scp -pr twitch.json polina:~/python/miranda/
