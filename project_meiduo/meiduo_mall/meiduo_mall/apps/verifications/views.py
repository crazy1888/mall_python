from django.shortcuts import render
from django.views import View
import random,logging
from django_redis import get_redis_connection
from django import http

from . import constants
from meiduo_mall.utils.response_code import RETCODE
from .libs.captcha.captcha import captcha
from verifications.libs.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import send_sms_code

# Create your views here.


#创建日志输出器
logger = logging.getLogger('django')


class SMSCodeView(View):
    # 短信验证码
    def get(self, request, mobile):
        # 提取参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        # 校验参数
        if not all([image_code_client, uuid]):
            return http.HttpResponseForbidden("缺少必要参数")

        #创建redis对象
        redis_conn = get_redis_connection('verify_code')

        # 判断用户是否频繁请求验证码
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        # 提取发送短信验证码的标记
        if send_flag:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR,'errmsg':'发送短信验证码过于频繁'})


        # 提取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        if image_code_server is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已失效'})

        # 删除图形验证码
        redis_conn.delete('img_%s' % uuid)

        # 对比图形码信息
        image_code_server = image_code_server.decode()  #将bytes转字符串，在比较
        if image_code_client.lower() != image_code_server.lower():  # 转小写
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码输入有误'})

        #生成短信验证码：随机生成6位数
        sms_code = '%06d' % random.randint(0,999999)
        logger.info(sms_code)   #手动输出日志，记录短信验证码

        #  # 保存短信验证码
        # redis_conn.setex('sms_%s' % mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        # #保存发送短信验证码的标记
        # redis_conn.setex('send_flag_%s' % mobile,constants.SEND_SMS_CODE_INTERVAL,1)

        #创建redis管道
        pl = redis_conn.pipeline()
        #将命令添加到队列中
        # 保存短信验证码
        pl.setex('sms_%s' % mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        #保存发送短信验证码的标记
        pl.setex('send_flag_%s' % mobile,constants.SEND_SMS_CODE_INTERVAL,1)
        #执行
        pl.execute()

        #发送
        #解耦出去，用celery
        # CCP().send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES // 60],constants.SEND_SMS_TEMPLATE_ID)
        #使用celery
        # send_sms_code(mobile,sms_code)      #错误
        send_sms_code.delay(mobile,sms_code)


        return http.JsonResponse({'code' : RETCODE.OK,'errmsg': '短信输入错误'})


class ImageCodeView(View):
    # "图形验证码"
    def get(self, request, uuid):
        # uuid：通用唯一标识码，用于唯一标识该图形验证码属于哪个用户的
        text, image = captcha.generate_captcha()  # 生成验证码
        # 保存图形验证码
        redis_conn = get_redis_connection('verify_code')    #对应dev的redis名称
        # redis_conn.setex('key','expires','value'   )
        redis_conn.setex('img_%s' % uuid, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        # 响应图片验证码
        return http.HttpResponse(image, content_type='image/jpg')

    def a(self, request):
        print(111)
