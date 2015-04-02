# -*- coding: utf-8 -*-
"""\

.. module:: vmconstruct.silly
    :platform: Unix
    :synopsis: Silly stuff

.. moduleauthor:: James Dingwall <james@dingwall.me.uk>


figlet "Hello World!" | toilet -f term --metal | /usr/games/cowsay -n
"""

import logging
import subprocess
import tempfile



class cowstatus(object):
    """\
    Print a message.
    """
    def __init__(self, msg):
        figlet = ["/usr/bin/figlet"]
        toilet = ["/usr/bin/toilet", "-f", "term", "--metal"]
        cowsay = ["/usr/games/cowsay", "-n"]

        with tempfile.TemporaryFile() as tfp:
            tfp.write(msg.encode("UTF-8"))
            tfp.seek(0)
            p1 = subprocess.Popen(figlet, stdin=tfp, stdout=subprocess.PIPE)

        p2 = subprocess.Popen(toilet, stdin=p1.stdout, stdout=subprocess.PIPE)
        p3 = subprocess.Popen(cowsay, stdin=p2.stdout, stdout=subprocess.PIPE)
        print(p3.communicate()[0].decode("UTF-8"))


if __name__ == "__main__":
    cowstatus("Hello World!")
