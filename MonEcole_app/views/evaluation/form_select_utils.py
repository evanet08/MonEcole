from .__initials import get_user_info,login_required,Eleve_NoteForm,render
from MonEcole_app.models.models_import import Eleve_note
from MonEcole_app.views.decorators.decorators import  module_required


@login_required
@module_required("Evaluation")
def select_by_field_to_generate_bulletin(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = Eleve_NoteForm(request.POST or None)
    return render(request, 'evaluation/index_evaluation.html', {
        'form_select_bulletin':form_select,
        'form_type': 'select_form_bull',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })
    
@login_required
@module_required("Evaluation")
def select_by_field_to_generate_file_note(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = Eleve_NoteForm(request.POST or None)
    return render(request, 'evaluation/index_evaluation.html', {
        'form_select':form_select,
        'form_type': 'select_form_note',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })
    

@login_required
@module_required("Institeur et son Espace")
def select_by_field_for_complaints(request):
    reclam_cours = Eleve_note.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = Eleve_NoteForm(request.POST or None)
    return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
        'form_select_reclam':form_select,
        'reclam_cours' : reclam_cours,
        'form_type': 'select_form_reclam',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })
    
    
@login_required
@module_required("Institeur et son Espace")
def select_by_field_for_repechages(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = Eleve_NoteForm(request.POST or None)
    return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
        'form_select_repechag':form_select,
        'form_type': 'select_form_repechag',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })
 
 
