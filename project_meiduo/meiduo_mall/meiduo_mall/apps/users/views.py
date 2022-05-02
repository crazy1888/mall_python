from django.shortcuts import render, redirect
from django.views import View
from django import http
from django.db import DatabaseError
import re
from django_redis import get_redis_connection
from django.contrib.auth import login,authenticate,logout
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import User
from meiduo_mall.utils.response_code import RETCODE
# Create your views here.

class UserInfoView(LoginRequiredMixin,View):
    """用户中心"""
    def get(self, request):
        """提供个人信息界面"""
        # if request.user.is_authenticated:
        #     return render(request,'user_center_info')
        # return redirect(reverse('users:login'))

        # login_url = 'login/'
        # redirect_field_name = 'redirect_to'

        #对应逻辑在LoginView

        return render(request, 'user_center_info.html')


class LogoutView(View):
    """用户退出登录"""
    def get(self,request):
        #清除状态保持信息
        logout(request)
        #退出登录后重定向到首页
        response = redirect(reverse('contents:index'))
        #删除cookie的用户名
        response.delete_cookie('username')  #对应LoginView的设置
        #响应结果
        return response


class MobileCountView(View):
    def get(self,request,mobile):
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','count':count})

class UsernameCountView(View):
    def get(self,request,username): #username从url获取接收
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','count':count})

class LoginView(View):
    """登录"""
    def get(self,request):
        return render(request,'login.html')

    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 校验参数
        # 判断参数是否齐全

        if not all([username,password]):
            return http.HttpResponseForbidden('缺少参数')

        # 判断用户名是否是5-20个字符
        if not re.match(r'[a-zA-Z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden('请输入正确的用户名或手机号')

        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')

        #认证用户，使用账号查询用户是否存在，如果存在，再校验密码是否正常
        user = authenticate(username=username,password=password)

        if user is None:
            return render(request,'login.html',{'account_errmsg':'用户名或密码错误'})

        # 实现状态保持
        login(request, user)
        # 设置状态保持的周期
        if remembered != 'on':
            # 没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
        else:
            # 记住用户：None表示两周后过期：默认是两周
            request.session.set_expiry(None)

        # 相应结果：重定向到首页
        next = request.GET.get('next')
        if next:
            #重定向到next
            response = redirect(next)
        else:
            #重定向到首页
            response = redirect(reverse('contents:index'))

        #为了实现首页的右上角展示用户名信息，我们需要将用户的缓存在cookie
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        # 响应登录结果
        # return redirect(reverse('contents:index'))
        return response


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

        #相应结果：重定向到首页
        response = redirect(reverse('contents:index'))

        # 为了实现首页的右上角展示用户名信息，我们需要将用户的缓存在cookie
        response.set_cookie('username',user.username,max_age=3600*24*15)

        return response