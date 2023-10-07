cd /home/rclone
echo "[s3]" >> /home/rclone/.rclone.conf
echo "type = s3" >> /home/rclone/.rclone.conf
echo "provider = AWS" >> /home/rclone/.rclone.conf
mkdir -p giab
rclone mount s3://giab /home/rclone/giab
