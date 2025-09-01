bind = 'unix:/home/ubuntu/sending/gunicorn.sock'
workers = 3
timeout = 900
keepalive = 5
accesslog = '/home/ubuntu/sending/gunicorn_access_log.log'
errorlog = '/home/ubuntu/sending/gunicorn_error_log.log'
reload_extra_files = ['/home/ubuntu/sending/main.py']
reload = True
# # Below was disabled because it is now being tracked in systemd instead
# daemon = True
# loglevel= 'debug'
# # Enable below to capture python stdout (output) and errors and gunicorn logs in a single file. Currently disabled
# capture_output = True