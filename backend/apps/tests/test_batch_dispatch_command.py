import csv
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from apps.charging.models import ChargingRequest, DispatchRecord


class RunBatchDispatchCommandTests(TestCase):
    def test_run_batch_dispatch_outputs_csv_and_rolls_back_data(self):
        stdout = StringIO()

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'batch_dispatch_result.csv'
            call_command('run_batch_dispatch', output=str(output_path), stdout=stdout)

            self.assertTrue(output_path.exists())
            with output_path.open('r', encoding='utf-8-sig', newline='') as file_obj:
                rows = list(csv.DictReader(file_obj))

        output = stdout.getvalue()
        self.assertIn('批量调度演示完成（数据库已自动回滚，文件输出已保留）', output)
        self.assertIn('终端仅输出两次批量调度的策略细节；完整时间线已写入 CSV。', output)
        self.assertIn('[第1批]', output)
        self.assertIn('[第2批]', output)
        self.assertIn('第1批总完成时长', output)
        self.assertIn('第2批总完成时长', output)
        self.assertIn('跨模式分配车辆：', output)
        self.assertIn('非 FIFO 排队证据：', output)
        self.assertRegex(output, r'V\d+\([FT]\) -> [FT]\d\[[FT]\]')
        self.assertGreater(len(rows), 10)
        self.assertEqual(set(rows[0].keys()), {'时刻', '事件', '快充1', '快充2', '慢充1', '慢充2', '慢充3', '等候区'})
        self.assertTrue(any('触发第1批批量调度' in row['事件'] for row in rows))
        self.assertTrue(any('触发第2批批量调度' in row['事件'] for row in rows))
        self.assertTrue(all(row['事件'] for row in rows if row['时刻']))
        self.assertEqual(ChargingRequest.objects.count(), 0)
        self.assertEqual(DispatchRecord.objects.count(), 0)
