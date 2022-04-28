from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.

class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')   #手机号码设置了唯一，相同的注册会出错

    class Meta:
        db_table = 'tb_user'  # 自定义表名
        verbose_name = '用户'
        verbose_name_plural = verbose_name  # 复数

    def __str__(self):
        return self.username
