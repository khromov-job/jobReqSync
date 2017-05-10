# -*- coding: utf-8 -*-

# TODO Сделать исключение NotImplementedError в методах, которые необходимо переопределять в дочерних классах
# TODO Дописать документацию к методам

import json
import logging
from abc import ABCMeta, abstractmethod

from job_launcher.abstract_job import AbstractJob
from job_launcher.utils import get_data_from_web, create_data_on_web, update_data_on_web, auth_web
from job_launcher.exceptions import WebError, WebAuthError

from request_sync.utils import get_result_dict, reset_changed
from request_sync.exceptions import ObjectError, DiffError


logger = logging.getLogger(__name__)


class AbstractSyncJob(AbstractJob, metaclass=ABCMeta):
    """
    Абстрактный класс синхронизации
    """
    def __init__(self, source_host, source_username, source_password, target_host, target_username, target_password,
                 object_type=None, data=None):
        super().__init__(data)

        source_auth_url = '{host}/auth/authenticate.json'.format(host=source_host)
        source_cook = None
        target_auth_url = '{host}/auth/authenticate.json'.format(host=target_host)
        target_cook = None
        try:
            source_cook = auth_web(source_auth_url, source_username, source_password)
            target_cook = auth_web(target_auth_url, target_username, target_password)
        except WebAuthError as ex:
            logger.debug(ex, exc_info=True)

        self.source = {
            'host': source_host,
            'cook': source_cook,
            'object': {},
            'auth_url': source_auth_url,
            'username': source_username,
            'password': source_password
        }
        self.target = {
            'host': target_host,
            'cook': target_cook,
            'object': {},
            'auth_url': target_auth_url,
            'username': target_username,
            'password': target_password
        }
        
        self.ident_keys = None
        self.deleted_keys = None
        self.flag = None
        self.base_resource_uri = None
        self.type = object_type
        # ***********************
        self.last_modified = None
        # ***********************

    def run(self, *args, **kwargs):
        """
        Выполняет работу по синхронизации объекта

        :raise  ReqSyncError:       Ошибка синхронизации заявки
        :raise  RouteSyncError:     Ошибка синхронизации маршрута
        """

        self.sync_object()

    def get_object(self, segment_type):
        """
        Получает из соответствующего сегмента данные объекта синхронизации
        """

        segment = None
        if segment_type == 'source':
            segment = self.source
        elif segment_type == 'target':
            segment = self.target

        host = segment['host']
        uri = '{object_uri}.json'.format(object_uri=self.get_object_uri())

        try:
            object_json = get_data_from_web(host,
                                            uri,
                                            auth_url=segment['auth_url'],
                                            username=segment['username'],
                                            password=segment['password'],
                                            cook=segment['cook'])
            # Если объект с заданным идентификатором не найден
            if not object_json:
                segment['object'] = None
            else:
                segment['object'] = json.loads(object_json)
                # *************************************************************
                self.last_modified = self.source['object'].get('last_modified')
                # *************************************************************
        except WebError as ex:
            raise ObjectError(self.identifiers, ex.error_code, str(ex)) from ex
        except json.JSONDecodeError as ex:
            raise ObjectError(self.identifiers, 0, str(ex)) from ex

    @abstractmethod
    def sync_object(self):
        """
        Синхронизирует объект в направлении source->target
        """
        raise NotImplementedError('Не определен метод sync_object')

    def create_target_object(self):
        """
        Создает объект синхронизации в целевом сегменте

        :raise ObjectError: Возбуждается в случае ошибки при создании объекта синхронизации в целевом сегменте
        """

        host = self.target['host']
        uri = self.base_resource_uri + '.json'

        try:
            res_target = get_result_dict(self.source['object'],
                                         None,
                                         self.deleted_keys,
                                         None,
                                         self.type)

            data = json.dumps(res_target)
            create_data_on_web(host,
                               uri,
                               data,
                               auth_url=self.target['auth_url'],
                               username=self.target['username'],
                               password=self.target['password'],
                               cook=self.target['cook'])
        except WebError as ex:
            raise ObjectError(self.identifiers, str(ex), ex.error_code) from ex
        except json.JSONDecodeError as ex:
            raise ObjectError(self.identifiers, str(ex)) from ex
        except DiffError as ex:
            raise ObjectError(self.identifiers, str(ex)) from ex

    def update_target_object(self):
        """
        Обновляет объект синхронизации в целевом сегменте

        :raise ObjectError: Возбуждается в случае ошибки при обновлении объекта синхронизации в целевом сегменте
        """

        host = self.target['host']
        uri = '{object_uri}.json'.format(object_uri=self.get_object_uri())

        try:
            res_target = get_result_dict(self.source['object'],
                                         self.target['object'],
                                         self.deleted_keys,
                                         self.ident_keys,
                                         self.type)

            data = json.dumps(res_target)
            update_data_on_web(host,
                               uri,
                               data,
                               auth_url=self.target['auth_url'],
                               username=self.target['username'],
                               password=self.target['password'],
                               cook=self.target['cook'])
        except WebError as ex:
            raise ObjectError(self.identifiers, str(ex), ex.error_code) from ex
        except json.JSONDecodeError as ex:
            raise ObjectError(self.identifiers, str(ex)) from ex
        except DiffError as ex:
            raise ObjectError(self.identifiers, str(ex)) from ex

    def reset_sync_flag(self):
        """
        Сбрасывает признак необходимости синхронизации объекта в сегменте-источнике

        :raise ObjectError: Возбуждается в случае ошибки при обновлении объекта синхронизации в сегменте-источнике
        """

        host = self.source['host']
        uri = self.get_object_uri()

        try:
            reset_changed(host,
                          uri,
                          auth_url=self.source['auth_url'],
                          username=self.source['username'],
                          password=self.source['password'],
                          payload={'last_modified': self.last_modified},
                          cook=self.source['cook'])
        except WebError as ex:
            raise ObjectError(self.identifiers, str(ex), ex.error_code) from ex

    @abstractmethod
    def get_object_uri(self):
        """
        Генерирует url для получения информации по объекту
        """
        raise NotImplementedError('Не определен метод get_object_uri')
