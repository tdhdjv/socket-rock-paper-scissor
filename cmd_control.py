import sys


def clear_all():
    sys.stdout.write('\033[2J')
    sys.stdout.write('\033[H')