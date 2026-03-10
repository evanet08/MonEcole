
from django.shortcuts import render,redirect,get_object_or_404
from MonEcole_app.forms.form_imports import  *
from MonEcole_app.models.models_import import *
from django.http import JsonResponse
import json
from django.contrib import messages
from datetime import datetime
from MonEcole_app.views.home.home import get_user_info
from django.contrib.auth.decorators import login_required
from MonEcole_app.views.decorators.decorators import  module_required
from MonEcole_app.views.tools.tenant_utils import (
    tenant_etablissement_filter, get_tenant_campus_ids,
    deny_cross_tenant_access, validate_campus_access
)
