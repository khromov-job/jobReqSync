import logging.config
import yaml
import json
import argparse
import sys

from job_launcher.launcher import JobLauncher
from job_launcher.exceptions import SettingsError, SourceDataError
from job_launcher import __unitype__

from request_sync.misc import __appname__, __uniapp__
from request_sync.req_sync import ReqSyncJob
from request_sync.route_sync import RouteSyncJob
from request_sync.exceptions import SyncError, DiffError
from request_sync.utils import get_identifiers_str


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', nargs='?', default='/etc/opt/' + __appname__,
                            help='Путь к директории с конфигурационными файлами.')
        args = parser.parse_args(sys.argv[1:])

        with open(args.config + '/log_settings.yaml', 'r') as log_conf:
            log_dict = yaml.load(log_conf)

        logging.config.dictConfig(log_dict)
        logger = logging.getLogger(__name__)

        return_code = 0

        logger.info('Запуск приложения', extra={'unitype': __unitype__.format(code=''),
                                                'uniapp': __uniapp__.format(sync_type='', identifiers='')})

        # Создаем экземпляр класса лончера
        launcher = JobLauncher(args.config + '/settings.yaml')
        try:
            logger.info('Получение настроек приложения', extra={'unitype': __unitype__.format(code=''),
                                                                'uniapp': __uniapp__.format(sync_type='', identifiers='')})
            settings = launcher.get_settings()
        except SettingsError as ex:
            logger.critical(ex, extra={'unitype': __unitype__.format(code='code={}'.format(ex.__class__.__name__)),
                                       'uniapp': __uniapp__.format(sync_type='', identifiers='')})
            return_code = logging.getLevelName('CRITICAL')
            logger.debug(ex, exc_info=True)
            return return_code

        source_ids = [(source['id'], source['priority'], source['params'], source['data_type'])
                      for source in settings['data_sources']]
        source_ids.sort(key=lambda source: source[1])

        # Цикл по источникам данных
        for source in source_ids:
            source_id = source[0]
            logger.info('Обработка источника данных {}'.format(source_id), extra={'unitype': __unitype__.format(code=''),
                                                                                  'uniapp': __uniapp__.format(
                                                                                      sync_type='',
                                                                                      identifiers='')})
            try:
                result = launcher.get_data(source_id)
                try:
                    result[source_id] = json.loads(result[source_id])
                except json.JSONDecodeError as ex:
                    raise SourceDataError(source_id, str(ex))
            except SourceDataError as ex:
                logger.warning(ex, extra={'unitype': __unitype__.format(code='code={}'.format(ex.__class__.__name__)),
                                          'uniapp': __uniapp__.format(sync_type='', identifiers='')})

                ls = logging.getLevelName('WARNING')
                if ls > return_code:
                    return_code = ls

                logger.debug(ex, exc_info=True)
                # Перейти к следующему источнику
                continue

            job = None
            job_type = source[3]
            source_host = source[2]['data_host']
            source_username = source[2]['username']
            source_password = source[2]['password']
            target_id = None

            if source_id == 'int_req':
                target_id = 'ext_req'
            elif source_id == 'ext_req':
                target_id = 'int_req'
            elif source_id == 'int_route':
                target_id = 'ext_route'
            elif source_id == 'ext_route':
                target_id = 'int_route'

            item = [src for src in source_ids if src[0] == target_id][0]
            target_host, target_username, target_password = (item[2]['data_host'],
                                                             item[2]['username'],
                                                             item[2]['password'])
            if job_type == 'REQUEST':
                job = ReqSyncJob(source_host,
                                 source_username,
                                 source_password,
                                 target_host,
                                 target_username,
                                 target_password,
                                 job_type)
            elif job_type == 'ROUTE':
                job = RouteSyncJob(source_host,
                                   source_username,
                                   source_password,
                                   target_host,
                                   target_username,
                                   target_password,
                                   source_id,
                                   job_type)

            try:
                try:
                    data_gen = (data for data in result[source_id]['results'])
                except KeyError as ex:
                    raise SourceDataError(source_id, 'Неизвестный ключ словаря: {}'.format(ex))
            except SourceDataError:
                logger.warning(ex, extra={'unitype': __unitype__.format(code='code={}'.format(ex.__class__.__name__)),
                                          'uniapp': __uniapp__.format(sync_type='sync_type={}'.format(job.type),
                                                                      identifiers='')})

                ls = logging.getLevelName('WARNING')
                if ls > return_code:
                    return_code = ls

                logger.debug(ex, exc_info=True)
                # Перейти к следующему источнику
                continue

            # Цикл по данным конкретного источника. data -> конкретный объект синхронизации
            for data in data_gen:
                try:
                    job.set_data(data)

                    d = {'REQUEST': 'заявки', 'ROUTE': 'маршрута'}
                    identifiers_str = get_identifiers_str(job.identifiers)
                    logger.info('Синхронизация {} {}'.format(d[job.type], identifiers_str),
                                extra={'unitype': __unitype__.format(code=''),
                                       'uniapp': __uniapp__.format(sync_type='sync_type={}'.format(job.type),
                                                                   identifiers=identifiers_str)})

                    launcher.launch(job)

                    logger.info('Синхронизация {} {} выполнена успешно'.format(d[job.type], identifiers_str),
                                extra={'unitype': __unitype__.format(code=''),
                                       'uniapp': __uniapp__.format(sync_type='sync_type={}'.format(job.type),
                                                                   identifiers=identifiers_str)})

                except SyncError as ex:
                    # Если ошибка не критичная, то выводим WARNING
                    if ex.unimportant:
                        logger.warning(ex, extra={'unitype': __unitype__.format(code='code={}'
                                                                                .format(ex.__class__.__name__)),
                                                  'uniapp': __uniapp__.format(sync_type='sync_type={}'.format(job.type),
                                                                              identifiers=get_identifiers_str(ex.identifiers))})

                        ls = logging.getLevelName('WARNING')
                        if ls > return_code:
                            return_code = ls
                    # Иначе выводим ERROR
                    else:
                        logger.error(ex, extra={'unitype': __unitype__.format(code='code={}'.format(ex.__class__.__name__)),
                                                'uniapp': __uniapp__.format(sync_type='sync_type={}'.format(job.type),
                                                                            identifiers=get_identifiers_str(ex.identifiers))})

                        ls = logging.getLevelName('ERROR')
                        if ls > return_code:
                            return_code = ls

                        logger.debug(ex, exc_info=True)
                    # Перейти к следующему объекту синхронизации
                continue

            logger.info('Обработка источника данных {} завершена'.format(source_id),
                        extra={'unitype': __unitype__.format(code=''),
                               'uniapp': __uniapp__.format(sync_type='', identifiers='')})

        logger.info('Завершение приложения', extra={'unitype': __unitype__.format(code=''),
                                                    'uniapp': __uniapp__.format(sync_type='', identifiers='')})
        return return_code
    except Exception as ex:
        logger.debug('Приложение аварийно завершило свою работу. Получено исключение: {}'.format(ex), exc_info=True)

