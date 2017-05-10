# -*- coding: utf-8 -*-

from job_launcher.exceptions import WebError

from request_sync.abstract_sync import AbstractSyncJob
from request_sync.exceptions import ObjectError, ReqSyncError
from request_sync.utils import reset_changed


# Рассмотреть целесообразность переопределить __getattr__ для получения данных из self._data (например, request_uuid)
class ReqSyncJob(AbstractSyncJob):
    """
    Класс синхронизации заявок
    """
    def __init__(self, source_host, source_username, source_password, target_host, target_username, target_password,
                 data=None):
        super().__init__(source_host,
                         source_username,
                         source_password,
                         target_host,
                         target_username,
                         target_password,
                         data)

        self.ident_keys = ["uuid", "regions", "sensors", "sensor_uuid", "plcs", "plc_uuid", "format_uuid", "srs_id",
                           "bands", "band_uuid", "routes", "metadata_identifier", "stations", "station_uuid", "id"]
        self.deleted_keys = ["source_id", "format_id", "plc_id", "band_id", "user_id", "operator_id",
                             "status_id", "platform_id", "delivery_method_id", "sensor_id", "plc_id",
                             "format_id", "band_id", "station_id", 'metadata_id', 'is_changed']
        self.flag = 'is_changed'
        self.base_resource_uri = '/request/requests'

    def __getattr__(self, item):
        try:
            if item == 'request_uuid':
                return self._data['uuid']
            elif item == 'identifiers':
                return {'request_uuid': self._data['uuid']}
            else:
                raise AttributeError(item)
        except KeyError:
            return None

    def sync_object(self):
        """
        Синхронизирует заявку в направлении source->target

        :raise ReqSyncError:  Возбуждается в случае возникновения ошибки при синхронизации признка пригодности маршрута
        """

        is_unimportant = False
        try:
            self.get_object('source')
            self.get_object('target')

            # Если в целевом сегменте существует соответсвующая заявка
            if self.target['object']:
                self.update_target_object()
            else:
                self.create_target_object()

            try:
                self.reset_sync_flag()
            except ObjectError as ex:
                is_unimportant = True
                raise ObjectError(ex.identifiers, str(ex), ex.error_code)

        except ObjectError as ex:
            raise ReqSyncError(ex.identifiers, str(ex), unimp=is_unimportant) from ex

    def reset_sync_flag(self):
        """
        Сбрасывает признак необходимости синхронизации объекта в сегменте-источнике

        :raise ObjectError: Возбуждается в случае ошибки при сбросе признака необходимости синхронизации
                            в сегменте-источнике
        """

        # Сбрасываем признак необходимости синхронизации заявки
        super(ReqSyncJob, self).reset_sync_flag()

        # Сбрасываем признак необходимости синхронизации маршрутов, которые были синхронизированы при
        # синхронизации заявки

        route_identifiers = []
        for region in self.source['object']['regions']:
            region_uuid = region['uuid']
            for route in region['routes']:
                if route['is_changed']:
                    route_identifiers.append((region_uuid, route['metadata_identifier']))

        try:
            host = self.source['host']
            for region_uuid, metadata_identifier in route_identifiers:
                uri = '/request/regions/{region_uuid}/routes/{metadata_identifier}'\
                    .format(region_uuid=region_uuid, metadata_identifier=metadata_identifier)

                reset_changed(host,
                              uri,
                              auth_url=self.source['auth_url'],
                              username=self.source['username'],
                              password=self.source['password'],
                              cook=self.source['cook'])
        except WebError as ex:
            raise ObjectError(self.identifiers, str(ex), ex.error_code) from ex

    def get_object_uri(self):
        # Подумать насчет обработки исключения KeyError
        return '{base_resource_uri}/{request_uuid}'.format(base_resource_uri=self.base_resource_uri,
                                                           request_uuid=self.request_uuid)
