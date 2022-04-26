class Logger:
    stream = None

    @staticmethod
    def init():
        Logger.stream = open("event_log.txt", "w")

    @staticmethod
    def log(line: str):
        Logger.stream.write(line + "\n")

    @staticmethod
    def close():
        Logger.stream.close()
