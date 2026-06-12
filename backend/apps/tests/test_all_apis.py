import json
from datetime import date

from django.core.management import call_command
from django.test import Client, TestCase

from apps.common.enums import ErrorCode, RequestStatus
from apps.station.models import ChargingPile, SystemConfig


class AllAPITestCase(TestCase):
    """覆盖全部 REST 接口的集成测试。"""

    @classmethod
    def setUpTestData(cls):
        call_command('init_system')

    def setUp(self):
        self.client = Client()

    def _json(self, response):
        return json.loads(response.content.decode('utf-8'))

    def _request(self, method, path, data=None, token=None):
        headers = {'content_type': 'application/json'}
        if token:
            headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        body = json.dumps(data) if data is not None else ''
        return getattr(self.client, method.lower())(path, data=body, **headers)

    def _assert_ok(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        payload = self._json(response)
        self.assertEqual(payload['code'], ErrorCode.SUCCESS, payload)
        return payload['data']

    def _register_user(self, car_id='TEST-CAR-01', password='123456'):
        data = self._assert_ok(self._request(
            'post', '/api/auth/register',
            {'car_id': car_id, 'user_name': '测试用户', 'car_capacity': 60, 'password': password},
        ))
        self.assertIn('access_token', data)
        return data['access_token']

    def _login_user(self, car_id='TEST-CAR-01', password='123456'):
        data = self._assert_ok(self._request(
            'post', '/api/auth/login', {'car_id': car_id, 'password': password},
        ))
        return data['access_token']

    def _login_admin(self):
        data = self._assert_ok(self._request(
            'post', '/api/auth/login', {'car_id': 'A077379', 'password': '123456'},
        ))
        self.assertEqual(data['role'], 'admin')
        return data['access_token']

    def _pause_dispatch(self):
        config = SystemConfig.objects.filter(is_active=True).first()
        config.waiting_dispatch_paused = True
        config.save(update_fields=['waiting_dispatch_paused'])

    # ---- 认证 ----

    def test_auth_register_and_login(self):
        token = self._register_user('TEST-AUTH-01')
        self.assertTrue(token)
        token2 = self._login_user('TEST-AUTH-01')
        self.assertTrue(token2)

    def test_auth_login_admin(self):
        token = self._login_admin()
        self.assertTrue(token)

    def test_auth_login_invalid_user(self):
        response = self._request('post', '/api/auth/login', {'car_id': 'NOBODY', 'password': '123456'})
        payload = self._json(response)
        self.assertEqual(payload['code'], ErrorCode.USER_NOT_FOUND)

    # ---- 管理员：系统配置 / 充电桩 ----

    def test_admin_system_config(self):
        admin_token = self._login_admin()
        config = self._assert_ok(self._request('get', '/api/admin/system-config', token=admin_token))
        self.assertEqual(config['fast_pile_num'], 2)
        self.assertEqual(config['slow_pile_num'], 3)

        updated = self._assert_ok(self._request(
            'put', '/api/admin/system-config',
            {'charging_queue_len': 3, 'waiting_area_size': 10},
            token=admin_token,
        ))
        self.assertEqual(updated['charging_queue_len'], 3)

    def test_admin_pile_status(self):
        admin_token = self._login_admin()
        piles = self._assert_ok(self._request('get', '/api/pile/status', token=admin_token))
        self.assertEqual(len(piles), 5)

    def test_admin_pile_lifecycle(self):
        admin_token = self._login_admin()
        pile = ChargingPile.objects.filter(pile_no='T3').first()
        self.assertIsNotNone(pile)

        self._assert_ok(self._request('post', f'/api/pile/{pile.id}/poweroff', token=admin_token))
        self._assert_ok(self._request('post', f'/api/pile/{pile.id}/poweron', token=admin_token))
        data = self._assert_ok(self._request('post', f'/api/pile/{pile.id}/start', token=admin_token))
        self.assertIn(data['status'], {'available', 'standby'})

    # ---- 用户：充电全流程 + 账单 ----

    def test_user_charging_billing_flow(self):
        self._register_user('TEST-FLOW-01')
        user_token = self._login_user('TEST-FLOW-01')

        req = self._assert_ok(self._request(
            'post', '/api/charging/request',
            {'request_mode': 'F', 'request_amount': 20},
            token=user_token,
        ))
        self.assertIn(req['status'], {RequestStatus.QUEUING, RequestStatus.DISPATCHED})
        pile_id = req.get('pile_id')

        queue = self._assert_ok(self._request('get', '/api/charging/queue-status', token=user_token))
        self.assertTrue(queue['has_request'])

        if req['status'] == RequestStatus.DISPATCHED and pile_id:
            self._assert_ok(self._request(
                'post', '/api/charging/start', {'pile_id': pile_id}, token=user_token,
            ))
            status = self._assert_ok(self._request('get', '/api/charging/status', token=user_token))
            self.assertEqual(status['status'], RequestStatus.CHARGING)

            end_data = self._assert_ok(self._request('post', '/api/charging/end', token=user_token))
            self.assertIn('bill_id', end_data)

            bills = self._assert_ok(self._request('get', '/api/bill/list', token=user_token))
            self.assertGreaterEqual(len(bills), 1)
            bill_id = bills[0]['bill_id']

            detail = self._assert_ok(self._request('get', f'/api/bill/detail/{bill_id}', token=user_token))
            self.assertGreaterEqual(len(detail['details']), 1)

            pay = self._assert_ok(self._request('post', f'/api/bill/pay/{bill_id}', token=user_token))
            self.assertEqual(pay['pay_status'], 'paid')

    def test_user_update_amount_and_mode_in_waiting_area(self):
        self._register_user('TEST-MODIFY-01')
        user_token = self._login_user('TEST-MODIFY-01')
        self._pause_dispatch()

        req = self._assert_ok(self._request(
            'post', '/api/charging/request',
            {'request_mode': 'F', 'request_amount': 20},
            token=user_token,
        ))
        self.assertEqual(req['status'], RequestStatus.QUEUING)

        updated = self._assert_ok(self._request(
            'put', '/api/charging/amount', {'amount': 25}, token=user_token,
        ))
        self.assertEqual(updated['request_amount'], 25.0)
        self.assertEqual(updated['queue_num'], req['queue_num'])

        mode_changed = self._assert_ok(self._request(
            'put', '/api/charging/mode', {'mode': 'T'}, token=user_token,
        ))
        self.assertEqual(mode_changed['request_mode'], 'T')
        self.assertNotEqual(mode_changed['queue_num'], req['queue_num'])

        self._assert_ok(self._request('delete', '/api/charging/cancel', token=user_token))

    def test_user_cancel_while_queuing(self):
        self._register_user('TEST-CANCEL-01')
        user_token = self._login_user('TEST-CANCEL-01')
        self._pause_dispatch()

        self._assert_ok(self._request(
            'post', '/api/charging/request',
            {'request_mode': 'T', 'request_amount': 10},
            token=user_token,
        ))
        data = self._assert_ok(self._request('delete', '/api/charging/cancel', token=user_token))
        self.assertEqual(data['status'], RequestStatus.CANCELLED)

    # ---- 管理员：队列 / 故障 / 报表 ----

    def test_admin_pile_queue(self):
        admin_token = self._login_admin()
        pile = ChargingPile.objects.first()
        data = self._assert_ok(self._request('get', f'/api/queue/pile/{pile.id}', token=admin_token))
        self.assertEqual(data['pile_id'], pile.id)
        self.assertIn('queue', data)

    def test_admin_fault_and_recover(self):
        admin_token = self._login_admin()
        pile = ChargingPile.objects.filter(pile_no='F2').first()

        report = self._assert_ok(self._request(
            'post', '/api/admin/fault/report', {'pile_id': pile.id}, token=admin_token,
        ))
        self.assertIn('fault_id', report)

        faults = self._assert_ok(self._request('get', '/api/admin/fault/list', token=admin_token))
        self.assertGreaterEqual(len(faults), 1)

        recover = self._assert_ok(self._request(
            'post', '/api/admin/fault/recover', {'pile_id': pile.id}, token=admin_token,
        ))
        self.assertEqual(recover['pile_id'], pile.id)

    def test_admin_report_stats(self):
        admin_token = self._login_admin()
        today = date.today().isoformat()
        data = self._assert_ok(self._request(
            'get', f'/api/admin/report/stats?period=day&date={today}', token=admin_token,
        ))
        self.assertEqual(data['period'], 'day')
        self.assertEqual(len(data['items']), 5)

    # ---- 权限校验 ----

    def test_auth_required_and_permission(self):
        response = self._request('get', '/api/charging/queue-status')
        self.assertEqual(self._json(response)['code'], ErrorCode.AUTH_ERROR)

        user_token = self._register_user('TEST-PERM-01')
        response = self._request('get', '/api/admin/system-config', token=user_token)
        self.assertEqual(self._json(response)['code'], ErrorCode.PERMISSION_ERROR)
