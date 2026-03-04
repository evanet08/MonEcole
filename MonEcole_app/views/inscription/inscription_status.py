from  .inscription import *

@csrf_exempt
@login_required
@module_required("Inscription")
def update_redoublement(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    try:
        data = json.loads(request.body)
        id_eleve = data.get('id_eleve')
        id_annee = data.get('id_annee')
        id_campus = data.get('id_campus')
        id_cycle = data.get('id_cycle')
        id_classe = data.get('id_classe')
        redoublement = data.get('redoublement')
        
        if not all([id_eleve, id_annee, id_campus, id_cycle, id_classe, redoublement is not None]):
            logger.warning(f"Paramètres manquants pour update_redoublement : {data}")
            return JsonResponse({'error': 'Paramètres manquants'}, status=400)
       
        # Recherche de l'inscription actuelle
        inscription = Eleve_inscription.objects.filter(
            id_eleve_id=id_eleve,
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle,
            id_classe_id=id_classe
        ).first()

        if not inscription:
            return JsonResponse({'error': 'Inscription non trouvée'}, status=404)

        if inscription.redoublement and not redoublement:
            return JsonResponse({
                'success': False,
                'error': 'Le statut de redoublement ne peut pas être désactivé.car en faisant références des resultats pour année antérieure;lélève doit redoubler!'
            }, status=403)

        if inscription.redoublement:
            return JsonResponse({
                'success': True,
                'message': f"Statut de redoublement déjà activé pour l'élève {id_eleve}."
            })

        annee = Annee.objects.filter(id_annee=id_annee).first()
        campus = Campus.objects.filter(id_campus=id_campus).first()
        cycle = Classe_cycle_actif.objects.filter(id_campus=campus, id_annee=annee, id_cycle_actif=id_cycle).first()
        classe = Classe_active.objects.filter(id_campus=campus, id_annee=annee, cycle_id=id_cycle, id_classe_active=id_classe).first()

        if not all([annee, campus, cycle, classe]):
            return JsonResponse({'error': 'Données de référence manquantes'}, status=400)

        annee_precedente = Annee.objects.filter(annee__lt=annee.annee).order_by('-annee').first()
        if not annee_precedente:
            return JsonResponse({
                'success': False,
                'error': "Statut de redoublement impossible : cet élève est inscrit uniquement dans cette année séléctionnée! "
            }, status=400)

        campus_precedent = Campus.objects.filter(campus=campus.campus).first()
        cycle_precedent = Classe_cycle_actif.objects.filter(
            id_campus=campus_precedent.id_campus,
            id_annee=annee_precedente,
            cycle_id__cycle=cycle.cycle_id.cycle
        ).first()
        classe_precedente = Classe_active.objects.filter(
            id_campus=campus_precedent.id_campus,
            id_annee=annee_precedente,
            cycle_id=cycle_precedent.id_cycle_actif,
            classe_id__classe=classe.classe_id.classe
        ).first()
        
        if not all([campus_precedent, cycle_precedent, classe_precedente]):
            return JsonResponse({
                'success': False,
                'error': "Données de référence de l'année précédente manquantes."
            }, status=400)
        inscription_precedente = Eleve_inscription.objects.filter(
            id_eleve_id=id_eleve,
            id_annee_id=annee_precedente.id_annee,
            id_campus_id=campus_precedent.id_campus,
            id_classe_cycle_id=cycle_precedent.id_cycle_actif,
            id_classe_id=classe_precedente.id_classe_active
        ).first()
        if not inscription_precedente:
            return check_historical_inscriptions(
                id_eleve,
                annee_precedente.id_annee,
                redoublement,
                inscription,
                campus_nom=campus.campus,
                cycle_nom=cycle.cycle_id.cycle,
                classe_nom=classe.classe_id.classe
            )
        deliberation_result = Deliberation_annuelle_resultat.objects.filter(
            id_campus_id=campus_precedent.id_campus,
            id_cycle_id=cycle_precedent.id_cycle_actif,
            id_classe_id=classe_precedente.id_classe_active,
            id_annee_id=annee_precedente.id_annee,
            id_eleve_id=id_eleve
        ).first()
        if not deliberation_result:
            return JsonResponse({
                'success': False,
                'error': "cette opération ne peut être éxecuter car  cet élève n'a pas des resultats pour l'année antérieure" 
            }, status=400)

        repechage_result = Deliberation_repechage_resultat.objects.filter(
            id_campus_id=campus_precedent.id_campus,
            id_cycle_id=cycle_precedent.id_cycle_actif,
            id_classe_id=classe_precedente.id_classe_active,
            id_annee_id=annee_precedente.id_annee,
            id_eleve_id=id_eleve
        ).first()
        
        
        if repechage_result and deliberation_result:
            cours_repechage = Deliberation_repechage_resultat.objects.filter(
                id_eleve_id=id_eleve,
                id_annee_id=annee_precedente.id_annee,
                id_campus_id=campus_precedent.id_campus,
                id_cycle_id=cycle_precedent.id_cycle_actif,
                id_classe_id=classe_precedente.id_classe_active
                
            )
            cours_count = cours_repechage.count()
            cours_valides = cours_repechage.filter(valid_repechage=True).count()

            redoublement_auto = False
            if cours_count == 2:
                redoublement_auto = cours_valides < 1
            elif cours_count == 3:
                redoublement_auto = cours_valides < 2
            else:
                logger.warning(f"[REPECHAGE] Élève {id_eleve}: Nombre inattendu de cours en repêchage ({cours_count}).")
                return JsonResponse({
                    'success': False,
                    'error': "Nombre de cours en repêchage invalide."
                }, status=400)

            if redoublement_auto:
                inscription.redoublement = True
                inscription.save()
                logger.info(f"[REPECHAGE] Élève {id_eleve} : redoublement appliqué (cours valides : {cours_valides}/{cours_count})")
                return JsonResponse({
                    'success': True,
                    'message': f"Statut de redoublement mis à jour avec succès pour cet élève."
                })
            

        pourcentage = deliberation_result.pourcentage
        try:
            mention = Mention.objects.get(
                Q(id_mention=deliberation_result.id_mention_id) &
                Q(min__lte=pourcentage) &
                Q(max__gte=pourcentage)
            )
            logger.debug(f"Mention trouvée pour l'élève {id_eleve} : {mention.mention} ({mention.min}% - {mention.max}%)")
        except ObjectDoesNotExist:
            logger.warning(f"Aucune mention correspondante pour pourcentage={pourcentage} pour l'élève {id_eleve}")
            inscription.redoublement = redoublement
            inscription.save()
            return JsonResponse({
                'success': True,
                'message': f"Statut de redoublement mis à jour pour l'élève {id_eleve}."
            })

        try:
            deliberation_condition = Deliberation_annuelle_condition.objects.get(
                id_mention=mention.id_mention,
                id_annee_id=annee_precedente.id_annee,
                id_campus_id=campus_precedent.id_campus,
                id_cycle_id=cycle_precedent.id_cycle_actif,
                id_classe_id=classe_precedente.id_classe_active
            )
        except ObjectDoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f"Veuillez configurer dans le système toutes conditions nécéssaires  pour facilter la prise de décision."
            })

        try:
            finalite = Deliberation_annuelle_finalite.objects.get(
                id_finalite=deliberation_condition.id_finalite_id
            )
            if finalite.droit_avancement == True:
                logger.warning(f"Échec mise à jour redoublement pour {id_eleve} : droit_avancement=True")
                return JsonResponse({
                    'success': False,
                    'error': "Redoublement non autorisé : Vue ses résultats pour année antérieure il peut pas être redoublant!"
                }, status=403)
            else:
                inscription.redoublement = redoublement
                inscription.save()
                logger.info(f"Statut redoublement mis à jour pour l'élève {id_eleve} : redoublement={redoublement}")
                return JsonResponse({
                    'success': True,
                    'message': f"Statut de redoublement mis à jour pour l'élève {id_eleve}."
                })
        
        except ObjectDoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f"Veuillez configurer dans le système toutes finalités nécéssaires  pour facilter la prise de décision."
                
            })

    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du redoublement pour l'élève {id_eleve} : {str(e)}")
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)

