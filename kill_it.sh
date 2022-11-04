#!/usr/bin/bash

tasklist.exe |grep SC2 |awk '{print $2}' |xargs /mnt/c/Windows/system32/taskkill.exe /f /pid

