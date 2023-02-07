import logging

import logging
logging.INFO_PLUS = 22
logging.addLevelName(logging.INFO_PLUS, "INFO+")
def info_plus(self, message, *args, **kws):
    if self.isEnabledFor(logging.INFO_PLUS):
        # Yes, logger takes its '*args' as 'args'.
        self._log(logging.INFO_PLUS, message, args, **kws) 
logging.Logger.info_plus = info_plus

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = '\033[93m' #"\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    cyan = '\033[96m'
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

# create logger with 'spam_application'
logger = logging.getLogger("DocCrawler")
logger.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)    

# the file handler
fh = logging.FileHandler('run.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"))
logger.addHandler(fh)