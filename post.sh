#!/bin/bash
ln -s $(pwd) ~/.config/miranda

printf '{}\n' > ~/.config/miranda/client_secret.json
printf '{}\n' > ~/.config/miranda/twitch.json
printf '{}\n' > ~/.config/miranda/vkplay.json
printf '{}\n' > ~/.config/miranda/youtube.json
