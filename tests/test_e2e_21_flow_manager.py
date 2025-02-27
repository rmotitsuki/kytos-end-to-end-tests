import json
import pytest
import requests
from tests.helpers import NetworkTest
import os
import time
import re

CONTROLLER = '127.0.0.1'
KYTOS_API = 'http://%s:8181/api/kytos' % CONTROLLER

class TestE2EFlowManager:
    net = None

    @classmethod
    def setup_class(cls):
        cls.net = NetworkTest(CONTROLLER)
        cls.net.start()
        cls.net.wait_switches_connect()

    @classmethod
    def teardown_class(cls):
        cls.net.stop()

    def test_030_restart_kytos_should_preserve_flows(self):
        """Test if, after kytos restart, the flows are preserved on the switch
           flow table."""
        self.net.restart_kytos_clean()
        time.sleep(5)

        payload = {
            "flows": [
                {
                "priority": 10,
                "match": {
                    "in_port": 1,
                    "dl_vlan": 999
                },
                "actions": [
                    {
                    "action_type": "output",
                    "port": 2
                    }
                ]
                }
            ]
        }

        api_url = KYTOS_API + '/flow_manager/v2/flows/00:00:00:00:00:00:00:01'
        response = requests.post(api_url, data=json.dumps(payload), 
                                 headers={'Content-type': 'application/json'})
        assert response.status_code == 200
        data = response.json()
        assert 'FlowMod Messages Sent' in data['response']

        # wait for the flow to be installed
        wait_time = 20
        time.sleep(wait_time)

        # restart controller keeping configuration
        t1 = time.time()
        self.net.start_controller()
        self.net.wait_switches_connect()
        delta = time.time() - t1

        # wait for the flow to be installed
        time.sleep(wait_time)
        wait_time += wait_time

        s1 = self.net.net.get('s1')
        flows_s1 = s1.dpctl('dump-flows')
        assert len(flows_s1.split('\r\n ')) == 2
        for flow in flows_s1.split('\r\n '):
            match = re.search("duration=([0-9.]+)", flow)
            duration = float(match.group(1))
            assert duration >= wait_time + delta

    def test_031_on_switch_restart_kytos_should_recreate_flows(self):
        """Test if, after kytos restart, the flows are preserved on the switch 
           flow table."""
        self.net.restart_kytos_clean()
        time.sleep(5)

        payload = {
            "flows": [
                {
                "priority": 10,
                "match": {
                    "in_port": 1,
                    "dl_vlan": 999
                },
                "actions": [
                    {
                    "action_type": "output",
                    "port": 2
                    }
                ]
                }
            ]
        }

        api_url = KYTOS_API + '/flow_manager/v2/flows/00:00:00:00:00:00:00:01'
        response = requests.post(api_url, data=json.dumps(payload), 
                                 headers={'Content-type': 'application/json'})
        assert response.status_code == 200
        data = response.json()
        assert 'FlowMod Messages Sent' in data['response']

        # wait for the flow to be installed
        time.sleep(20)

        # OVS does not have a way to actually restart the switch
        # so to simulate that, we just delete all flows
        s1 = self.net.net.get('s1')
        s1.dpctl('del-flows')

        # wait for the flow to be installed
        time.sleep(20)

        flows_s1 = s1.dpctl('dump-flows')
        assert len(flows_s1.split('\r\n ')) == 2
        assert 'dl_vlan=999' in flows_s1
