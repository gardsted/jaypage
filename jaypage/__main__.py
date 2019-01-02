import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("jaypage")
[
    logging.getLogger(i).setLevel(logging.WARNING) 
    for i in logging.root.manager.loggerDict.keys()
    if not i == "jaypage"
]


if __name__ == '__main__':
    logger.info("starting")
    logger.info("stopping")
