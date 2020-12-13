import logging

import redis
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, render_to_response
from django.urls import reverse_lazy, reverse

from app.config.settings import AppSettings
from app.productdb.utils import login_required_if_login_only_mode
from django_project.celery import app as celery, TaskState, get_meta_data_for_task
from django_project import context_processors

logger = logging.getLogger("productdb")


def custom_page_not_found_view(request, exception):
    response = render(request, 'django_project/custom_404_page.html', {})
    response.status_code = 404
    return response


def custom_error_view(request):
    response = render(request, 'django_project/custom_500_page.html', {})
    response.status_code = 500
    return response


def custom_bad_request_view(request, exception):
    response = render(request, 'django_project/custom_400_page.html', {})
    response.status_code = 400
    return response


def custom_permission_denied_view(request, exception):
    response = render(request, 'django_project/custom_403_page.html', {})
    response.status_code = 403
    return response


def custom_csrf_failure_page(request, reason=""):
    context = {
        "message": "Form expired" if reason == "" else reason
    }
    return render_to_response('django_project/custom_csrf_failure_page.html', context)


class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    template_name = "django_project/change_password.html"
    success_url = reverse_lazy("custom_password_change_done")

    def get(self, request, *args, **kwargs):
        if context_processors.is_ldap_authenticated_user(request)["IS_LDAP_ACCOUNT"]:
            return HttpResponseForbidden("You're not allowed to change your password in this application")

        return super().get(request, *args, **kwargs)


@login_required
def custom_password_change_done(request):
    """thank you page with link to homepage"""
    # check if the request comes from an LDAP account, if so, raise a PermissionDenied exception
    if context_processors.is_ldap_authenticated_user(request)["IS_LDAP_ACCOUNT"]:
        return HttpResponseForbidden("You're not allowed to change your password in this application")

    else:
        return render(request, "django_project/password_change_done.html", context={})


def login_user(request):
    """login user
    :param request:
    :return:
    """
    app_config = AppSettings()
    context = {
        "login_only_mode": app_config.is_login_only_mode()
    }
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("productdb:home"))

    if request.GET:
        context["next"] = request.GET['next']

    else:
        context["next"] = None

    if request.method == 'POST':
        # authenticate user
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                if context["next"] and not context["next"].startswith("/productdb/login"):
                    return HttpResponseRedirect(context["next"])

                else:
                    return HttpResponseRedirect(reverse("productdb:home"))

            else:
                context["message"] = "User account was disabled.<br>Please contact the administrator."
        else:
            context["message"] = "Login failed, invalid credentials"

    return render(request, "django_project/login.html", context=context)


@login_required
def logout_user(request):
    """logout user
    :param request:
    :return:
    """
    if request.user.is_authenticated:
        logout(request)

    return redirect(reverse("login"))


def task_progress_view(request, task_id):
    """Progress view for an asynchronous task"""
    if login_required_if_login_only_mode(request):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

    default_title = "Please wait..."
    redirect_default = reverse("productdb:home")
    meta_data = get_meta_data_for_task(task_id)

    # title of the progress view
    if "title" in meta_data.keys():
        title = meta_data["title"]
    else:
        title = default_title

    # redirect after task is completed
    if "redirect_to" in meta_data.keys():
        redirect_to = meta_data["redirect_to"]
        auto_redirect = meta_data.get("auto_redirect", False)

    else:
        logger.warning("Cannot find redirect link to task meta data, use homepage")
        redirect_to = redirect_default
        auto_redirect = False

    context = {
        "task_id": task_id,
        "title": title,
        "redirect_to": redirect_to,
        "auto_redirect": auto_redirect
    }
    return render(request, "django_project/task_progress_view.html", context=context)


def task_status_ajax(request, task_id):
    """returns a JSON representation of the task state"""
    if settings.DEBUG:  # show results for task in debug mode
        valid_request = True
    else:
        valid_request = request.is_ajax()

    if valid_request:
        try:
            task = celery.AsyncResult(task_id)
            if task.state == TaskState.PENDING:
                response = {
                    "state": "pending",
                    "status_message": "try to start task"
                }

            elif task.state == TaskState.STARTED or task.state.lower() == TaskState.PROCESSING:
                response = {
                    "state": "processing",
                    "status_message": task.info.get("status_message", "")
                }

            elif task.state == TaskState.SUCCESS:
                response = {
                    "state": "success",
                    "status_message": task.info.get("status_message", "")
                }
                if "error_message" in task.info:
                    response["error_message"] = task.info["error_message"]

                if "data" in task.info:
                    response["data"] = task.info["data"]

            else:
                # something went wrong in the within the task
                response = {
                    "state": "failed",
                    "error_message": str(task.info),  # this is the exception that was raised
                }

        except redis.ConnectionError:
            logger.error("cannot get task update", exc_info=True)
            response = {
                "state": "failed",
                "error_message": "A server process (redis) is not running, please contact the administrator"
            }

        except Exception:  # catch any exception
            logger.error("cannot get task update", exc_info=True)
            response = {
                "state": "failed",
                "error_message": "Unknown error: " + str(task.info),  # this is the exception raised
            }
        logger.debug("task state for %s is\n%s" % (task_id, str(response)))

        return JsonResponse(response)

    else:
        return HttpResponse("Bad Request", status=400)
