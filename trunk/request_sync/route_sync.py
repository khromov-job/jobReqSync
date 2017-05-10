# -*- coding: utf-8 -*-

from request_sync.abstract_sync import AbstractSyncJob
from request_sync.exceptions import ObjectError, RouteSyncError


class RouteSyncJob(AbstractSyncJob):
    """
    Класс синхронизации маршрутов
    """
    def __init__(self, source_host, source_username, source_password, target_host, target_username, target_password,
                 source_id, data=None):
        super().__init__(source_host,
                         source_username,
                         source_password,
                         target_host,
                         target_username,
                         target_password,
                         data)

        self.ident_keys = ['id', 'request_region_uuid', 'metadata_identifier']
        self.deleted_keys = ['request_region_id', 'metadata_id', 'cloudiness_percent', 'linked_by', 'is_changed']
        if source_id == 'int_route':
            self.deleted_keys.append('user_suitable')
        elif source_id == 'ext_route':
            self.deleted_keys.append('suitable')
        self.flag = 'is_changed'

    def __getattr__(self, item):
        try:
            if item == 'region_uuid':
                return self._data['request_region_uuid']
            elif item == 'metadata_identifier':
                return self._data['metadata_identifier']
            elif item == 'identifiers':
                return {'region_uuid': self._data['request_region_uuid'],
                        'metadata_identifier': self._data['metadata_identifier']}
            else:
                raise AttributeError(item)
        except KeyError:
            return None

    def set_data(self, data):
        super(RouteSyncJob, self).set_data(data)
        self.base_resource_uri = '/request/regions/{region_uuid}/routes'.format(region_uuid=self.region_uuid)

    def sync_object(self):
        """
        Синхронизирует маршрут в направлении source->target

        :raise RouteSyncError:  Возбуждается в случае возникновения ошибки при синхронизации признка пригодности
                                маршрута
        """

        is_unimportant = False
        try:
            self.get_object('source')
            self.get_object('target')

            # Если в целевом сегменте существует соответсвующий маршрут
            if self.target['object']:
                    self.update_target_object()
            # Если в целевом сегменте отсутствует соответсвующий маршрут
            else:
                try:
                    self.create_target_object()
                except ObjectError as ex:
                    # При коде 400 считаем, что заявка вместе с районом, к которому привязан маршрут,
                    # пока не синхронизировалась
                    if ex.error_code == 404:
                        is_unimportant = True
                    raise ObjectError(ex.identifiers, str(ex), ex.error_code)

            try:
                self.reset_sync_flag()
            except ObjectError as ex:
                is_unimportant = True
                raise ObjectError(ex.identifiers, str(ex), ex.error_code)

        except ObjectError as ex:
            raise RouteSyncError(ex.identifiers, str(ex), unimp=is_unimportant) from ex

    def get_object_uri(self):
        # Подумать насчет обработки исключения KeyError
        return '/request/regions/{region_uuid}/routes/{metadata_identifier}'\
            .format(region_uuid=self.region_uuid,
                    metadata_identifier=self.metadata_identifier)
