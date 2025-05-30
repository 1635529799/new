from django.shortcuts import render, redirect
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, login, authenticate
from .forms import LoginForm
# Create your views here.


def do_register(request):
    try:
        msg = ""
        if request.method == "GET":
            return render(request, "register.html", locals())
        if request.method == "POST":
            user = request.user
            datas = request.POST
            username = request.POST.get("username")
            password = request.POST.get("password")
            password2 = request.POST.get("password2")

            if len(username) < 6 or len(password) < 6 or len(password2) < 6:
                msg="账号密码必须大于6位"
                return render(request, "register.html", locals())
            if len(username) < 6 or len(password) < 6 or len(password2) < 6:
                msg="两次输入的密码不一致"
                return render(request, "register.html", locals())
            only = UserProfile.objects.filter(username=username)
            if len(only) > 0:
                msg = "用户名已经存在"
                return render(request, "register.html", locals())
            new_user = UserProfile()
            new_user.username = username
            new_user.set_password(password)

            new_user.mpassword = password
            new_user.save()
            return redirect("accounts:login")
        else:
            return render(request, "register.html", locals())
    except Exception as e:
        print(e)
        msg = "添加失败系统错误"
        return render(request, "register.html", locals())


def user_login(request):
    try:
        if request.user.is_authenticated:
            print("用户已登录，重定向到首页")
            return redirect("/")
        if request.method == 'POST':
            login_form = LoginForm(request.POST)
            print("表单是否有效：", login_form.is_valid())

            if login_form.is_valid():
                username = login_form.cleaned_data["username"]
                password = login_form.cleaned_data["password"]

                print(f"尝试登录：{username} / {password}")

                user = authenticate(username=username, password=password)

                if user is not None:
                    print("登录成功")
                    login(request, user)
                    return redirect("/")
                else:
                    errorinfo = "账号或密码不正确"
                    print("登录失败：", errorinfo)
                    return render(request, 'login.html', {
                        'login_form': login_form,
                        "errorinfo": errorinfo
                    })
            else:
                errorinfo = "账号或密码不正确或格式错误"
                print("表单校验失败：", errorinfo)
                return render(request, 'login.html', {
                    'login_form': login_form,
                    "errorinfo": errorinfo
                })
        else:
            print("GET 请求，返回登录页面")
            login_form = LoginForm()
            return render(request, 'login.html', {'login_form': login_form})
    except Exception as e:
        login_form = LoginForm()
        print("登录异常：", e)
        errorinfo = "系统错误"
        return render(request, 'login.html', {'login_form': login_form, "errorinfo": errorinfo})

@login_required
def user_logout(request):
    try:
        logout(request)
        request.session.clear()
        return redirect('accounts:login')
    except Exception as e:
        print(e)
    return render(request, "error.html", {"msg":"退出错误"})

