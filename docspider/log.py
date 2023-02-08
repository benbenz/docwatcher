import logging
import json
from logging.handlers import RotatingFileHandler

logging.INFO_PLUS = 22
logging.addLevelName(logging.INFO_PLUS, "INFO+")
def info_plus(self, message, *args, **kws):
    if self.isEnabledFor(logging.INFO_PLUS):
        # Yes, logger takes its '*args' as 'args'.
        self._log(logging.INFO_PLUS, message, args, **kws) 
logging.Logger.info_plus = info_plus

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[93;20m" #'\033[93m' #"\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    cyan = "\x1b[96;20m" #'\033[96m'
    reset = "\x1b[0m"
    #format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    #format = "%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format = "%(asctime)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.INFO_PLUS: cyan + format + reset ,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt,"%Y-%m-%d %H:%M:%S")
        return formatter.format(record)   

try:
    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)
        LOG_LEVEL = cfg.get("log_level","INFO")
except:
    LOG_LEVEL = "INFO"

LOG_LEVEL = logging.getLevelName(LOG_LEVEL)
if not LOG_LEVEL:
    LOG_LEVEL = logging.INFO

# create logger with 'spam_application'
logger = logging.getLogger("DocCrawler")
logger.setLevel(LOG_LEVEL)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(LOG_LEVEL)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)    

# the file handler
fh = RotatingFileHandler('run.log',maxBytes=32*1024*1024,backupCount=2) #logging.FileHandler('run.log')
fh.setLevel(LOG_LEVEL)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"))
logger.addHandler(fh)