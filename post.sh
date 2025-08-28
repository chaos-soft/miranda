#!/bin/bash
mkdir -p ~/.config/miranda

curl -LJ -o ~/.config/miranda/config.ini https://github.com/chaos-soft/miranda/raw/refs/heads/master/config.ini

printf '{}\n' > ~/.config/miranda/twitch.json
printf '{}\n' > ~/.config/miranda/vkplay.json
printf '{}\n' > ~/.config/miranda/youtube.json
