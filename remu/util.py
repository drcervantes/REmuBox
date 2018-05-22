""" TODO """
import string
import random
import logging

def rand_str(length):
    """ TODO """
    choices = string.ascii_uppercase + string.digits
    return ''.join(random.SystemRandom().choice(choices) for _ in range(length))


