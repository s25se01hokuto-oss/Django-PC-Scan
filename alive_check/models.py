from django.db import models

class Seat(models.Model):
    TYPE_CHOICES = [
        ('seat', 'Seat'),
        ('aisle', 'Aisle'),
    ]
    STATUS_CHOICES = [
        ('alive', 'Alive'),
        ('dead', 'Dead'),
        ('unknown', 'Unknown'),
    ]

    row = models.IntegerField()
    col = models.IntegerField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unknown')
    last_checked = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['row', 'col']
        unique_together = ('row', 'col')

    def __str__(self):
        if self.type == 'seat':
            return f"Seat ({self.row}, {self.col}) - {self.ip_address or 'No IP'} ({self.status})"
        return f"Aisle ({self.row}, {self.col})"
