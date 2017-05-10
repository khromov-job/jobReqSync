#!/usr/bin/python
#-*- coding:utf-8 -*-

import unittest
import os
import json
from request_sync import utils


class Setup(unittest.TestCase):

    def setUp(self):
        self.data = {'regions': [{'sensors': [{'name': 'Moscow', 'date': '14.01.17'},
                                              {'plcs': [1, 2, {'format_id': None, 'plc_id': 1}]}]}]}
        self.res_del_keys = {'regions': [{'sensors': [{'date': '14.01.17'}, {'plcs': [1, 2]}]}]}
        self.pth_txt = "['regions'][0]['sensors'][1]['plcs'][2]['format_id']"
        self.pth_parsed = ['regions', 0, 'sensors', 1, 'plcs', 2, 'format_id']
        self.rec_value = 19
        self.rec_res = {'regions': [{'sensors': [{'name': 'Moscow', 'date': '14.01.17'},
                                                 {'plcs': [1, 2, {'format_id': 19, 'plc_id': 1}]}]}]}

        self.req_deleted_keys = ["source_id", "format_id", "plc_id", "band_id", "user_id", "operator_id",
                                 "status_id", "platform_id", "delivery_method_id", "sensor_id", "plc_id",
                                 "format_id", "band_id", "station_id", 'metadata_id', 'is_changed']

        self.req_ident_keys = ["uuid", "regions", "sensors", "sensor_uuid", "plcs", "plc_uuid", "format_uuid",
                               "srs_id", "bands", "band_uuid", "routes", "metadata_identifier", "stations",
                               "station_uuid", "id"]

        self.route_del_keys = ['request_region_id', 'metadata_id', 'cloudiness_percent', 'linked_by', 'is_changed']

        self.route_ident_keys = ['id', 'request_region_uuid', 'metadata_identifier']

        src_pth = os.path.dirname(os.path.dirname(__file__)) + '/tests/json_dumps_new.txt'
        tar_pth = os.path.dirname(os.path.dirname(__file__)) + '/tests/json_dumps_old.txt'
        res_req_pth = os.path.dirname(os.path.dirname(__file__)) + '/tests/result_request.txt'
        res_route_pth = os.path.dirname(os.path.dirname(__file__)) + '/tests/result_route.txt'
        res_prep_pth = os.path.dirname(os.path.dirname(__file__)) + '/tests/result_preprocess.txt'
        res_postp_pth = os.path.dirname(os.path.dirname(__file__)) + '/tests/result_postprocess.txt'

        with open(src_pth, 'r') as f:
            self.req_new = json.loads(f.read())
        with open(tar_pth, 'r') as f:
            self.req_old = json.loads(f.read())
        with open(res_req_pth, 'r') as f:
            self.res_req = json.loads(f.read())
        with open(res_route_pth, 'r') as f:
            self.res_route = json.loads(f.read())
        with open(res_prep_pth, 'r') as f:
            self.result_prep = json.loads(f.read())
        with open(res_postp_pth, 'r') as f:
            self.result_postp = json.loads(f.read())


class TestSubFuncs(Setup, unittest.TestCase):

    def test_delete_keys(self):
        delete_res = utils.delete_keys(self.data, ['name', 'plc_id', 'format_id'])
        self.assertEqual(delete_res, self.res_del_keys)

    def test_sift_keys(self):
        sift_res = utils.sift_keys(self.data, ['regions', 'sensors', 'date', 'plcs'])
        self.assertEqual(sift_res, self.res_del_keys)

    def test_parse_path(self):
        parse_res = utils.parse_path(self.pth_txt)
        self.assertEqual(parse_res, self.pth_parsed)

    def test_recursive_set(self):
        utils.recursive_set(self.data, self.pth_parsed, self.rec_value)
        self.assertEqual(self.data, self.rec_res)

    def test_preprocess(self):
        prep = utils.pre_process(self.req_new['request'])
        self.assertEqual(prep, self.result_prep)

    # def test_postprocess(self):
    #     postp = utils.post_process(self.result_prep)
    #     self.assertEqual(postp, self.result_postp)


class TestResultDict(Setup, unittest.TestCase):

    def test_res_req(self):
        diff = utils.get_result_dict(self.req_new["request"], self.req_old["request"], self.req_deleted_keys,
                                     self.req_ident_keys, data_type="REQUEST")
        res_req = utils.pre_process(diff)
        self.assertEqual(res_req, self.res_req)

    def test_res_route(self):
        diff = utils.get_result_dict(self.req_new["route"], self.req_old["route"], self.route_del_keys,
                                     self.route_ident_keys, data_type="ROUTE")
        self.assertEqual(diff, self.res_route)


if __name__ == "__main__":
    unittest.main()
