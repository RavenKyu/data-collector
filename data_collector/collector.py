import time
import os
import types
import operator
import json
import urllib3
import requests
import inspect
import logging
from celery import Celery

from apscheduler.schedulers.background import BackgroundScheduler
from data_collector import (ExceptionResponse, ExceptionScheduleReduplicated)


BROKER_URL = os.environ.setdefault('BROCKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

EVENT_COLLECTOR_URL = os.environ.setdefault('EVENT_COLLECTOR_URL', 'http://localhost:5000')


###############################################################################
def crontab_add_second(crontab):
    cron = [
        'second',
        'minute',
        'hour',
        'day',
        'month',
        'day_of_week']

    crontab = crontab.split()
    if 6 != len(crontab):
        raise ValueError(
            'crontab need 6 values. '
            'second, minute, hour, day, month, day_of_week')
    return dict(zip(cron, crontab))


###############################################################################
class DataCollector:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self.scheduler.start()
        self.templates = dict()

        self.__global_store = dict()

        self.job_broker = Celery(
            'routine-jobs', broker=BROKER_URL, backend=CELERY_RESULT_BACKEND)

    # =========================================================================
    def add_job_schedules(self, schedule_templates: list):
        logging.debug("Adding schedules with template.")
        for schedule_template in schedule_templates:
            schedule_name, trigger = operator.itemgetter(
                'schedule_name', 'trigger')(schedule_template)

            # schedule name can't be duplicated.
            schedule_names = [x['schedule_name'] for x in
                              self.get_schedule_jobs()]
            if schedule_name in schedule_names:
                msg = f'The schedule name \'{schedule_name}\' ' \
                      f'is already assigned.'
                logging.error(msg)
                raise ExceptionScheduleReduplicated(msg)

            self._add_job_schedule(
                schedule_name,
                trigger_type=trigger['type'],
                trigger_setting=trigger['setting'])

            # store the schedule template
            self.templates[schedule_name] = schedule_template
            self.__global_store[schedule_name] = {'_gv': dict()}

    # =========================================================================
    def _add_job_schedule(self, key, trigger_type, trigger_setting):
        if trigger_type == 'crontab' and 'crontab' in trigger_setting:
            crontab = crontab_add_second(trigger_setting['crontab'])
            trigger_type = 'cron'
            trigger_setting = {**trigger_setting, **crontab}
            del trigger_setting['crontab']

        arguments = dict(
            func=self.request_data,
            args=(key,),
            id=key,
            trigger=trigger_type)
        arguments = {**arguments, **trigger_setting}
        logging.debug(f'Schedule "{key}" is added '
                      f'in the job scheduler.')
        self.scheduler.pause()
        try:
            self.scheduler.add_job(**arguments)
        finally:
            self.scheduler.resume()

    # =========================================================================
    def remove_job_schedule(self, schedule_name: str):
        self.get_schedule_job(schedule_name)
        logging.debug(
            f'Removing the schedule "{schedule_name}" from scheduler.')
        self.scheduler.remove_job(schedule_name)
        try:
            logging.debug(f'Removing the schedule.')
            del self.templates[schedule_name]
            del self.__global_store[schedule_name]
        except KeyError:
            logging.warning(
                f'Failed to find the schedule name "{schedule_name}". '
                f'It should be failing to collect data. '
                f'please check the connection is ok.')

        logging.debug(f'Removing the template "{schedule_name}" '
                      f'from the template store.')
        return

    # =========================================================================
    def modify_job_schedule(self, schedule_name, trigger_type, trigger_args):
        logging.debug('Modifying the job schedule "{schedule_name}".')
        if trigger_type == 'crontab' and 'crontab' in trigger_args:
            crontab = crontab_add_second(trigger_args['crontab'])
            trigger = 'cron'

            setting = {**trigger_args, **crontab}
            del setting['crontab']
        else:
            trigger = trigger_type
            setting = trigger_args

        job = self.scheduler.get_job(schedule_name)
        job.reschedule(trigger, **setting)
        self.templates[schedule_name]['trigger'] = dict(
            type=trigger_type, setting=trigger_args)

    # =========================================================================
    @staticmethod
    def get_python_module(code, name):
        module = types.ModuleType(name)
        exec(code, module.__dict__)
        return module

    # =========================================================================
    @staticmethod
    def insert_number_each_line(data: str):
        result = list()
        data = data.split('\n')
        for (number, line) in enumerate(data):
            result.append(f'{number+1:04} {line}')
        return '\n'.join(result)

    # =========================================================================
    @staticmethod
    def filter_dict(dict_to_filter, thing_with_kwargs):
        sig = inspect.signature(thing_with_kwargs)
        filter_keys = [param.name for param in sig.parameters.values() if
                       param.kind == param.POSITIONAL_OR_KEYWORD]
        filtered_dict = {filter_key: dict_to_filter[filter_key] for filter_key
                         in filter_keys}
        return filtered_dict

    # =========================================================================
    def _source(self, name, setting):
        source_type, code, arguments = operator.itemgetter(
            'type', 'code', 'arguments')(setting)
        module = DataCollector.get_python_module(code, name)
        try:
            _gv = self.__global_store[name]
            arguments = {**arguments, **_gv}
            filtered_arguments = DataCollector.filter_dict(arguments, module.main)
            logging.debug(f'{name} - Executing the script')
            data = module.main(**filtered_arguments)
        except Exception as e:
            code = DataCollector.insert_number_each_line(code)
            logging.error(f'{e}\ncode: \n{code}')
            raise
        return data

    # =========================================================================
    def request_data(self, schedule_name):
        st = time.time()
        schedule = self.templates[schedule_name]
        if schedule_name not in self.templates:
            msg = f'The template "{schedule_name}" ' \
                  f'is not in the main template store'
            logging.error(msg)
            raise KeyError(msg)

        # checking use flag
        if not schedule['use']:
            logging.info(f'{schedule_name} is disabled.')
            return

        # source
        try:
            data = self._source(schedule_name, schedule['source'])
        except Exception as e:
            logging.error(f'{schedule_name} - {e}')
            raise
        if data is None:
            message = f'[{schedule_name}] The user function returned None.'
            logging.warning(message)

        # works
        # calling function for each works with arguments via celery
        for work in schedule['works']:
            work_type, arguments = operator.itemgetter(
                'type', 'arguments')(work)
            self.job_broker.send_task(
                work_type, args=(data, ), kwargs=arguments)

        # sending events to the event
        # PING
        # event emitting
        data = json.dumps(data)
        event = {
            'name': schedule_name,
            'event': {
                'type': 'data-collector',
                'schedule_name': schedule_name},
            'data': data
        }
        try:
            self.emit_event(schedule_name, event)
        except (urllib3.exceptions.MaxRetryError,
                requests.exceptions.ConnectionError) as e:
            logging.error(f'Connection Error: Failed to emit events.')
        except Exception as e:
            logging.error(f'{event["name"]} - {e}')
            import traceback
            traceback.print_exc()
        latency_ms = int((time.time() - st) * 1000)
        logging.info(f'{schedule_name} '
                     f'- Succeed collecting data and emitting events '
                     f'- {latency_ms}ms')
        return

    # =========================================================================
    def emit_event(self, name: str, event: dict):
        with requests.Session() as s:
            api = EVENT_COLLECTOR_URL + '/api/v1/events/emit'
            response = s.post(api, json=event)
            if response.status_code != 200:
                raise Exception(
                    f'code: {response.status_code}\n'
                    f'messages: {name} - {response.reason}')

    # =========================================================================
    def remove_job_schedule(self, _id: str):
        self.scheduler.remove_job(_id)
        return

    # =========================================================================
    def modify_job_schedule(self, _id, seconds):
        self.scheduler.reschedule_job(_id, trigger='interval', seconds=seconds)

    # =========================================================================
    def get_schedule_jobs(self):
        jobs = self.scheduler.get_jobs()
        if not jobs:
            logging.debug('No schedules running now.')
            return jobs
        result = list()
        for job in jobs:
            schedule_name = job.id
            next_run_time = job.next_run_time
            template_data = self.templates[schedule_name]
            template_data['next_run_time'] = next_run_time
            result.append(template_data)
        return result
