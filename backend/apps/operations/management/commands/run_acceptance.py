"""
按作业验收用例自动执行事件并输出填表快照。

用法：
  python manage.py run_acceptance              # 真实节奏：事件间隔 30 秒
  python manage.py run_acceptance --fast       # 快速模式：不等待
  python manage.py run_acceptance --until 09:30 # 执行到指定时刻（默认 09:30）
  python manage.py run_acceptance --output result.csv
  python manage.py run_acceptance --snapshot-only  # 仅输出当前快照
"""

import csv
import time

from django.core.management.base import BaseCommand

from apps.common.sim_clock import disable, enable, make_case_time
from apps.operations.acceptance_events import ACCEPTANCE_EVENTS, PILE_COLUMNS
from apps.operations.acceptance_service import AcceptanceService


class Command(BaseCommand):
    help = '按作业验收用例自动执行事件（比例尺 1:10 虚拟时钟）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fast', action='store_true',
            help='快速模式，事件间不等待真实 30 秒',
        )
        parser.add_argument(
            '--interval', type=float, default=30.0,
            help='真实事件间隔秒数（默认 30）',
        )
        parser.add_argument(
            '--until', type=str, default='09:30',
            help='执行到该用例时刻（含），默认 09:30',
        )
        parser.add_argument(
            '--output', type=str, default='',
            help='将快照表格导出为 CSV 文件',
        )
        parser.add_argument(
            '--no-reset', action='store_true',
            help='不重置环境（在现有数据上继续）',
        )
        parser.add_argument(
            '--snapshot-only', action='store_true',
            help='仅打印当前验收快照，不执行事件',
        )

    def handle(self, *args, **options):
        try:
            if options['snapshot_only']:
                snap = AcceptanceService.build_snapshot()
                self._print_snapshot(snap, event='(快照)')
                return

            if not options['no_reset']:
                self.stdout.write('正在重置验收环境…')
                AcceptanceService.reset_environment()

            enable(make_case_time(6, 0))
            self.stdout.write(self.style.SUCCESS(
                '模拟时钟已开启，起始时刻 06:00（比例尺 1:10）'
            ))

            events = AcceptanceService.filter_events(options['until'])
            rows = []

            # 输出表头
            header = ['时刻', '事件', '快充1', '快充2', '慢充1', '慢充2', '慢充3', '等候区']
            self.stdout.write('\n' + '\t'.join(header))

            for idx, (case_time, event) in enumerate(events):
                if idx > 0 and not options['fast']:
                    time.sleep(options['interval'])

                event_str = self._format_event(event)
                snap = AcceptanceService.run(case_time, event, event_str)
                if event[0] == 'A' and event[2] in ('F', 'T') and snap.get('request_rejected'):
                    self.stdout.write(self.style.WARNING(
                        f'  → {event[1]} 到达被拒：{snap["request_rejected"]}'
                    ))
                if snap.get('validation_errors'):
                    for err in snap['validation_errors']:
                        self.stderr.write(self.style.ERROR(
                            f'快照校验失败 [{case_time}]: {err}'
                        ))
                    raise SystemExit(1)
                for sub_idx, row in enumerate(snap['table_rows']):
                    csv_row = {**row, '事件': event_str if sub_idx == 0 else ''}
                    rows.append(csv_row)
                    line = '\t'.join([
                        row['时刻'],
                        event_str if sub_idx == 0 else '',
                        row['快充1'],
                        row['快充2'],
                        row['慢充1'],
                        row['慢充2'],
                        row['慢充3'],
                        row['等候区'],
                    ])
                    self.stdout.write(line)

            if options['output']:
                self._write_csv(options['output'], rows)
                self.stdout.write(self.style.SUCCESS(f'\n已导出 {options["output"]}'))

            self.stdout.write(self.style.SUCCESS(
                f'\n验收执行完成，共 {len(events)} 条事件。'
            ))

        finally:
            disable()
            self.stdout.write('模拟时钟已关闭。')

    def _format_event(self, event):
        return '(' + ','.join(str(x) for x in event) + ')'

    def _print_snapshot(self, snap, event=''):
        for sub_idx, row in enumerate(snap.get('table_rows', [snap.get('table_row', {})])):
            self.stdout.write('\t'.join([
                row.get('时刻', '-'),
                event if sub_idx == 0 else '',
                row.get('快充1', '-'), row.get('快充2', '-'),
                row.get('慢充1', '-'), row.get('慢充2', '-'), row.get('慢充3', '-'),
                row.get('等候区', '-'),
            ]))

    def _write_csv(self, path, rows):
        fieldnames = ['时刻', '事件', '快充1', '快充2', '慢充1', '慢充2', '慢充3', '等候区']
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, '') for k in fieldnames})
