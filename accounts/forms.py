#coding:utf-8
from django import forms
from accounts.models import UserProfile
import re
import sys
import os

#登录表单
class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "用户名", "required": "required","id":"user","name":"username"}),
                              max_length=100,error_messages={"required": "username不能为空",})

    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "密码", "required": "required","id":"password","name":"password"}),
                              max_length=200,error_messages={"required": "password不能为空",})



