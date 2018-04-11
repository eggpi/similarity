import os
import subprocess

def email(message, attachments):
    subprocess.getoutput(
        '/usr/bin/mail -s "%s" ' % message +
        ' '.join('-a ' + a for a in attachments) +
        ' similarity.update@tools.wmflabs.org')
    time.sleep(2*60)

def running_in_toolforge():
    return os.path.exists('/etc/wmflabs-project')
