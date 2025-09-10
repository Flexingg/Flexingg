from django.db import models
from django.conf import settings

class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    from_user = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, related_name='friendship_creator_set')
    to_user = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, related_name='friend_request_set')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"

class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    user = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')

    def __str__(self):
        return f"{self.user.username} - {self.group.name} ({self.role})"

class Group(models.Model): 
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField() 
    creator = models.ForeignKey('core.UserProfile', on_delete=models.CASCADE, related_name='created_groups') 
    created_at = models.DateTimeField(auto_now_add=True) 
    members = models.ManyToManyField('core.UserProfile', through=GroupMembership, related_name='member_groups') 
     
    def __str__(self): 
        return self.name
