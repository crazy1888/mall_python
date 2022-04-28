from celery import Celery

celery_app = Celery('meiduo')       #创建实例

#加载配置
celery_app.config_from_object('celery_tasks.config')

#注册任务
celery_app.autodiscover_tasks(['celery_tasks.sms'],)