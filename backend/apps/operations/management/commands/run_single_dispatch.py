"""
固定场景的单次调度演示命令。

用法：
  python manage.py run_single_dispatch
  python manage.py run_single_dispatch --settings=config.settings.test
"""

from django.core.management.base import BaseCommand

from apps.operations.single_dispatch_demo import SingleDispatchDemoService


class Command(BaseCommand):
    help = '演示单次调度场景并输出本次调度结果（运行后自动回滚，不污染正式环境）'

    def handle(self, *args, **options):
        result = SingleDispatchDemoService.run()

        self.stdout.write(self.style.SUCCESS('单次调度场景执行完成（已自动回滚，不影响正式环境）'))
        self.stdout.write(f"调度模式：{result['dispatch_mode']}")
        self.stdout.write(f"每桩总容量：{result['charging_queue_len']}（当前每桩已有 1 辆在充，因此本轮各桩可进入 2 辆）")

        self.stdout.write('\n[快充结果]')
        for pile_result in result['fast_results']:
            self._print_pile_result(pile_result)

        self.stdout.write('\n[慢充结果]')
        for pile_result in result['slow_results']:
            self._print_pile_result(pile_result)

        self.stdout.write('\n[未进入本轮调度的等候区车辆]')
        self.stdout.write('快充：' + self._format_waiting(result['remaining_fast_waiting']))
        self.stdout.write('慢充：' + self._format_waiting(result['remaining_slow_waiting']))

        self.stdout.write('\n[汇总]')
        self.stdout.write(f"快充本轮总完成时长：{result['fast_total_completion_hours']:.4f} 小时")
        self.stdout.write(f"慢充本轮总完成时长：{result['slow_total_completion_hours']:.4f} 小时")
        self.stdout.write(self.style.SUCCESS(
            f"本次调度总完成时长：{result['total_completion_hours']:.4f} 小时"
        ))

    def _print_pile_result(self, pile_result):
        current_car = pile_result['current_car']
        if current_car:
            self.stdout.write(
                f"- {pile_result['pile_no']}：当前在充 {current_car['plate_no']}，"
                f"剩余 {current_car['remaining_amount']:.1f} 度，"
                f"剩余 {current_car['remaining_hours']:.4f} 小时"
            )
        else:
            self.stdout.write(f"- {pile_result['pile_no']}：当前无在充车辆")

        if not pile_result['entries']:
            self.stdout.write('  本轮无车辆进入该桩队列')
            return

        self.stdout.write('  本轮调度结果：')
        for entry in pile_result['entries']:
            self.stdout.write(
                f"    {entry['label']} -> {pile_result['pile_no']} "
                f"(排队位次 {entry['queue_position']}，"
                f"请求电量 {entry['request_amount']:.1f} 度，"
                f"完成时长 {entry['completion_hours']:.4f} 小时)"
            )

    def _format_waiting(self, items):
        if not items:
            return '无'
        return '，'.join(
            f"{item['label']}({item['request_amount']:.1f}度)"
            for item in items
        )
