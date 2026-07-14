"""
Archivo: src/logger.py
Proyecto: Krishna Omega Ultra
Descripción: Configuración de logging con rotación.
"""
import os, logging, sys
from logging.handlers import RotatingFileHandler

def get_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    os.makedirs('logs', exist_ok=True)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    fh = RotatingFileHandler('logs/bot.log', maxBytes=5*1024*1024, backupCount=3)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger