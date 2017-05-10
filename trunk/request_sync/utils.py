import hashlib
import requests
from deepdiff import DeepDiff
from copy import deepcopy

from job_launcher.utils import auth
from job_launcher.exceptions import WebError
from request_sync.exceptions import DiffError


def delete_keys(data, keys):
    """
    Удаляет из словаря data все ключи, перечисленные в keys.
    Возвращает новый словарь.

    :param data:        словарь
    :param keys:        список ключей, которые необходимо удалить

    :return:            новый словарь
    """
    try:
        if isinstance(data, dict):
            new_dict = dict()
            for ess in data:
                if ess not in keys:
                    if isinstance(data[ess], (dict, list)):
                        rec = delete_keys(data[ess], keys)
                        if rec != {} or []:
                            new_dict[ess] = rec
                    else:
                        new_dict[ess] = data[ess]
            return new_dict
        elif isinstance(data, list):
            new_list = list()
            for i in data:
                if i not in keys:
                    if isinstance(i, (dict, list)):
                        rec = delete_keys(i, keys)
                        if rec != {} or []:
                            new_list.append(rec)
                    else:
                        new_list.append(i)
            return new_list
    except KeyError as ex:
        raise DiffError(message='Ошибка при удалении ключа из словаря. Не найден ключ {}'.format(ex)) from ex
    except (ValueError, TypeError) as ex:
        raise DiffError(message='Ошибка при удалении ключа из словаря. {}'.format(ex)) from ex


def sift_keys(data, keys):
    """
    Отсеивает (удаляет) из словаря data все ключи, кроме перечисленных в keys.
    Возвращает новый словарь.

    :param data:        словарь
    :param keys:        список ключей, которые должны остаться в словаре

    :return:            новый словарь
    """
    try:
        if isinstance(data, dict):
            new_dict = dict()
            for ess in data:
                if ess in keys:
                    if isinstance(data[ess], (dict, list)):
                        rec = sift_keys(data[ess], keys)
                        new_dict[ess] = rec
                    else:
                        new_dict[ess] = data[ess]
            return new_dict
        elif isinstance(data, list):
            new_list = list()
            for i in data:
                if isinstance(i, (dict, list)):
                    rec = sift_keys(i, keys)
                    if rec != {} or []:
                        new_list.append(rec)
                else:
                    new_list.append(i)
            return new_list
    except KeyError as ex:
        raise DiffError(message='Ошибка при отсеивании ключей. Не найден ключ {}'.format(ex)) from ex
    except (ValueError, TypeError) as ex:
        raise DiffError(message='Ошибка при отсеивании ключей. {}'.format(ex)) from ex


def parse_path(str_path):
    """
    Преобразует строку вида "['data'][0]['type']" в массив вида ['data', 0, 'type']
    Возвращает список ключей и числовых индексов, не изменяя их порядок следования.

    :param str_path:        путь в строковом формате

    :return:                путь в виде списка
    """
    list_path = list()
    cutted = str_path[1: len(str_path) - 1]
    clear = (cutted.replace('[', '')).split(']')
    for ch in clear:
        list_path.append(int(ch)) if ch.isdigit() else list_path.append(ch.replace("'", ''))
    return list_path


def recursive_set(data, path, value):
    """
    Устанавливает значение value в словаре data по адресу path.
    Ничего не возвращает.

    :param data:    словарь
    :param path:    путь в виде списка, по которому необходимо установить значение
    :param value:   значение

    :return:        None
    """
    try:
        head, tail = path[0], path[1:]
        if tail:
            # Еще не дошли до конца пути
            try:
                return recursive_set(data[head], tail, value)
            except IndexError:
                data[head].append(value)
        else:
            # Путь пройден, присваиваем значение
            data[head] = value
    except KeyError as ex:
        raise DiffError(message='Ошибка при рекурсивной установке значения. Не найден ключ {}'.format(ex)) from ex
    except (ValueError, TypeError) as ex:
        raise DiffError(message='Ошибка при рекурсивной установке значения. {}'.format(ex)) from ex

