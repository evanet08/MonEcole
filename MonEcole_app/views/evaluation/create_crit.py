from .__initials import *
from MonEcole_app.views.decorators.decorators import module_required


@login_required
@module_required("Evaluation")
def add_note_type(request):
    note_type_list = Eleve_note_type.objects.all()

    try:
        user_info = get_user_info(request)
    except Exception as e:
        messages.error(request, "Erreur interne : impossible de récupérer les infos utilisateur.")
        return redirect('add_types_notes')

    if request.method == 'POST':
        form = Note_type_Form(request.POST)

        if form.is_valid():
            type_note = form.cleaned_data['type'].strip()
          

            if Eleve_note_type.objects.filter(type__iexact=type_note).exists():
                messages.error(request, f'Le type de note "{type_note}" existe déjà.')
                return redirect('add_types_notes')
            else:
                form.save()
                messages.success(request, 'Type de note ajouté avec succès !')
                return redirect('add_types_notes')  
        else:
            messages.error(request, 'Erreur lors de l\'ajout du type de note. Veuillez vérifier les données.')
    else:
        form = Note_type_Form()
    
    return render(request, 'evaluation/index_evaluation.html', {
        'type_note_form': form,
        'form_type': 'form_note_type',
        'note_type_list': note_type_list,
        'photo_profil': user_info['photo_profil'],
        'modules': user_info['modules'],
        'last_name': user_info['last_name']
    })

@login_required
@module_required("Evaluation")
def add_session(request):
    session_list = Session.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.cleaned_data['session'].strip()  
            if Session.objects.filter(session__iexact=session).exists():
                messages.error(request, f'La session "{session}" existe déjà.')
                return redirect('create_session')
            else:
                form.save()
                messages.success(request, 'La session  ajoutée avec succès !')
                return redirect('create_session')  
        else:
            messages.error(request, 'Erreur lors de l\'ajout de la session. Veuillez vérifier les données.')
    else:
        form = SessionForm()

    return render(request, 'evaluation/index_evaluation.html', {
                    'session_form':form,
                    'form_type': 'form_session',
                    'session_list': session_list,
                    'photo_profil': user_modules['photo_profil'],
                    'modules': user_modules['modules'],
                    'last_name': user_modules['last_name']},)

@login_required
@module_required("Evaluation")
def session_edit(request):
    if request.method == 'POST':
        id_session = request.POST.get('id_session')
        session = get_object_or_404(Session, id_session=id_session)
        form = SessionForm(request.POST, instance=session)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            try:
                form.save()
                print('Session saved:', session.id_session)
                if is_ajax:
                    messages.success(request, 'Session modifiée avec succès.')
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Session modifiée avec succès.',
                        'redirect': '/create_session'
                    })
            except Exception as e:
                print('Error saving session:', str(e))
                if is_ajax:
                    messages.error(request, f'Erreur lors de l’enregistrement : {str(e)}')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erreur lors de l’enregistrement : {str(e)}',
                        'redirect': '/create_session'
                    })
        else:
            # print('Form errors:', form.errors)
            if is_ajax:
                messages.error(request, f'Formulaire invalide : {form.errors.as_text()}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formulaire invalide : {form.errors.as_text()}',
                    'redirect': '/create_session'
                })
        return render(request, 'evaluation/index_evaluation.html', {'form': form})
    return render(request, 'evaluation/index_evaluation.html')


