import argparse
import yaml
from data_collector.app import app
from data_collector.app import collector


def argument_parser():
    parser = argparse.ArgumentParser('data-collector')
    parser.add_argument('-a', '--address', default='localhost',
                        help='host address')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='port')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--template_file', type=str, action='append')
    return parser


def main():
    parser = argument_parser()
    argspec = parser.parse_args()

    if argspec.template_file:
        for t in argspec.template_file:
            with open(t, 'r') as f:
                schedules = yaml.safe_load(f)
            collector.add_job_schedules(schedules)

    app.run(host=argspec.address,
            port=argspec.port,
            debug=argspec.debug)


if __name__ == '__main__':
    main()