def pre_process(data):
    """
    Преобразует в словари вложенные сущности, являющиеся списками внутри data,
    создавая для каждого элемента уникальный ключ-идентификатор.

    :param data:        объект словарь-заявка, содержащая сущности-списки, которые нужно преобразовать в словари

    :return:            новый словарь, где сущности-списки преобразованы в словари
    """
    try:
        if 'regions' in data:
            new_regions = dict()
            regions = data['regions']
            for region in regions:
                if 'sensors' in region:
                    new_sensors = dict()
                    sensors = region['sensors']
                    for sensor in sensors:
                        if 'plcs' in sensor:
                            new_plcs = dict()
                            plcs = sensor['plcs']
                            for plc in plcs:
                                plc_uniq = str(plc['plc_uuid']) + str(plc['format_uuid']) + str(plc['srs_id'])
                                k = hashlib.md5()
                                k.update(plc_uniq.encode('utf-8'))
                                plc_key = k.hexdigest()
                                new_plcs[plc_key] = plc
                            sensor['plcs'] = new_plcs
                        if 'bands' in sensor:
                            new_bands = dict()
                            bands = sensor['bands']
                            for band in bands:
                                new_bands[band['band_uuid']] = band
                            sensor['bands'] = new_bands
                        new_sensors[sensor['sensor_uuid']] = sensor
                    region['sensors'] = new_sensors
                if 'routes' in region:
                    new_routes = dict()
                    routes = region['routes']
                    for route in routes:
                        new_routes[route['metadata_identifier']] = route
                    region['routes'] = new_routes
                if 'stations' in region:
                    new_stations = dict()
                    stations = region['stations']
                    for station in stations:
                        new_stations[station['station_uuid']] = station
                    region['stations'] = new_stations
                new_regions[region['uuid']] = region
            data['regions'] = new_regions
        return data
    except (KeyError, IndexError, ValueError, TypeError) as ex:
        raise DiffError(message='Ошибка в процессе предобработки данных. {}'.format(ex))


def post_process(data):
    """
    Преобразует вложенные в словарь data словари обратно в списки.

    :param data:    объект словаря (заявка), содержащий сущности-словари, которые необходимо преобразовать в списки

    :return:        новый словарь, в котором выполнено обратное преобразование сущностей-словарей в списки
    """
    try:
        if 'regions' in data:
            new_regions = list()
            regions = data['regions']
            for region in regions.values():
                if 'sensors' in region:
                    new_sensors = list()
                    sensors = region['sensors']
                    for sensor in sensors.values():
                        if 'plcs' in sensor:
                            new_plcs = list()
                            plcs = sensor['plcs']
                            new_plcs.extend(plcs.values())
                            sensor['plcs'] = new_plcs
                        if 'bands' in sensor:
                            new_bands = list()
                            bands = sensor['bands']
                            new_bands.extend(bands.values())
                            sensor['bands'] = new_bands
                        new_sensors.append(sensor)
                    region['sensors'] = new_sensors
                if 'routes' in region:
                    new_routes = list()
                    routes = region['routes']
                    new_routes.extend(routes.values())
                    region['routes'] = new_routes
                if 'stations' in region:
                    new_stations = list()
                    stations = region['stations']
                    new_stations.extend(stations.values())
                    region['stations'] = new_stations
                new_regions.append(region)
            data['regions'] = new_regions
        return data
    except (KeyError, IndexError, ValueError, TypeError) as ex:
        raise DiffError(message='Ошибка в процессе постобработки данных. {}'.format(ex)) from ex


