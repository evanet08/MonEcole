
from MonEcole_app.views.evaluation import *
from MonEcole_app.views.rdc_structure import *

@csrf_protect
@login_required
@module_required("Evaluation")
def generer_bulletin_pdf(request):
    if request.method == 'POST':
        id_annee  = request.POST.get('id_annee')
        id_campus = request.POST.get('id_campus')
        id_cycle  = request.POST.get('id_cycle')
        id_classe = request.POST.get('id_classe')
        id_eleves = request.POST.getlist('id_eleve')
    else:
        id_annee  = request.GET.get('id_annee')
        id_campus = request.GET.get('id_campus')
        id_cycle  = request.GET.get('id_cycle')
        id_classe = request.GET.get('id_classe')
        id_eleves = [request.GET.get('id_eleve')]

    if not all([id_annee, id_campus, id_cycle, id_classe]) or not id_eleves or not id_eleves[0]:
        messages.error(request, "Paramètres manquants ou invalides.")
        return HttpResponse('<script>sessionStorage.clear(); window.location.href="/home_evaluation";</script>')

    try:
        id_annee  = int(id_annee)
        id_campus = int(id_campus)
        id_cycle  = int(id_cycle)
        id_classe = int(id_classe)
        id_eleves = [int(e) for e in id_eleves if e and e.isdigit()]
    except ValueError:
        messages.error(request, "Paramètres numériques invalides.")
        return HttpResponse('<script>history.back();</script>', status=400)

    if not id_eleves:
        messages.error(request, "Aucun élève sélectionné.")
        return HttpResponse('<script>history.back();</script>', status=400)

    # ───────────────────────────────────────────────
    # Déterminer la localisation
    # ───────────────────────────────────────────────
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        localisation = campus.localisation.strip().upper()
    except Campus.DoesNotExist:
        messages.error(request, "Campus introuvable.")
        return HttpResponse('<script>history.back();</script>', status=404)

    buffer = BytesIO()
    filename_parts = []
    elements = []

    styles, style_normal, style_center, style_title, style_right = get_styles()

    # ───────────────────────────────────────────────
    # CAS BDI
    # ───────────────────────────────────────────────
    if localisation == "BDI":
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=20, leftMargin=20,
            topMargin=20, bottomMargin=20,
        )

        for idx, id_eleve in enumerate(id_eleves):
            try:
                eleve = Eleve.objects.get(id_eleve=id_eleve)
                inscription = Eleve_inscription.objects.filter(
                    id_eleve=id_eleve,
                    id_annee=id_annee,
                    id_campus=id_campus,
                    id_classe_cycle=id_cycle,
                    id_classe=id_classe,
                    status=1
                ).first()

                if not inscription:
                    continue

                if idx > 0:
                    elements.append(PageBreak())
                elements.extend(create_header_elements())
                student_info, nom_eleve = create_student_info_tables(
                    id_eleve, id_annee, id_campus, id_cycle, id_classe
                )
                elements.extend(student_info)

                results_table, total_pct = create_results_table(
                    id_eleve, id_annee, id_campus, id_cycle, id_classe
                )
                elements.extend(results_table)

                elements.extend(create_signature_table())
                elements.append(PageBreak())

                elements.extend(create_back_page(
                    id_annee, id_campus, id_cycle, id_eleve, id_classe, total_pct
                ))

                filename_parts.append(slugify(nom_eleve))

            except Exception as e:
                logger.exception(f"Erreur bulletin BDI élève {id_eleve}")
                continue

        if not elements:
            messages.error(request, "Aucun bulletin valide généré pour BDI.")
            return HttpResponse('<script>history.back();</script>', status=400)

        doc.build(elements, onFirstPage=page_template, onLaterPages=page_template)

    # ───────────────────────────────────────────────
    # CAS RDC
    # ───────────────────────────────────────────────
    else:
        try:
            classe_active = Classe_active.objects.get(id_classe_active=id_classe)
            classe_name = classe_active.classe_id.classe.strip()
        except:
            messages.error(request, "Classe introuvable.")
            return HttpResponse('<script>history.back();</script>', status=404)
        margin = 5 * mm

        if classe_name in ['1ère Année', '1er Langue', '1er SC', '1er Eco', '1ère Primaire', '2ème Primaire', '3ème Primaire', '4ème Primaire', '5ème Primaire', '6ème Primaire']:
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0,
                bottomMargin=5*mm,
                leftMargin=5*mm,
                rightMargin=5*mm
            )

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)

                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 5*mm))
                    institution = Institution.objects.get(id_ecole=campus.id_etablissement)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center)
                    create_nid_section(elements, style_normal)

                    left_table = create_line2_left(elements, style_normal, id_campus)
                    right_table = create_line2_right(elements, eleve,style_normal,id_classe)
                    create_line2_section(elements, left_table, right_table)

                    create_bulletin_title(elements, style_title,id_annee,id_classe)
                    create_notes_table(
                        elements, style_center, style_normal,
                        id_annee, id_campus, id_cycle, id_classe, id_eleve
                    )
                    create_footer(elements, style_normal, style_center)

                    filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))

                except Exception as e:
                    logger.exception(f"Erreur bulletin 1ère Année élève {id_eleve}")
                    continue

        elif classe_name in ['7ème A E.B', '8ème A E.B', '7ème', '8ème']:
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0,
                bottomMargin=5*mm,
                leftMargin=5*mm,
                rightMargin=5*mm
            )

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)

                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 5*mm))
                    institution = Institution.objects.get(id_ecole=campus.id_etablissement)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center)
                    create_nid_section(elements, style_normal)

                    left_table = create_line2_left(elements, style_normal, id_campus)
                    right_table = create_line2_right__secondaire_rdc(elements, eleve,id_classe, style_normal)
                    create_line2_section__secondaire_rdc(elements, left_table, right_table)
                    create_bulletin_title__secondaire_rdc(elements, style_title, style_right,id_annee,id_classe)
                    create_notes_table__secondaire_rdc(
                        elements, style_center, style_normal,
                        id_annee, id_campus, id_cycle, id_classe, id_eleve
                    )
                    create_footer__secondaire_rdc(elements, style_normal, style_center,id_classe)

                    filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))

                except Exception as e:
                    logger.exception(f"Erreur bulletin 7ème élève {id_eleve}")
                    continue
                
        elif classe_name in ['4ème construction', '2ème Niveau Eléctricité Industrielle', '2sc MTP', '2ème LANGUE', '2ème Eco', '2ème BCT', '3ème MPT', '3ème BCT', '3ème ECO']:
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0,
                bottomMargin=5*mm,
                leftMargin=5*mm,
                rightMargin=5*mm
            )

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)

                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 5*mm))

                    institution = Institution.objects.get(id_ecole=campus.id_etablissement)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None

                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center)
                    create_nid_section(elements, style_normal)
                    left_table = create_line2_left(elements, style_normal, id_campus)
                    right_table = create_line2_right__secondaire_rdc(
                        elements,
                        eleve,
                        id_classe,
                        style_normal
                    )

                    create_line2_section__secondaire_rdc(
                        elements,
                        left_table,
                        right_table
                    )

                    create_bulletin_title__secondaire_superieur(
                        elements,
                        style_title,
                        style_right
                    )

                    create_notes_table_superieur(
                        elements,
                        style_center,
                        style_normal,
                        id_annee,
                        id_campus,
                        id_cycle,
                        id_classe,
                        id_eleve
                    )

                    create_footer__secondaire_rdc(
                        elements,
                        style_normal,
                        style_center,
                        id_classe
                    )

                    filename_parts.append(
                        slugify(eleve.nom or f"eleve_{id_eleve}")
                    )

                except Exception as e:
                    logger.exception(
                        f"Erreur bulletin 4ème construction élève {id_eleve}"
                    )
                    continue



        else:
            messages.error(request, f"Classe non prise en charge : {classe_name}")
            return HttpResponse('<script>history.back();</script>', status=400)

        if not elements:
            messages.error(request, "Aucun bulletin valide généré pour RDC.")
            return HttpResponse('<script>history.back();</script>', status=400)

        def on_all_pages(canvas, doc):
            draw_border(canvas, doc, eleve, margin) 

        doc.build(elements, onFirstPage=on_all_pages, onLaterPages=on_all_pages)

    # ───────────────────────────────────────────────
    # Nom de fichier final + réponse
    # ───────────────────────────────────────────────
    if len(id_eleves) == 1 and filename_parts:
        nom_fichier = slugify(filename_parts[0])
    else:
        try:
            classe = Classe.objects.get(id_classe=id_classe)
            nom_classe = slugify(classe.nom or "classe")
        except:
            nom_classe = "classe"
        nom_fichier = f"Bulletins_{localisation}_{nom_classe}_{id_annee}"

    filename = f"{nom_fichier}.pdf"

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"; filename*=UTF-8\'\'{filename}'

    buffer.close()
    return response

