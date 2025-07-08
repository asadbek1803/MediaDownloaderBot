from tortoise import fields, models

class User(models.Model):
    LANGUAGE_CHOICES = [
        ('uz', 'Uzbek'),
        ('ru', 'Russian'),
        ('en', 'English'),
    ]

    id = fields.IntField(pk=True)
    full_name = fields.CharField(max_length=100)
    telegram_id = fields.BigIntField(unique=True)
    username = fields.CharField(max_length=50, null=True)
    is_admin = fields.BooleanField(default=False)
    is_banned = fields.BooleanField(default=False)
    lang = fields.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='uz'
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.full_name} ({self.telegram_id})"


class Channels(models.Model):
    id = fields.IntField(pk=True)
    channel_username = fields.CharField(max_length = 120)
    channel_id = fields.BigIntField(unique=True)

    class Meta:
        table = "channels"