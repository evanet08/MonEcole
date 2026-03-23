
from MonEcole_app.models.models_import import *
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from MonEcole_app.views.tools import get_user_info
from django.shortcuts import render
from MonEcole_app.forms.evaluation_form import DeliberationTrimestreForm
from .__initials import *
from .structure_bulletin import stylize_table
import logging
from django.db import transaction
from django.db.models import Max
from .evaluation import (
    get_note_types,
    get_cours_classe,
    get_trimestres,
    build_domaines_dict,
    build_groupes,
    initialize_table_data,
    clean_cours_name,
    add_cours__notes_in_rows,
)