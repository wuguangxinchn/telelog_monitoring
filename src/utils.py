"""
Config load utility.

"""
import json
import logging
import os
from datetime import datetime


def load_config(file_path='C:/Data/telelog_monitoring/conf/config.json'):
    """
    Loads our static configuration file.

    :param file_path: The input path to the config file.
    :return: A python dictionary containing configuration variables
    """
    with open(file_path, 'r') as f:
        cfg = json.loads(f.read())

    return cfg


def save_config(cfg, file_path='C:/Data/telelog_monitoring/conf/config.json'):
    """
    Save configuration file.

    :param cfg: A python dictionary containing configuration variables
    :param file_path: The output path to the config file.
    :return: None
    """
    with open(file_path, 'w') as f:
        f.write(json.dumps(cfg))


def get_logger(path="", level='INFO'):
    """
    Sets up our logger
    :return:
    """

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARN,
        "ERROR": logging.ERROR
    }

    # First make the logging dir if not exists
    os.makedirs('{}/log'.format(path), exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(level_map[level])

    fh = logging.FileHandler(filename='{}/log/{}.log'.format(path, datetime.utcnow().strftime('%Y-%m-%d')))
    formatter = logging.Formatter(
        '%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s [%(process)d] %(message)s')
    fh.setFormatter(formatter)
    fh.setLevel(level_map[level])
    logger.addHandler(fh)

    return logger
