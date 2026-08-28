from .prevacm600dc import PrevacM600DC


def main():
    import sys

    import tango.server

    args = ["PrevacM600DC"] + sys.argv[1:]
    tango.server.run((PrevacM600DC,), args=args)