def check_historical_inscriptions(id_eleve, id_annee, redoublement, inscription, campus_nom, cycle_nom, classe_nom):
    """
    Vérifie les inscriptions historiques de l'élève pour la même classe, cycle et campus dans toutes les années antérieures.
    """
    try:
        annees_anterieures = Annee.objects.filter(annee__lt=Annee.objects.get(id_annee=id_annee).annee).order_by('-annee')

        if not annees_anterieures.exists():
            return JsonResponse({
                'success': False,
                'message': f"Statut de redoublement ne peut pas etre réalisable car l'élève n'a aucun resultat pour  année antérieure"
            })

        for annee in annees_anterieures:
            campus = Campus.objects.filter(campus=campus_nom).first()
            if not campus:
                continue  

            cycle = Classe_cycle_actif.objects.filter(
                id_campus=campus,
                id_annee=annee,
                cycle_id__cycle=cycle_nom
            ).first()
            if not cycle:
                continue
            classe = Classe_active.objects.filter(
                id_campus=campus,
                id_annee=annee,
                cycle_id=cycle.id_cycle_actif,
                classe_id__classe=classe_nom
            ).first()
            if not classe:
                continue 

            inscription_historique = Eleve_inscription.objects.filter(
                id_eleve_id=id_eleve,
                id_annee_id=annee.id_annee,
                id_campus_id=campus.id_campus,
                id_classe_cycle_id=cycle.id_cycle_actif,
                id_classe_id=classe.id_classe_active
            ).first()

            if not inscription_historique:
                continue  
            deliberation_result = Deliberation_annuelle_resultat.objects.filter(
                id_campus_id=campus.id_campus,
                id_cycle_id=cycle.id_cycle_actif,
                id_classe_id=classe.id_classe_active,
                id_annee_id=annee.id_annee,
                id_eleve_id=id_eleve
            ).first()

            if not deliberation_result:
                continue
            pourcentage = deliberation_result.pourcentage
            repechage_result = Deliberation_repechage_resultat.objects.filter(
                id_campus_id=campus.id_campus,
                id_cycle_id=cycle.id_cycle_actif,
                id_classe_id=classe.id_classe_active,
                id_annee_id=annee.id_annee,
                id_eleve_id=id_eleve
            ).first()

            if repechage_result:
                cours_repechage = Deliberation_repechage_resultat.objects.filter(
                    id_eleve_id=id_eleve,
                    id_annee_id=annee.id_annee
                )
                cours_count = cours_repechage.count()
                cours_valides = cours_repechage.filter(valid_repechage=True).count()

                redoublement_auto = False
                if cours_count == 2:
                    redoublement_auto = cours_valides < 1
                elif cours_count == 3:
                    redoublement_auto = cours_valides < 2
                else:
                    logger.warning(f"[REPECHAGE] Élève {id_eleve}: Nombre inattendu de cours en repêchage ({cours_count}).")
                    return JsonResponse({
                        'success': False,
                        'error': "Nombre de cours en repêchage invalide."
                    }, status=400)

                if redoublement_auto:
                    inscription.redoublement = True
                    inscription.save()
                    logger.info(f"[REPECHAGE] Élève {id_eleve} : redoublement appliqué (cours valides : {cours_valides}/{cours_count})")
                    return JsonResponse({
                        'success': True,
                        'message': f"Statut de redoublement mis à jour avec succès pour l'élève {id_eleve}."
                    })
                else:
                    logger.info(f"[REPECHAGE] Élève {id_eleve} : pas de redoublement (cours valides : {cours_valides}/{cours_count})")
                    if redoublement:
                        return JsonResponse({
                            'success': False,
                            'error': "Redoublement non autorisé : l'élève a validé suffisamment de cours en repêchage."
                        }, status=403)
                    return JsonResponse({
                        'success': True,
                        'message': f"Aucun redoublement requis pour l'élève {id_eleve}."
                    })

            try:
                mention = Mention.objects.get(
                    Q(id_mention=deliberation_result.id_mention_id) &
                    Q(min__lte=pourcentage) &
                    Q(max__gte=pourcentage)
                )
                logger.debug(f"Mention trouvée (historique) pour l'élève {id_eleve} : {mention.mention} ({mention.min}% - {mention.max}%)")
            except ObjectDoesNotExist:
                logger.warning(f"Aucune mention correspondante pour pourcentage={pourcentage} pour l'élève {id_eleve} (historique)")
                inscription.redoublement = redoublement
                inscription.save()
                return JsonResponse({
                    'success': True,
                    'message': f"Statut de redoublement mis à jour pour l'élève {id_eleve}."
                })

            try:
                deliberation_condition = Deliberation_annuelle_condition.objects.get(
                    id_mention=mention.id_mention,
                    id_annee_id=annee.id_annee,
                    id_campus_id=campus.id_campus,
                    id_cycle_id=cycle.id_cycle_actif,
                    id_classe_id=classe.id_classe_active
                )
            except ObjectDoesNotExist:
                inscription.redoublement = redoublement
                inscription.save()
                return JsonResponse({
                    'success': True,
                    'message': f"Statut de redoublement mis à jour pour l'élève {id_eleve}."
                })

            try:
                finalite = Deliberation_annuelle_finalite.objects.get(
                    id_finalite=deliberation_condition.id_finalite_id
                )
                if finalite.droit_avancement==True:
                    return JsonResponse({
                        'success': False,
                        'error': "Redoublement non autorisé,car vue les resultats de l'élève;il n'a pas le droit au redoublement dans cette classe!."
                    }, status=403)
                else:
                    inscription.redoublement = redoublement
                    inscription.save()
                    return JsonResponse({
                        'success': True,
                        'message': f"Statut de redoublement mis à jour pour l'élève {id_eleve}."
                    })
            except ObjectDoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f"veuillez configurer toutes les conditions pour facilter les criteres de redoublement."
                })

        return JsonResponse({
            'success': False,
            'message': f"Statut de redoublement rejetté car l'élève n'a aucune inscription ou résultat trouvé pour les années antérieures!."
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)

@csrf_exempt  
@login_required
def update_status(request):
    if request.method != 'POST':
        logger.warning("Méthode non autorisée pour update_status")
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    try:
        data = json.loads(request.body)
        id_eleve = data.get('id_eleve')
        id_annee = data.get('id_annee')
        id_campus = data.get('id_campus')
        id_cycle = data.get('id_cycle')
        id_classe = data.get('id_classe')
        status = data.get('status')

        if not all([id_eleve, id_annee, id_campus, id_cycle, id_classe, status is not None]):
            logger.warning(f"Paramètres manquants pour update_status : {data}")
            return JsonResponse({'error': 'Paramètres manquants'}, status=400)

        inscription = Eleve_inscription.objects.filter(
            id_eleve_id=id_eleve,
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle,
            id_classe_id=id_classe
        ).first()

        if not inscription:
            logger.warning(f"Aucune inscription trouvée pour l'élève {id_eleve} dans la classe {id_classe}")
            return JsonResponse({'error': 'Inscription non trouvée'}, status=404)

        inscription.status = status
        inscription.save()

        logger.info(f"Statut mis à jour pour l'élève {id_eleve} : status={status}")
        return JsonResponse({
            'success': True,
            'message': f"Statut mis à jour pour l'élève {id_eleve}."
        })

    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut : {str(e)}")
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)