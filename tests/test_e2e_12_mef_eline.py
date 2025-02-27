from datetime import datetime, timedelta
import json
import pytest
import requests
import time
from tests.helpers import NetworkTest

CONTROLLER = '127.0.0.1'
KYTOS_API = f'http://{CONTROLLER}:8181/api/kytos'


class TestE2EMefEline():
    net = None

    @classmethod
    def setup_class(cls):
        cls.net = NetworkTest(CONTROLLER)
        cls.net.start()

    @classmethod
    def teardown_class(cls):
        cls.net.stop()

    @pytest.fixture()
    def kytos_clean(self):
        self.net.restart_kytos_clean()

    @pytest.fixture()
    def circuit_id(self, kytos_clean):
        created_id = self._create_circuit()
        return created_id

    @pytest.fixture()
    def disabled_circuit_id(self, circuit_id):
        self._disable_circuit(circuit_id)
        time.sleep(2)
        return circuit_id    

    def _circuit_exists(self, circuit_id):
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{circuit_id}'
        response = requests.get(api_url)
        return response.status_code == 200

    def _create_circuit(self):
        payload = {
            "name": "my evc1",
            "enabled": False,
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:01:2",
            }
        }
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/'
        response = requests.post(api_url, json=payload)
        assert response.status_code == 201

        data = response.json()

        # wait circuit to be created
        while not self._circuit_exists(data.get('circuit_id')):
            time.sleep(1)

        return data.get('circuit_id')

    # Disable circuit
    def _disable_circuit(self, circuit_id):
        payload = {
            "enable": False,
        }
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{circuit_id}'
        response = requests.patch(api_url, json=payload)

        assert response.status_code == 200
        
        return 

    def test_create_schedule_by_frequency(self, disabled_circuit_id):
        """ Test scheduler creation to enable the circuit by frequency, 
            every minute. """

        # Schedule by frequency every minute
        payload = {
              "circuit_id":disabled_circuit_id,
              "schedule": {
                "frequency": "* * * * *"
              }
            }

        # verify if the circuit is really disabled
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{disabled_circuit_id}'
        response = requests.get(api_url)
        json = response.json() 
        assert json.get("enabled") == False

        # create circuit schedule
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule'
        response = requests.post(api_url, json=payload)
        assert response.status_code == 201  
        
        # waiting some time to trigger the scheduler
        time.sleep(62)

        # Verify if the circuit is enabled 
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{disabled_circuit_id}'
        response = requests.get(api_url)
        assert response.status_code == 200

        json = response.json() 
        assert json.get("enabled") == True
        
        scheduler_frq = json.get("circuit_scheduler")[0].get("frequency")
        payload_frq = payload.get("schedule").get("frequency")
        assert scheduler_frq is not None
        assert payload_frq == scheduler_frq

    def test_create_schedule_by_date(self, disabled_circuit_id):
        """ Test scheduler creation to enable the circuit by date, 
            after one minute. """

        # Schedule by date to next minute
        ts = datetime.now() + timedelta(seconds=60)
        schedule_time = ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        payload = {
              "circuit_id":disabled_circuit_id,
              "schedule": {
                "date": schedule_time
              }
            }

        # verify if the circuit is really disabled
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{disabled_circuit_id}'
        response = requests.get(api_url)
        json = response.json() 
        assert json.get("enabled") == False

        # create circuit schedule
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule'
        response = requests.post(api_url, json=payload)
        assert response.status_code == 201  
        
        # waiting some time to trigger the scheduler
        time.sleep(62)

        # Verify if the circuit is enabled 
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{disabled_circuit_id}'
        response = requests.get(api_url)
        assert response.status_code == 200

        json = response.json() 
        assert json.get("enabled") == True

        scheduler_date = json.get("circuit_scheduler")[0].get("date")
        payload_date = payload.get("schedule").get("date")
        assert payload_date == scheduler_date
     
    def test_delete_schedule(self, circuit_id):
        """ Test to delete a scheduler. """

        # Schedule by frequency every minute
        payload = {
              "circuit_id":circuit_id,
              "schedule": {
                "frequency": "* * * * *"
              }
            }

        # create circuit schedule
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule'
        response = requests.post(api_url, json=payload)
        assert response.status_code == 201

        # Recover schedule id created
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{circuit_id}'
        response = requests.get(api_url)
        json = response.json()
        schedule_id = json.get("circuit_scheduler")[0].get("id")

        # delete circuit schedule
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule/{schedule_id}'
        response = requests.delete(api_url)
        assert response.status_code == 200

        # Verify if the circuit schedule does not exist
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule/{schedule_id}'
        response = requests.get(api_url)
        assert response.status_code == 405

    def test_patch_schedule(self, disabled_circuit_id):
        """ Test to modify a scheduler and enable a circuit 
            after one minute """

        # Schedule by frequency every hour
        payload = {
              "circuit_id":disabled_circuit_id,
              "schedule": {
                "frequency": "* 1 * * *"
              }
            }

        # create circuit schedule
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule'
        response = requests.post(api_url, json=payload)
        json = response.json()
        assert response.status_code == 201

        # Get schedule ID
        schedule_id = json.get("id")

        # verify if the circuit is really disabled
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{disabled_circuit_id}'
        response = requests.get(api_url)
        json = response.json()
        assert json.get("enabled") == False

        # Schedule by frequency every minute
        payload = {
            "frequency": "* * * * *"
        }

        # patch circuit schedule
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/schedule/{schedule_id}'
        response = requests.patch(api_url, json=payload)
        assert response.status_code == 200

        # waiting to trigger the scheduler
        time.sleep(62)

        # Verify if the circuit is enabled
        api_url = f'{KYTOS_API}/mef_eline/v2/evc/{disabled_circuit_id}'
        response = requests.get(api_url)
        json = response.json()

        assert response.status_code == 200
        assert json.get("enabled") == True

        frequency = json.get("circuit_scheduler")[0].get("frequency")
        assert payload.get("frequency") == frequency