def get_result_dict(source, target=None, deleted_keys=None, ident_keys=None, data_type=None):
    """
    Формирует результирующий словарь, образованный путем дополнения "скелета" словаря source
    значениями, которые изменились, или появились в source по сравнению с target.
    Если data_type="REQUEST", вызывает функции pre_process() и post_process() для корректной
    обработки структуры данных.

    :param source:          словарь-источник, содержащий новые значения
    :param target:          словарь-цель, содержащий старые значения
    :param deleted_keys:    список ключей, которые нужно удалить из словарей перед получением diff'a
    :param ident_keys:      список ключей, из которых формируется "скелет" будущего diff'a
    :param data_type:       тип обрабатываемой сущности (для заявок REQUEST, для маршрутов ROUTE)

    :return:                результирующий словарь, сформированный в зависимости от входных параметров
    """
    try:
        source = deepcopy(source)
        target = deepcopy(target)
        if target is None and deleted_keys is not None:
            return delete_keys(source, deleted_keys)
        elif target == source and ident_keys is not None:
            return sift_keys(source, ident_keys)
        else:
            if data_type == "REQUEST":
                source = pre_process(source)
                target = pre_process(target)
                if 'regions' in source:
                    ident_keys.extend(source['regions'].keys())
                    for region in source['regions'].values():
                        if 'sensors' in region:
                            ident_keys.extend(region['sensors'].keys())
                            for sensor in region['sensors'].values():
                                if 'plcs' in sensor:
                                    ident_keys.extend(sensor['plcs'].keys())
                                if 'bands' in sensor:
                                    ident_keys.extend(sensor['bands'].keys())
                        if 'routes' in region:
                            ident_keys.extend(region['routes'].keys())
                        if 'stations' in region:
                            ident_keys.extend(region['stations'].keys())
            source = delete_keys(source, deleted_keys)
            target = delete_keys(target, deleted_keys)
            skeleton = sift_keys(source, ident_keys)
            diff = DeepDiff(target, source)
            for diff_k in diff.keys():
                if diff_k == 'values_changed' or diff_k == 'type_changes':
                    fresh_vals = diff[diff_k]
                    for k in fresh_vals:
                        raw_str = k[4:]
                        path = parse_path(raw_str)
                        if path[-1::][0] == 'id':
                            value = fresh_vals[k]['old_value']
                        else:
                            value = fresh_vals[k]['new_value']
                        recursive_set(skeleton, path, value)
                if diff_k == 'dictionary_item_added':
                    fresh_vals = diff[diff_k]
                    for k in fresh_vals:
                        raw_str = k[4:]
                        path = parse_path(raw_str)
                        value = eval(str(source) + raw_str)
                        value = delete_keys(value, 'id')
                        recursive_set(skeleton, path, value)
            if data_type == "REQUEST":
                return post_process(skeleton)
            else:
                return skeleton
    except (KeyError, IndexError, ValueError, TypeError) as ex:
        raise DiffError(message='Ошибка при получении результирующего словаря: {}'.format(ex)) from ex


def get_identifiers_str(identifiers):
    """
    Формирует строку с идентификаторами

    :param identifiers:         идентификаторы

    :return:                    строка, содержащая идентификаторы
    """
    identifiers_str = ''
    for s in ('{}={}'.format(key, identifiers[key]) for key in identifiers):
        identifiers_str += ' ' + s
    return identifiers_str


@auth
def reset_changed(data_host, data_uri, *, auth_url=None, username=None, password=None, payload=None, cook=None):
    """
    Сбрасывает признак необходимости синхронизации у заявки или маршрута
    :param data_host:       хост сервера с данными
    :param data_uri:        URI данных
    :param auth_url:        URL сервиса авторизации
    :param username:        имя пользователя
    :param password:        пароль
    :param payload:         дополнительные параметры
    :param cook:            куки

    :return:                None
    """
    data_url = data_host + data_uri + '/reset_changed.json'
    try:
        resp = requests.post(data_url, data=payload, cookies=cook)
        if resp.status_code == 200:
            return resp.text
        else:
            raise WebError(data_url, 'Ошибка при выполнении HTTP-запроса, код: {}'.format(resp.status_code))

    except requests.exceptions.ConnectionError as ex:
        raise WebError(data_url, 'Ошибка при подключении к сервису. {}'.format(ex)) from ex
