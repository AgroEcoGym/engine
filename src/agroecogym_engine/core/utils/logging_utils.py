########################################
# farm/utils/logging_utils.py
########################################

import logging
from datetime import datetime
from pathlib import Path


def setup_logger(name="farmgym", level=logging.INFO, log_dir="logs"):
    """
    Configure un logger standard pour l'environnement FarmGym.

    - Logue à la fois dans la console et dans un fichier daté.
    - Format lisible avec timestamps et niveau de log.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True, parents=True)
    log_path = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Evite les doublons si reconfiguré
    if not logger.handlers:
        # Console
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
        logger.addHandler(ch)

        # Fichier
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(fh)

    return logger


def get_logger(name="farmgym"):
    """
    Retourne un logger existant (ou le crée s'il n'existe pas).
    """
    if name in logging.Logger.manager.loggerDict:
        return logging.getLogger(name)
    else:
        return setup_logger(name)
