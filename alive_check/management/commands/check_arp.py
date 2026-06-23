import subprocess
import re
from django.core.management.base import BaseCommand
from django.utils import timezone
from alive_check.models import Seat

class Command(BaseCommand):
    help = "Checks classroom host statuses via Linux ARP table and updates DB"

    def handle(self, *args, **options):
        # 1. Fetch current ARP cache
        try:
            result = subprocess.run(
                ["arp", "-an"],
                capture_output=True,
                text=True,
                check=True
            )
            arp_stdout = result.stdout
        except Exception as e:
            self.stderr.write(f"Failed to fetch ARP cache: {e}")
            return

        # 2. Extract active IPs with valid MACs
        active_ips = set()
        mac_pattern = r"(?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}"
        
        for line in arp_stdout.splitlines():
            # Extract IP inside parentheses, e.g. (192.168.203.14)
            ip_match = re.search(r"\(([\d\.]+)\)", line)
            if ip_match:
                ip = ip_match.group(1)
                is_incomplete = "<" in line or "incomplete" in line
                has_valid_mac = bool(re.search(mac_pattern, line))
                
                if not is_incomplete and has_valid_mac:
                    active_ips.add(ip)

        # 3. Update database entries
        seats = Seat.objects.filter(type='seat').exclude(ip_address__isnull=True)
        now = timezone.now()
        
        updated_count = 0
        for seat in seats:
            new_status = 'alive' if seat.ip_address in active_ips else 'dead'
            if seat.status != new_status or seat.last_checked is None:
                seat.status = new_status
                seat.last_checked = now
                seat.save(update_fields=['status', 'last_checked'])
                updated_count += 1
                
        self.stdout.write(self.style.SUCCESS(f"ARP status update completed. Updated {updated_count} seats."))
