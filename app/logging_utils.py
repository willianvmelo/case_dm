import logging


class RequestContextFilter(logging.Filter):
    def __init__(self, get_request_id):
        super().__init__()
        self.get_request_id = get_request_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.get_request_id() or "-"
        return True


def setup_logging(get_request_id):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s %(message)s",
    )
    logging.getLogger().addFilter(RequestContextFilter(get_request_id))