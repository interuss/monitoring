import os
import sys

from monitoring.mock_uss import webapp


def main(argv):
    del argv
    port = int(os.environ.get("MOCK_USS_PORT", "8071"))
    webapp.setup()
    webapp.start_periodic_tasks_daemon()
    webapp.run(host="localhost", port=port)


if __name__ == "__main__":
    main(sys.argv)
