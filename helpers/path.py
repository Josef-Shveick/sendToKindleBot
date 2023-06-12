import os


class PATH:
    ROOT_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    ENV = os.path.join(ROOT_BASE_DIR, 'env')
