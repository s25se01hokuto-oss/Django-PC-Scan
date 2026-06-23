import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classroom_ping.settings')
django.setup()

from alive_check.models import Seat

def seed():
    print("Clearing existing seats...")
    Seat.objects.all().delete()

    # Define a 5x7 grid (35 slots total) to match the layout:
    # Row 0: Aisle, Seat(PC1), Aisle, Aisle, Aisle, Aisle, Aisle
    # Row 1: Aisle, Seat(PC2), Aisle, Aisle, Aisle, Aisle, Aisle
    # Row 2: Aisle, Seat(PC3), Seat(PC4), Seat(PC5), Seat(PC6), Seat(PC7), Seat(PC8)
    # Row 3: Aisle, Aisle, Aisle, Aisle, Aisle, Aisle, Aisle
    # Row 4: Seat(PC9), Seat(PC10), Seat(PC11), Seat(PC12), Seat(PC13), Seat(PC14), Aisle
    layout = [
        ['aisle', 'seat',  'aisle', 'aisle', 'aisle', 'aisle', 'aisle'],  # Row 0
        ['aisle', 'seat',  'aisle', 'aisle', 'aisle', 'aisle', 'aisle'],  # Row 1
        ['aisle', 'seat',  'seat',  'seat',  'seat',  'seat',  'seat'],   # Row 2
        ['aisle', 'aisle', 'aisle', 'aisle', 'aisle', 'aisle', 'aisle'],  # Row 3
        ['seat',  'seat',  'seat',  'seat',  'seat',  'seat',  'aisle'],  # Row 4
    ]

    ips = [
        '127.0.0.1',  # PC1 - alive
        '192.0.2.1',  # PC2 - dead
        '127.0.0.1',  # PC3 - alive
        '127.0.0.1',  # PC4 - alive
        '192.0.2.2',  # PC5 - dead
        '127.0.0.1',  # PC6 - alive
        '192.0.2.3',  # PC7 - dead
        '127.0.0.1',  # PC8 - alive
        '127.0.0.1',  # PC9 - alive
        '192.0.2.4',  # PC10 - dead
        '127.0.0.1',  # PC11 - alive
        '192.0.2.5',  # PC12 - dead
        '127.0.0.1',  # PC13 - alive
        '192.0.2.6',  # PC14 - dead
    ]

    ip_index = 0
    seats_to_create = []

    for r_idx, row in enumerate(layout):
        for c_idx, slot_type in enumerate(row):
            ip = None
            if slot_type == 'seat':
                ip = ips[ip_index % len(ips)]
                ip_index += 1
            
            seats_to_create.append(
                Seat(
                    row=r_idx,
                    col=c_idx,
                    type=slot_type,
                    ip_address=ip
                )
            )

    # Bulk create for efficiency
    Seat.objects.bulk_create(seats_to_create)
    print(f"Successfully seeded {Seat.objects.count()} slots!")

if __name__ == '__main__':
    seed()

