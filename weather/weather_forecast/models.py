import uuid

from django.db import models


class User(models.Model):
    """  """

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return str(self.user_id)


class SearchHistory(models.Model):
    """ История названий городов из успешных запросов пользователей """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    city_name = models.CharField(max_length=100)
    date_request = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'User: {self.user.user_id}, City: {self.city_name}'
