# deploy to qdoor

# Copy the files
echo -e "\e[31mCopying files...\e[0m"
scp /home/quentin/gdrive/dev/rpi/reed_door/tokenss.py /home/quentin/gdrive/dev/rpi/reed_door/reeddoor.py  \
    /home/quentin/gdrive/dev/rpi/reed_door/bot_token.py \
    /home/quentin/gdrive/dev/rpi/reed_door/reed.service \
    /home/quentin/gdrive/dev/rpi/reed_door/alarm_bot.py \
    /home/quentin/gdrive/dev/rpi/reed_door/alarm_bot.service \
    pi@qdoor:~/reed/

# Change executable
ssh pi@qdoor "sudo cp /home/pi/reed/reed.service /etc/systemd/system/reed.service; sudo cp /home/pi/reed/alarm_bot.service /etc/systemd/system/alarm_bot.service; sudo systemctl daemon-reload; sudo systemctl restart reed.service; sudo systemctl status reed.service; sudo systemctl restart alarm_bot.service; sudo systemctl status alarm_bot.service"

