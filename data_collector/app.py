from flask import Flask

from data_collector.collector import DataCollector
# from data_collector.modules.api.v1.api import bp as api_v1

# from restful_modbus_api.modules import NoContent
# from restful_modbus_api.modules.schedules.schedules import bp as module_schedule
# from restful_modbus_api.modules.base.base import bp as module_base

collector = DataCollector()

app = Flask(__name__)
# app.register_blueprint(api_v1, url_prefix='/api/v1')
# app.register_blueprint(module_schedule, url_prefix='/schedules')
# app.register_blueprint(module_base, url_prefix='/')
# api_v1.gv['collector'] = collector
# api_v1.gv['app'] = app

