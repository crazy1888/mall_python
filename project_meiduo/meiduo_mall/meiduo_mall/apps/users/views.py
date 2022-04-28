from django.shortcuts import render, redirect
from django.views import View
from django import http
from django.db import DatabaseError
import re
from django_redis import get_redis_connection

from .models import User
from django.urls import reverse
from django.contrib.auth import login
from meiduo_mall.utils.response_code import RETCODE
# Create your views here.

class MobileCountView(View):
    def get(self,request,mobile):
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','count':count})

class UsernameCountView(View):
    def get(self,request,username): #username从url获取接收
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','count':count})

class RegisterView(View):
    def get(self,request):
        #注册页面
        return render(request,'register.html')

    def post(self,request):
        #注册业务逻辑
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        allow = request.POST.get('allow')
        sms_code_client = request.POST.get('sms_code')

        #校验参数：前后端校验需要分开。避免恶意用户越过前端逻辑发请求。要保证后端安全，前后端校验逻辑相同。对应register.js的判断。
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')

        #验证码
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request,'register.html',{'sms_code_errmsg':'短信验证码已失效'})
        if sms_code_client != sms_code_server.decode():
            return render(request,'register.html',{'sms_code_errmsg':'输入短信验证码有误'})

        # 判断是否勾选用户协议
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # return render(request,'register.html',{'register_errmsg':'注册失败'}) #ceshi

        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:   #数据库注册失败
            return render(request,'register.html',{'register_errmsg':'注册失败'})

        #实现状态保持
        login(request,user)

        return redirect(reverse('contents:index'))