sudo journalctl -u myflask -f      # Gunicorn logs
sudo tail -f /var/log/nginx/error.log


sudo systemctl restart myflask
sudo systemctl restart nginx
