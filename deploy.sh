# deploy to qdoor

# Copy the files
echo -e "\e[31mCopying files...\e[0m"
scp /home/quentin/gdrive/dev/rpi/reed_door/deploy.sh qdoor:~/reed/deploy.sh
scp /home/quentin/gdrive/dev/rpi/reed_door/tokenss.py qdoor:~/reed/tokenss.py
scp /home/quentin/gdrive/dev/rpi/reed_door/reeddoor.py qdoor:~/reed/reeddoor.py
scp /home/quentin/gdrive/dev/rpi/reed_door/reed.service qdoor:~/reed/reed.service

# Change executable
echo -e "\e[31mMake the file executable\e[0m"
ssh qdoor "sudo chmod +x reeddoor.py"

# Check if the files are there
echo -e "\e[31mDisplaying the files\e[0m"
ssh qdoor "ls -lah /home/pi/reed"

# Deploying the service
# copy the service, refresh units and reload service
echo -e "\e[31mDeploying the service\e[0m"
ssh qdoor "sudo cp /home/pi/reed/reed.service /etc/systemd/system/reed.service"
ssh qdoor "sudo systemctl daemon-reload"
ssh qdoor "sudo systemctl restart reed.service"
ssh qdoor "sudo systemctl status reed.service"
