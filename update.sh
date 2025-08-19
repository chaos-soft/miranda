#!/bin/bash
ssh polina 'rm -r ~/python/miranda/miranda-'
ssh polina 'mv ~/python/miranda/miranda ~/python/miranda/miranda-'
scp -pr config.ini  polina:~/python/miranda/
scp -pr miranda     polina:~/python/miranda/
