"""
演示严格批量调度两次触发过程并输出验收表格/CSV。

用法：
  python manage.py run_batch_dispatch
  python manage.py run_batch_dispatch --output batch_dispatch_result.csv
"""

from django.core.management.base import BaseCommand

from apps.operations.batch_dispatch_demo import BatchDispatchDemoService


class Command(BaseCommand):
    help = '演示严格 batch_min_total 两次批量调度过程（数据库自动回滚，CSV 保留）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='batch_dispatch_result.csv',
            help='导出 CSV 文件路径，默认 batch_dispatch_result.csv',
        )

    def handle(self, *args, **options):
        result = BatchDispatchDemoService.run()
        rows = result['rows']
        batch_reports = result['batch_reports']

        self.stdout.write(self.style.SUCCESS(
            '批量调度演示完成（数据库已自动回滚，文件输出已保留）'
        ))
        self.stdout.write('终端仅输出两次批量调度的策略细节；完整时间线已写入 CSV。')
        for report in batch_reports:
            self.stdout.write(
                f"\n[第{report['batch_no']}批] 触发时刻 {report['trigger_time']}，"
                f"充电区容量 {report['charging_area_capacity']}，总站内容量 {report['total_capacity']}"
            )
            self.stdout.write('  调度说明：忽略快慢模式与到达先后顺序，按总完成时长最短一次性确定本批车辆与桩位。')
            for entry in report['entries']:
                self.stdout.write(
                    f"  {entry['car_id']}({entry['request_mode']}) -> {entry['pile_no']}[{entry['pile_type']}] "
                    f"(位次 {entry['position']}，请求电量 {entry['request_amount']:.1f} 度，"
                    f"完成时长 {entry['completion_hours']:.4f} 小时)"
                )
            if report['cross_mode_entries']:
                self.stdout.write('  跨模式分配车辆：')
                for entry in report['cross_mode_entries']:
                    self.stdout.write(
                        f"    {entry['car_id']} 申请 {entry['request_mode']}，实际分配到 {entry['pile_no']}[{entry['pile_type']}]"
                    )
            if report['non_fifo_examples']:
                self.stdout.write('  非 FIFO 排队证据：')
                for example in report['non_fifo_examples']:
                    self.stdout.write(
                        f"    在 {example['pile_no']} 上，"
                        f"{example['ahead_car_id']}({example['ahead_mode']},到达序 {example['ahead_arrival_rank']}) "
                        f"排在 {example['behind_car_id']}({example['behind_mode']},到达序 {example['behind_arrival_rank']}) 前"
                    )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  第{report['batch_no']}批总完成时长：{float(report['total_completion_hours']):.4f} 小时"
                )
            )

        BatchDispatchDemoService.write_csv(options['output'], rows)
        self.stdout.write(self.style.SUCCESS(f'\n已导出 {options["output"]}'))
