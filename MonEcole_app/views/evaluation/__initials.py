
from django.http import HttpResponse
from MonEcole_app.models.models_import import *
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph,PageBreak
from io import BytesIO
from reportlab.platypus import Image  
from reportlab.platypus import Spacer, HRFlowable
from django.utils.text import slugify
from django.shortcuts import render,redirect
from MonEcole_app.views.home.home import get_user_info
from django.contrib import messages
from reportlab.platypus import Paragraph, Image, Table, Spacer, KeepTogether, HRFlowable, SimpleDocTemplate, PageBreak, Flowable
from MonEcole_app.forms.evaluation_form import EvaluationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from MonEcole_app.forms.form_imports import *
from MonEcole_app.models.models_import import Eleve_inscription,Eleve
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import io
import openpyxl
from openpyxl.styles import Font
from django.db.models import Exists, OuterRef
from openpyxl.styles import Protection
from django.db.models import Count,Sum,Avg
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
import re
from django.shortcuts import get_object_or_404