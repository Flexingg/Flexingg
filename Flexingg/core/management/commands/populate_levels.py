from decimal import Decimal, InvalidOperation, getcontext, ROUND_HALF_UP
from django.core.management.base import BaseCommand, CommandError

# Ensure reasonable Decimal precision
getcontext().prec = 18

class Command(BaseCommand):
    help = "Populate Level table with exponential XP requirements.\n\n" \
           "Formula: xp_required = base_xp * (growth_factor ** (level_number - 1)).\n" \
           "Example: python manage.py populate_levels --max-level 100 --base-xp 100 --growth-factor 1.1\n" \
           "Use --force to delete existing Level rows before populating."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-level",
            type=int,
            default=100,
            help="Maximum level to create (default: 100)"
        )
        parser.add_argument(
            "--base-xp",
            type=str,
            default="100",
            help="Base XP for level 1→2 (can be integer or decimal, default: 100)"
        )
        parser.add_argument(
            "--growth-factor",
            type=str,
            default="1.1",
            help="Exponential growth factor per level (default: 1.1)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="If set, delete existing Level rows before populating"
        )

    def handle(self, *args, **options):
        from core.models import Level

        max_level = options["max_level"]
        try:
            base_xp = Decimal(options["base_xp"])
            growth_factor = Decimal(options["growth_factor"])
        except (InvalidOperation, TypeError) as e:
            raise CommandError(f"Invalid numeric option provided: {e}")

        if max_level < 1:
            raise CommandError("max-level must be >= 1")

        if options["force"]:
            self.stdout.write("Deleting existing Level rows (force)...")
            Level.objects.all().delete()

        created = 0
        updated = 0

        for lvl in range(1, max_level + 1):
            # xp_required is cumulative XP required to reach this level number
            # Use integer rounding to nearest whole XP
            # Formula uses (level - 1) as exponent so level 1 => base_xp * (growth_factor ** 0) = base_xp
            exponent = lvl - 1
            xp_decimal = (base_xp * (growth_factor ** exponent)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            xp_required = int(xp_decimal)

            obj, created_flag = Level.objects.update_or_create(
                level_number=lvl,
                defaults={"xp_required": xp_required}
            )
            if created_flag:
                created += 1
            else:
                updated += 1
            if lvl % 10 == 0 or lvl == max_level:
                self.stdout.write(f"Processed level {lvl}: xp_required={xp_required}")

        self.stdout.write(self.style.SUCCESS(f"Levels processed: created={created} updated={updated} (max_level={max_level})"))