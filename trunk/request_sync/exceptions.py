# -*- coding: utf-8 -*-

from job_launcher.exceptions import JobError


class ObjectError(JobError):
    """
    Возникает в случае ошибок, связанных с выполнением каких-либо действий с объектами
    (обновление, создание, сброс значения)

    :param identifiers:
    :param message:
    :param error_code:
    """
    def __init__(self, identifiers, message=str(), error_code=0):
        super(ObjectError, self).__init__(message)
        self.identifiers = identifiers
        self.error_code = error_code


class SyncError(JobError):
    """
    Возникает в случае ошибок синхронизации

    :param identifiers:
    :param message:
    :param unimp:
    """
    def __init__(self, identifiers, message=str(), unimp=False):
        super(SyncError, self).__init__(message)
        self.identifiers = identifiers
        self.unimportant = unimp


class ReqSyncError(SyncError):
    """
    Возникает в случае ошибок синхронизации заявок


    :param identifiers:
    :param message:
    :param unimp:
    """
    def __init__(self, identifiers, message=str(), unimp=False):
        if 'request_uuid' not in identifiers:
            identifiers['request_uuid'] = None

        super(ReqSyncError, self).__init__(identifiers,
                                           'Ошибка при синхронизации заявки request_uuid = {}. {}'
                                           .format(
                                               identifiers['request_uuid'],
                                               message),
                                           unimp)


class RouteSyncError(SyncError):
    """
    Возникает в случае ошибок синхронизации маршрутов

    :param identifiers:
    :param message:
    :param unimp:
    """
    def __init__(self, identifiers, message=str(), unimp=False):
        if 'metadata_identifier' not in identifiers:
            identifiers['metadata_identifier'] = None
        if 'region_uuid' not in identifiers:
            identifiers['region_uuid'] = None

        super(RouteSyncError, self).__init__(identifiers,
                                             'Ошибка при синхронизации маршрута '
                                             'metadata_identifier = {} для района region_uuid = {}. {}'
                                             .format(identifiers['metadata_identifier'],
                                                     identifiers['region_uuid'],
                                                     message),
                                             unimp
                                             )


class DiffError(JobError):
    """
    Возникает в случае ошибок, связанных с получение diff'а двух словарей, то есть
    в процессе работы функции get_result_dict.

    :param message:
    """
    def __init__(self, message=str()):
        super(DiffError, self).__init__('Ошибка при формировании результата сравнения объекта из целевого сегмента и '
                                        'сегмента-источника. {}'.format(message))
