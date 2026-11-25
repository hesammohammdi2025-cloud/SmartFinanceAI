
import calendar

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from transactions.models import (
    Transaction,
    OrganizationTransaction,
    RecurringTransaction,
)


def calculate_next_date(current_date, frequency, start_date):

    if frequency == "daily":
        return current_date + timedelta(days=1)

    if frequency == "weekly":
        return current_date + timedelta(weeks=1)

    if frequency == "monthly":

        year = current_date.year
        month = current_date.month + 1

        if month > 12:
            month = 1
            year += 1

        last_day = calendar.monthrange(year, month)[1]

        day = min(start_date.day, last_day)

        return current_date.replace(
            year=year,
            month=month,
            day=day
        )

    if frequency == "yearly":

        year = current_date.year + 1

        last_day = calendar.monthrange(
            year,
            start_date.month
        )[1]

        day = min(start_date.day, last_day)

        return current_date.replace(
            year=year,
            month=start_date.month,
            day=day
        )

    raise ValueError(
        f"دوره تکرار نامعتبر است: {frequency}"
    )


class Command(BaseCommand):

    help = "پردازش و ثبت تراکنش‌های تکرارشونده"

    def handle(self, *args, **options):

        today = timezone.localdate()

        processed_count = 0
        processed_schedules_count = 0
        skipped_count = 0
        failed_count = 0
        deactivated_count = 0

        recurring_ids = list(
            RecurringTransaction.objects.filter(
                is_active=True,
                next_run_date__lte=today
            ).values_list("id", flat=True)
        )

        for recurring_id in recurring_ids:

            schedule_processed = False

            try:

                with db_transaction.atomic():

                    recurring = (
                        RecurringTransaction.objects
                        .select_for_update()
                        .filter(
                            id=recurring_id,
                            is_active=True,
                            next_run_date__lte=today
                        )
                        .first()
                    )

                    if recurring is None:
                        skipped_count += 1
                        continue

                    if (
                        recurring.end_date
                        and recurring.next_run_date > recurring.end_date
                    ):
                        recurring.is_active = False
                        recurring.save(
                            update_fields=[
                                "is_active",
                                "updated_at"
                            ]
                        )

                        deactivated_count += 1
                        continue

                    if not recurring.user_id and not recurring.organization_id:

                        recurring.is_active = False

                        recurring.save(
                            update_fields=[
                                "is_active",
                                "updated_at"
                            ]
                        )

                        failed_count += 1

                        self.stderr.write(
                            f"برنامه {recurring.id} مالک معتبری ندارد."
                        )

                        continue

                    while (
                        recurring.next_run_date <= today
                        and recurring.is_active
                    ):

                        run_date = recurring.next_run_date

                        if (
                            recurring.end_date
                            and run_date > recurring.end_date
                        ):
                            recurring.is_active = False
                            deactivated_count += 1
                            break

                        if recurring.user_id:

                            Transaction.objects.create(
                                user=recurring.user,
                                title=recurring.title,
                                amount=recurring.amount,
                                transaction_type=recurring.transaction_type,
                                category=recurring.category,
                                date=run_date,
                                description=recurring.description,
                            )

                        elif recurring.organization_id:

                            OrganizationTransaction.objects.create(
                                organization=recurring.organization,
                                created_by=recurring.created_by,
                                title=recurring.title,
                                amount=recurring.amount,
                                transaction_type=recurring.transaction_type,
                                category=recurring.category,
                                date=run_date,
                                description=recurring.description,
                            )

                        recurring.last_generated_date = run_date

                        next_date = calculate_next_date(
                            run_date,
                            recurring.frequency,
                            recurring.start_date
                        )

                        recurring.next_run_date = next_date

                        processed_count += 1
                        schedule_processed = True

                        if (
                            recurring.end_date
                            and next_date > recurring.end_date
                        ):
                            recurring.is_active = False
                            deactivated_count += 1
                            break

                    recurring.save()

                if schedule_processed:
                    processed_schedules_count += 1

            except Exception as error:

                failed_count += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"خطا در پردازش برنامه {recurring_id}: {error}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"تعداد تراکنش‌های ثبت‌شده: {processed_count}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"تعداد برنامه‌های پردازش‌شده: {processed_schedules_count}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"تعداد برنامه‌های ردشده: {skipped_count}"
            )
        )

        self.stdout.write(
            self.style.ERROR(
                f"تعداد برنامه‌های دارای خطا: {failed_count}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"تعداد برنامه‌های غیرفعال‌شده: {deactivated_count}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "پردازش تراکنش‌های تکرارشونده پایان یافت."
            )
        )
