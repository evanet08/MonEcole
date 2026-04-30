/* Recouvrement Module — JS Logic */
const R={
    dashData:'/api/recouvrement/dashboard-data/',dashDetails:'/api/recouvrement/dashboard-details/',
    classes:'/api/recouvrement/classes/',eleves:'/api/recouvrement/eleves/',
    varsRestant:'/api/recouvrement/variables-restant/',banques:'/api/recouvrement/banques/',
    categories:'/api/recouvrement/categories/',paiSubmit:'/api/recouvrement/paiements-submitted/',
    paiValid:'/api/recouvrement/paiements-validated/',paiEleve:'/api/recouvrement/paiements-eleve/',
    saveCat:'/api/recouvrement/save-categorie-variable/',saveVar:'/api/recouvrement/save-variable/',
    saveBanque:'/api/recouvrement/save-banque/',saveCompte:'/api/recouvrement/save-compte/',
    savePrix:'/api/recouvrement/save-variable-prix/',savePai:'/api/recouvrement/save-paiement/',
    ops:'/api/recouvrement/operations/',catOps:'/api/recouvrement/categories-operations/',
    saveCatOp:'/api/recouvrement/save-categorie-operation/',saveOp:'/api/recouvrement/save-operation/',
    invoice:'/api/recouvrement/invoice/',
    allVars:'/api/recouvrement/variables-all/',prixClasse:'/api/recouvrement/prix-classe/',
    penalites:'/api/recouvrement/penalites/',savePen:'/api/recouvrement/save-penalite/',
    datesBut:'/api/recouvrement/dates-butoires/',saveDateBut:'/api/recouvrement/save-date-butoire/',
    updOblig:'/api/recouvrement/update-variable-obligatoire/'
};
function fmt(n){return n!=null?(n).toLocaleString('fr-FR'):'—';}
function $(id){return document.getElementById(id);}
function post(url,fd){return fetch(url,{method:'POST',body:fd}).then(r=>r.json());}
function get(url){return fetch(url).then(r=>r.json());}
function toast(msg,ok){const t=document.createElement('div');t.textContent=msg;t.style.cssText='position:fixed;top:20px;right:20px;z-index:9999;padding:10px 20px;border-radius:10px;color:#fff;font-size:.78rem;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,.2);animation:statPop .3s ease;background:'+(ok?'linear-gradient(135deg,#059669,#10b981)':'linear-gradient(135deg,#dc2626,#f87171)');document.body.appendChild(t);setTimeout(()=>t.remove(),3000);}

/* Tab switching */
function switchCfgTab(btn){
    document.querySelectorAll('#cfgTabs .config-tab').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('#sec-configuration .config-tab-content').forEach(c=>c.classList.remove('active'));
    $(btn.dataset.tab).classList.add('active');
}

/* ========== DASHBOARD ========== */
function loadDashboard(){
    const a=$('dash-annee')?.value;if(!a)return;
    get(R.dashData+'?annee='+a).then(d=>{
        if(!d.success)return;const s=d.stats;
        $('stat-paye').textContent=fmt(s.total_paye);
        $('stat-attendu').textContent=fmt(s.total_attendu);
        $('stat-reste').textContent=fmt(s.reste_a_payer);
        $('stat-trans').textContent=fmt(s.total_transactions);
        $('stat-dette').textContent=fmt(s.eleves_en_dette);
        $('stat-rejete').textContent=fmt(s.total_rejete);
        // Chart area
        const area=$('dash-chart-area');
        if(s.total_attendu>0){
            const pct=Math.round((s.total_paye/s.total_attendu)*100);
            area.innerHTML=`
                <div style="margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;font-size:.72rem;color:#64748b;margin-bottom:4px"><span>Progression globale</span><span style="font-weight:700;color:#0f172a">${pct}%</span></div>
                    <div style="height:28px;background:#f1f5f9;border-radius:14px;overflow:hidden">
                        <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,#059669,#34d399);border-radius:14px;transition:width 1.5s ease;display:flex;align-items:center;justify-content:flex-end;padding-right:8px">
                            <span style="font-size:.62rem;font-weight:700;color:#fff">${fmt(s.total_paye)}</span>
                        </div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.72rem">
                    <div style="padding:8px 12px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0"><strong style="color:#166534">Payé:</strong> ${fmt(s.total_paye)} Fbu</div>
                    <div style="padding:8px 12px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca"><strong style="color:#991b1b">Reste:</strong> ${fmt(s.reste_a_payer)} Fbu</div>
                </div>`;
        }else{area.innerHTML='<div class="rec-empty"><i class="fas fa-chart-area"></i>Aucune donnée</div>';}
        // Resume
        const res=$('dash-resume');
        if(res)res.innerHTML=`<div style="font-size:.75rem;line-height:1.8"><div><strong>${fmt(s.total_transactions)}</strong> transactions enregistrées</div><div><strong>${fmt(s.eleves_en_dette)}</strong> élèves en retard de paiement</div><div><strong>${fmt(s.total_rejete)}</strong> paiements rejetés</div></div>`;
    });
}

/* ========== PAIEMENTS ========== */
function loadClasses(selId,anneeId,cb){
    const sel=$(selId);if(!sel)return;
    sel.innerHTML='<option value="">— Sélectionner —</option>';
    get(R.classes+'?annee_id='+anneeId).then(d=>{
        if(d.success)(d.classes||[]).forEach(c=>{
            const o=document.createElement('option');o.value=c.id_classe;
            o.textContent=c.campus_nom+' — '+c.classe_nom+(c.groupe?' ('+c.groupe+')':'');
            o.dataset.campus=c.id_campus;o.dataset.cycle=c.id_cycle;o.dataset.groupe=c.groupe||'';
            sel.appendChild(o);
        });
        if(cb)cb();
    });
}
function onPayAnneeChange(){loadClasses('pay-classe',$('pay-annee').value);}
function onPayClasseChange(){
    const a=$('pay-annee').value,c=$('pay-classe').value;
    if(!c){$('pay-eleve').innerHTML='<option value="">— Sélectionner —</option>';return;}
    const sel=$('pay-eleve');sel.innerHTML='<option value="">— Sélectionner —</option>';
    get(R.eleves+'?id_annee='+a+'&id_classe='+c).then(d=>{
        if(d.success)(d.data||[]).forEach(e=>{
            const o=document.createElement('option');o.value=e.id_eleve;o.textContent=e.nom_complet;
            sel.appendChild(o);
        });
    });
    loadPayAll();
}
function onPayEleveChange(){
    const e=$('pay-eleve').value;
    if(e){$('btnNewPay').style.display='';loadVarsRestant();}
    else{$('btnNewPay').style.display='none';$('pay-variables-cards').style.display='none';}
}
function loadVarsRestant(){
    const a=$('pay-annee').value,c=$('pay-classe').value,e=$('pay-eleve').value;
    if(!e)return;
    get(R.varsRestant+'?id_annee='+a+'&id_classe='+c+'&id_eleve='+e).then(d=>{
        if(!d.success||!d.variables||!d.variables.length){
            $('pay-variables-cards').style.display='';
            $('pay-vars-grid').innerHTML='<div class="rec-empty" style="font-size:.72rem"><i class="fas fa-exclamation-triangle" style="color:#d97706"></i> Aucun prix configur\u00e9 pour cette classe. <br>Allez dans <strong>Configuration \u2192 Prix</strong> pour d\u00e9finir les prix des variables.</div>';
            // Fallback: load ALL variables into the dropdown
            const sel=$('pf-variable');sel.innerHTML='<option value="">\u2014 Variable \u2014</option>';
            get(R.allVars).then(vd=>{
                if(vd.success)(vd.variables||[]).forEach(v=>{
                    const o=document.createElement('option');o.value=v.id_variable;o.textContent=v.variable;sel.appendChild(o);
                });
            });
            return;
        }
        $('pay-variables-cards').style.display='';
        let h='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px">';
        d.variables.forEach(v=>{
            const pct=Math.round(((v.montant_total-v.reste_a_payer)/v.montant_total)*100);
            const color=pct>=100?'#059669':pct>=50?'#d97706':'#dc2626';
            h+=`<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px">
                <div style="font-size:.72rem;font-weight:700;color:#1e293b;margin-bottom:4px">${v.nom_variable}</div>
                <div style="font-size:.6rem;color:#94a3b8;margin-bottom:6px">${v.categorie}</div>
                <div style="height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden;margin-bottom:4px">
                    <div style="height:100%;width:${pct}%;background:${color};border-radius:4px;transition:width .8s"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:.62rem">
                    <span style="color:#64748b">Pay\u00e9: ${fmt(v.total_deja_paye)}</span>
                    <span style="font-weight:700;color:${color}">Reste: ${fmt(v.reste_a_payer)}</span>
                </div>
                ${v.reduction?'<div style="font-size:.58rem;color:#7c3aed;margin-top:2px"><i class="fas fa-percentage" style="font-size:.5rem"></i> R\u00e9duction: '+v.reduction+'%</div>':''}
            </div>`;
        });
        h+='</div>';$('pay-vars-grid').innerHTML=h;
        // Fill variable select in form
        const sel=$('pf-variable');sel.innerHTML='<option value="">\u2014 Variable \u2014</option>';
        d.variables.forEach(v=>{if(v.reste_a_payer>0){const o=document.createElement('option');o.value=v.id_variable;o.textContent=v.nom_variable+' (reste: '+fmt(v.reste_a_payer)+')';sel.appendChild(o);}});
    });
}
function togglePayForm(){
    const w=$('pay-form-wrap');w.style.display=w.style.display==='none'?'':'none';
    if(w.style.display!=='none'){
        const opt=$('pay-classe').selectedOptions[0];
        $('pf-annee').value=$('pay-annee').value;$('pf-classe').value=$('pay-classe').value;
        $('pf-eleve').value=$('pay-eleve').value;
        if(opt){$('pf-campus').value=opt.dataset.campus||'';$('pf-cycle').value=opt.dataset.cycle||'';$('pf-groupe').value=opt.dataset.groupe||'';}
        loadComptes();
    }
}
function loadComptes(){
    get(R.banques).then(d=>{
        if(!d.banques)return;
        const sel=$('pf-compte');sel.innerHTML='<option value="">— Compte —</option>';
        d.banques.forEach(b=>{
            fetch('/api/recouvrement/comptes/'+b.id_banque+'/').then(r=>r.json()).then(cd=>{
                (cd.comptes||[]).forEach(c=>{const o=document.createElement('option');o.value=c.id_compte;o.textContent=b.banque+' — '+c.compte;sel.appendChild(o);});
            });
        });
    });
}
function switchPayTab(btn){
    document.querySelectorAll('#payTabs .config-tab').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('#sec-paiements .config-tab-content').forEach(c=>c.classList.remove('active'));
    $(btn.dataset.tab).classList.add('active');
}
function loadPayAll(){loadPayPending();loadPayValidated();loadPayRejected();}
function loadPayPending(){
    const a=$('pay-annee').value,c=$('pay-classe').value;if(!c)return;
    get(R.paiSubmit+'?id_annee='+a+'&id_classe='+c).then(d=>{
        const wrap=$('pay-pending-wrap');
        $('pay-pending-count').textContent=d.data?d.data.length:0;
        if(!d.success||!d.data||!d.data.length){wrap.innerHTML='<div class="rec-empty"><i class="fas fa-inbox"></i>Aucun paiement en attente</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Élève</th><th>Variable</th><th>Montant</th><th>Date</th><th>Bordereau</th><th style="width:120px">Actions</th></tr></thead><tbody>';
        d.data.forEach((p,i)=>{
            const bord=p.bordereau?`<a href="${p.bordereau}" target="_blank" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem"><i class="fas fa-image"></i></a>`:'—';
            h+=`<tr>
                <td>${i+1}</td><td style="font-weight:600">${p.eleve_nom} ${p.eleve_prenom}</td>
                <td>${p.variable}</td><td style="font-weight:700">${fmt(p.montant)} Fbu</td>
                <td style="font-size:.7rem">${p.date_paie||'—'}</td><td>${bord}</td>
                <td>
                    <button onclick="updatePayField(${p.id_paiement},'status','true')" class="rec-btn rec-btn-success" style="padding:2px 6px;font-size:.58rem" title="Valider"><i class="fas fa-check"></i></button>
                    <button onclick="updatePayField(${p.id_paiement},'is_rejected','true')" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem;color:#dc2626" title="Rejeter"><i class="fas fa-times"></i></button>
                </td>
            </tr>`;
        });
        h+='</tbody></table>';wrap.innerHTML=h;
    });
}
function loadPayValidated(){
    const a=$('pay-annee').value,c=$('pay-classe').value;if(!c)return;
    get(R.paiValid+'?id_annee='+a+'&id_classe='+c).then(d=>{
        const wrap=$('pay-validated-wrap');
        const validOnly=(d.data||[]).filter(p=>!p.is_rejected);
        const rejectedOnly=(d.data||[]).filter(p=>p.is_rejected);
        $('pay-valid-count').textContent=validOnly.length;
        $('pay-rejected-count').textContent=rejectedOnly.length;
        // Show export buttons
        const btns=$('pay-export-btns');if(btns)btns.style.display=validOnly.length?'flex':'none';
        if(!validOnly.length){wrap.innerHTML='<div class="rec-empty"><i class="fas fa-inbox"></i>Aucun paiement validé</div>';} else {
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Élève</th><th>Variable</th><th>Montant</th><th>Date</th><th>Bordereau</th><th style="width:140px">Actions</th></tr></thead><tbody>';
        validOnly.forEach((p,i)=>{
            const bord=p.bordereau?`<a href="${p.bordereau}" target="_blank" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem"><i class="fas fa-image"></i></a>`:'—';
            h+=`<tr>
                <td>${i+1}</td><td style="font-weight:600">${p.eleve_nom} ${p.eleve_prenom}</td>
                <td>${p.variable}</td><td style="font-weight:700">${fmt(p.montant)} Fbu</td>
                <td style="font-size:.7rem">${p.date_paie||'—'}</td><td>${bord}</td>
                <td>
                    <a href="${R.invoice}${p.id_paiement}/" target="_blank" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem" title="Facture PDF"><i class="fas fa-file-pdf" style="color:#dc2626"></i></a>
                    <button onclick="updatePayField(${p.id_paiement},'is_rejected','true')" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem;color:#f59e0b" title="Rejeter"><i class="fas fa-ban"></i></button>
                    <button onclick="deletePay(${p.id_paiement})" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem;color:#dc2626" title="Supprimer"><i class="fas fa-trash"></i></button>
                </td>
            </tr>`;
        });
        h+='</tbody></table>';wrap.innerHTML=h;}
        // Rejected tab
        const rWrap=$('pay-rejected-wrap');
        if(!rejectedOnly.length){rWrap.innerHTML='<div class="rec-empty"><i class="fas fa-inbox"></i>Aucun paiement rejeté</div>';} else {
        let hr='<table class="rec-table"><thead><tr><th>N°</th><th>Élève</th><th>Variable</th><th>Montant</th><th>Date</th><th style="width:100px">Actions</th></tr></thead><tbody>';
        rejectedOnly.forEach((p,i)=>{
            hr+=`<tr style="opacity:.7"><td>${i+1}</td><td style="font-weight:600">${p.eleve_nom} ${p.eleve_prenom}</td><td>${p.variable}</td><td style="font-weight:700;text-decoration:line-through">${fmt(p.montant)} Fbu</td><td style="font-size:.7rem">${p.date_paie||'—'}</td>
            <td><button onclick="updatePayField(${p.id_paiement},'is_rejected','false')" class="rec-btn rec-btn-success" style="padding:2px 6px;font-size:.58rem" title="Restaurer"><i class="fas fa-undo"></i></button>
            <button onclick="deletePay(${p.id_paiement})" class="rec-btn rec-btn-outline" style="padding:2px 6px;font-size:.58rem;color:#dc2626" title="Supprimer"><i class="fas fa-trash"></i></button></td></tr>`;
        });
        hr+='</tbody></table>';rWrap.innerHTML=hr;}
    });
}
function loadPayRejected(){/* Handled inside loadPayValidated */}
function updatePayField(id,field,value){
    const fd=new FormData();
    fd.append('csrfmiddlewaretoken',document.querySelector('[name=csrfmiddlewaretoken]')?.value||'');
    fd.append('id_paiement',id);fd.append('field',field);fd.append('value',value);
    post('/api/recouvrement/update-paiement-field/',fd).then(d=>{if(d.success){toast('Mis à jour',true);loadPayAll();}else toast(d.error||'Erreur',false);});
}
function deletePay(id){
    if(!confirm('Supprimer ce paiement définitivement ?'))return;
    const fd=new FormData();fd.append('csrfmiddlewaretoken',document.querySelector('[name=csrfmiddlewaretoken]')?.value||'');
    post('/api/recouvrement/delete-paiement/'+id+'/',fd).then(d=>{if(d.success){toast('Supprimé',true);loadPayAll();loadVarsRestant();}else toast(d.error||'Erreur',false);});
}
function exportFicheClasse(){
    const a=$('pay-annee').value,c=$('pay-classe').value;if(!c)return;
    const opt=$('pay-classe').selectedOptions[0];
    const campus=opt?.dataset.campus||'',cycle=opt?.dataset.cycle||'';
    window.open('/api/recouvrement/fiche-paie/?id_annee='+a+'&id_classe='+c+'&idCampus='+campus+'&id_cycle='+cycle,'_blank');
}
function exportFicheEleve(){
    const a=$('pay-annee').value,c=$('pay-classe').value,e=$('pay-eleve').value;
    if(!e){toast('Sélectionnez un élève',false);return;}
    const opt=$('pay-classe').selectedOptions[0];
    const campus=opt?.dataset.campus||'',cycle=opt?.dataset.cycle||'';
    window.open('/api/recouvrement/fiche-paie/?id_annee='+a+'&id_classe='+c+'&id_eleve='+e+'&idCampus='+campus+'&id_cycle='+cycle,'_blank');
}

/* ========== CONFIGURATION ========== */
function loadCategories(){
    get(R.categories).then(d=>{
        if(!d.categories)return;
        // List
        const list=$('cat-list');
        if(list){
            if(!d.categories.length){list.innerHTML='<div class="rec-empty"><i class="fas fa-folder-open"></i>Aucune catégorie</div>';return;}
            let h='<table class="rec-table"><thead><tr><th>N°</th><th>Catégorie</th></tr></thead><tbody>';
            d.categories.forEach((c,i)=>{h+=`<tr><td>${i+1}</td><td style="font-weight:600">${c.nom}</td></tr>`;});
            h+='</tbody></table>';list.innerHTML=h;
        }
        // Fill selects
        const vcs=$('var-cat-select');
        if(vcs){vcs.innerHTML='<option value="">— Catégorie —</option>';d.categories.forEach(c=>{vcs.innerHTML+=`<option value="${c.id_variable_categorie}">${c.nom}</option>`;});}
    });
}
function loadVariables(){
    get(R.allVars).then(d=>{
        const list=$('var-list');
        if(!list)return;
        if(!d.success||!d.variables||!d.variables.length){list.innerHTML='<div class="rec-empty"><i class="fas fa-tags"></i>Aucune variable</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Variable</th><th>Catégorie</th><th style="width:90px">Obligatoire</th></tr></thead><tbody>';
        d.variables.forEach((v,i)=>{
            const isOb=v.estObligatoire;
            const cls=isOb?'rec-badge-success':'rec-badge-warning';
            const txt=isOb?'Oui':'Non';
            h+=`<tr><td>${i+1}</td><td style="font-weight:600">${v.variable}</td><td>${v.categorie||'—'}</td><td><button onclick="toggleObligatoire(${v.id_variable},${!isOb})" class="rec-btn ${isOb?'rec-btn-success':'rec-btn-outline'}" style="padding:2px 8px;font-size:.6rem"><i class="fas fa-${isOb?'check':'times'}"></i> ${txt}</button></td></tr>`;
        });
        h+='</tbody></table>';list.innerHTML=h;
        fillVarSelects(d.variables);
    });
}
function fillVarSelects(vars){
    ['pen-variable','but-variable'].forEach(id=>{
        const sel=$(id);if(!sel)return;
        sel.innerHTML='<option value="">— Toutes —</option>';
        vars.forEach(v=>{sel.innerHTML+=`<option value="${v.id_variable}">${v.variable}</option>`;});
    });
}
function toggleObligatoire(varId,newVal){
    const fd=new FormData();
    fd.append('csrfmiddlewaretoken',document.querySelector('[name=csrfmiddlewaretoken]')?.value||'');
    fd.append('id_variable',varId);fd.append('estObligatoire',newVal?'true':'false');
    post(R.updOblig,fd).then(d=>{if(d.success){toast('Mis à jour',true);loadVariables();}else toast(d.error||'Erreur',false);});
}
function loadBanques(){
    get(R.banques).then(d=>{
        if(!d.banques)return;
        const bl=$('banque-list');
        if(bl){
            if(!d.banques.length){bl.innerHTML='<div class="rec-empty"><i class="fas fa-university"></i>Aucune banque</div>';return;}
            let h='<table class="rec-table"><thead><tr><th>N°</th><th>Banque</th><th>Sigle</th></tr></thead><tbody>';
            d.banques.forEach((b,i)=>{h+=`<tr><td>${i+1}</td><td style="font-weight:600">${b.banque}</td><td>${b.sigle||'—'}</td></tr>`;});
            h+='</tbody></table>';bl.innerHTML=h;
        }
        // Fill selects
        const cbs=$('compte-banque-select');
        if(cbs){cbs.innerHTML='<option value="">— Banque —</option>';d.banques.forEach(b=>{cbs.innerHTML+=`<option value="${b.id_banque}">${b.banque}</option>`;});}
        // Load comptes
        const cl=$('compte-list');
        if(cl){
            cl.innerHTML='';
            let all=[];
            Promise.all(d.banques.map(b=>fetch('/api/recouvrement/comptes/'+b.id_banque+'/').then(r=>r.json()).then(cd=>{
                (cd.comptes||[]).forEach(c=>{all.push({banque:b.banque,...c});});
            }))).then(()=>{
                if(!all.length){cl.innerHTML='<div class="rec-empty"><i class="fas fa-credit-card"></i>Aucun compte</div>';return;}
                let h='<table class="rec-table"><thead><tr><th>N°</th><th>Banque</th><th>Compte</th></tr></thead><tbody>';
                all.forEach((c,i)=>{h+=`<tr><td>${i+1}</td><td>${c.banque}</td><td style="font-weight:600;font-family:monospace">${c.compte}</td></tr>`;});
                h+='</tbody></table>';cl.innerHTML=h;
            });
        }
    });
}
function loadPrixClasses(){loadClasses('prix-classe',$('prix-annee').value);}
function loadPrix(){
    const a=$('prix-annee')?.value, sel=$('prix-classe'), c=sel?.value;
    const grid=$('prix-grid');
    if(!c||!a){grid.innerHTML='<div class="rec-empty"><i class="fas fa-hand-pointer"></i>Sélectionnez une année et une classe pour configurer les prix</div>';return;}
    grid.innerHTML='<div class="rec-empty"><i class="fas fa-spinner fa-spin"></i>Chargement…</div>';
    const opt=sel.selectedOptions[0];
    const campusId=opt?.dataset.campus||'', cycleId=opt?.dataset.cycle||'', groupe=opt?.dataset.groupe||'';
    get(R.prixClasse+'?id_annee='+a+'&id_classe='+c).then(d=>{
        if(!d.success){grid.innerHTML='<div class="rec-empty"><i class="fas fa-exclamation-triangle"></i>'+d.error+'</div>';return;}
        if(!d.variables||!d.variables.length){grid.innerHTML='<div class="rec-empty"><i class="fas fa-tags"></i>Aucune variable configurée. Créez d\'abord des variables dans l\'onglet <strong>Variables</strong>.</div>';return;}
        let h='<table class="rec-table"><thead><tr><th style="width:30px">N°</th><th>Variable</th><th>Catégorie</th><th style="width:140px">Prix (Fbu)</th><th style="width:100px">Action</th></tr></thead><tbody>';
        d.variables.forEach((v,i)=>{
            const hasPrice=v.prix!==null&&v.prix!==undefined;
            const badgeCls=hasPrice?'rec-badge-success':'rec-badge-warning';
            const badgeTxt=hasPrice?'Défini':'Non défini';
            h+=`<tr id="prix-row-${v.id_variable}">
                <td>${i+1}</td>
                <td style="font-weight:600">${v.variable}</td>
                <td><span class="rec-badge ${badgeCls}" style="font-size:.58rem"><i class="fas fa-${hasPrice?'check':'exclamation-circle'}"></i> ${badgeTxt}</span> ${v.categorie}</td>
                <td><input type="number" id="prix-input-${v.id_variable}" value="${hasPrice?v.prix:''}" min="0" placeholder="0" style="width:100%;padding:4px 8px;border:1px solid #e2e8f0;border-radius:6px;font-size:.75rem;text-align:right" /></td>
                <td><button onclick="savePrixVariable(${v.id_variable},'${a}','${c}','${campusId}','${cycleId}','${groupe}')" class="rec-btn rec-btn-success" style="padding:3px 10px;font-size:.65rem"><i class="fas fa-save"></i> Enregistrer</button></td>
            </tr>`;
        });
        h+='</tbody></table>';
        // Summary
        const total=d.variables.filter(v=>v.prix!==null&&v.prix!==undefined).length;
        const missing=d.variables.length-total;
        h+=`<div style="margin-top:10px;font-size:.72rem;color:#64748b;display:flex;gap:16px;align-items:center">
            <span><i class="fas fa-check-circle" style="color:#059669"></i> <strong>${total}</strong> prix défini${total>1?'s':''}</span>
            ${missing?'<span><i class="fas fa-exclamation-circle" style="color:#d97706"></i> <strong>'+missing+'</strong> en attente</span>':''}
        </div>`;
        grid.innerHTML=h;
    });
}
function savePrixVariable(varId,anneeId,classeId,campusId,cycleId,groupe){
    const inp=$('prix-input-'+varId);
    const prix=inp?.value;
    if(!prix||parseInt(prix)<=0){toast('Veuillez entrer un prix valide',false);return;}
    const fd=new FormData();
    fd.append('csrfmiddlewaretoken',document.querySelector('[name=csrfmiddlewaretoken]')?.value||'');
    fd.append('id_annee',anneeId);fd.append('id_classe',classeId);
    fd.append('id_variable',varId);fd.append('prix',prix);
    fd.append('idCampus',campusId);fd.append('id_cycle',cycleId);fd.append('groupe',groupe);
    post(R.savePrix,fd).then(d=>{
        if(d.success){toast('Prix enregistré',true);loadPrix();}
        else toast(d.error||'Erreur',false);
    });
}

/* ========== PÉNALITÉS ========== */
function loadPenalites(){
    const a=$('pen-annee')?.value||'';
    get(R.penalites+'?id_annee='+a).then(d=>{
        const list=$('pen-list');
        if(!list)return;
        if(!d.success||!d.data||!d.data.length){list.innerHTML='<div class="rec-empty"><i class="fas fa-gavel"></i>Aucune pénalité configurée</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Variable</th><th>Type</th><th>Valeur</th><th>Plafond</th><th>Année</th><th>Statut</th></tr></thead><tbody>';
        d.data.forEach((p,i)=>{
            const typeBadge=p.type==='FORFAIT'?'<span class="rec-badge rec-badge-info"><i class="fas fa-coins"></i> Forfait</span>':'<span class="rec-badge rec-badge-warning"><i class="fas fa-percentage"></i> Pourcentage</span>';
            const statBadge=p.actif?'<span class="rec-badge rec-badge-success"><i class="fas fa-check"></i> Actif</span>':'<span class="rec-badge rec-badge-danger"><i class="fas fa-times"></i> Inactif</span>';
            h+=`<tr><td>${i+1}</td><td style="font-weight:600">${p.variable}</td><td>${typeBadge}</td><td style="font-weight:700">${p.valeur}${p.type==='POURCENTAGE'?'%':' Fbu'}</td><td>${p.plafond?fmt(p.plafond)+' Fbu':'—'}</td><td>${p.annee||'—'}</td><td>${statBadge}</td></tr>`;
        });
        h+='</tbody></table>';list.innerHTML=h;
    });
}

/* ========== DATES BUTOIRES ========== */
function loadButClasses(){loadClasses('but-classe',$('but-annee').value);}
function loadButoires(){
    const a=$('but-annee')?.value||'';
    get(R.datesBut+'?id_annee='+a).then(d=>{
        const list=$('but-list');
        if(!list)return;
        if(!d.success||!d.data||!d.data.length){list.innerHTML='<div class="rec-empty"><i class="fas fa-calendar-times"></i>Aucune date butoire configurée</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Variable</th><th>Date limite</th></tr></thead><tbody>';
        d.data.forEach((b,i)=>{
            const dateStr=b.date_butoire||'—';
            const isPast=b.date_butoire&&new Date(b.date_butoire)<new Date();
            h+=`<tr><td>${i+1}</td><td style="font-weight:600">${b.variable||'—'}</td><td style="font-weight:700;color:${isPast?'#dc2626':'#059669'}"><i class="fas fa-calendar-day"></i> ${dateStr}</td></tr>`;
        });
        h+='</tbody></table>';list.innerHTML=h;
    });
}

/* ========== CAISSE ========== */
function switchCaissTab(btn){
    document.querySelectorAll('#caisseTabs .config-tab').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('#sec-caisse .config-tab-content').forEach(c=>c.classList.remove('active'));
    $(btn.dataset.tab).classList.add('active');
}
function loadCatOperations(){
    get(R.catOps+'?annee=&type=').then(d=>{
        const list=$('cat-op-list');
        if(!list)return;
        const cats=d.categories||[];
        if(!cats.length){list.innerHTML='<div class="rec-empty"><i class="fas fa-folder-open"></i>Aucune catégorie d\'opération</div>';return;}
        const entrees=cats.filter(c=>c.type_operation==='ENTREE');
        const sorties=cats.filter(c=>c.type_operation==='SORTIE');
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Nom</th><th>Type</th><th>Description</th></tr></thead><tbody>';
        cats.forEach((c,i)=>{
            const badge=c.type_operation==='ENTREE'?'rec-badge-success':'rec-badge-danger';
            const icon=c.type_operation==='ENTREE'?'fa-arrow-down':'fa-arrow-up';
            const label=c.type_operation==='ENTREE'?'Entrée':'Sortie';
            h+=`<tr><td>${i+1}</td><td style="font-weight:600">${c.nom}</td><td><span class="rec-badge ${badge}"><i class="fas ${icon}"></i> ${label}</span></td><td style="color:#64748b;font-size:.72rem">${c.description||'—'}</td></tr>`;
        });
        h+='</tbody></table>';
        h+=`<div style="margin-top:8px;font-size:.72rem;color:#64748b;display:flex;gap:16px">
            <span><i class="fas fa-arrow-down" style="color:#059669"></i> <strong>${entrees.length}</strong> entrée${entrees.length>1?'s':''}</span>
            <span><i class="fas fa-arrow-up" style="color:#dc2626"></i> <strong>${sorties.length}</strong> sortie${sorties.length>1?'s':''}</span>
        </div>`;
        list.innerHTML=h;
        // Also fill caisse-cat filter
        const catSel=$('caisse-cat');
        if(catSel){catSel.innerHTML='<option value="">Toutes</option>';cats.forEach(c=>{const ic=c.type_operation==='ENTREE'?'⬆️':'⬇️';catSel.innerHTML+=`<option value="${c.id}">${ic} ${c.nom}</option>`;});}
    });
}
function loadOperations(){
    const a=$('caisse-annee')?.value||'',t=$('caisse-type')?.value||'',cat=$('caisse-cat')?.value||'';
    get(R.ops+'?annee='+a+'&type='+t+'&categorie='+cat).then(d=>{
        if(!d.success)return;const s=d.stats||{};
        if($('caisse-total'))$('caisse-total').textContent=s.total||'0';
        if($('caisse-entrees'))$('caisse-entrees').textContent=fmt(s.entrees);
        if($('caisse-sorties'))$('caisse-sorties').textContent=fmt(s.sorties);
        if($('caisse-solde'))$('caisse-solde').textContent=fmt((s.entrees||0)-(s.sorties||0));
        const wrap=$('op-table-wrap');
        if(!d.operations||!d.operations.length){wrap.innerHTML='<div class="rec-empty"><i class="fas fa-inbox"></i>Aucune opération</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Date</th><th>Catégorie</th><th>Type</th><th>Montant</th><th>Source/Bénéf.</th><th>Mode</th><th>Description</th><th>Réf.</th></tr></thead><tbody>';
        d.operations.forEach((o,i)=>{
            const cls=o.type_operation==='ENTREE'?'rec-badge-success':'rec-badge-danger';
            const icon=o.type_operation==='ENTREE'?'fa-arrow-down':'fa-arrow-up';
            const label=o.type_operation==='ENTREE'?'Entrée':'Sortie';
            h+=`<tr><td>${i+1}</td><td>${o.date}</td><td style="font-weight:600">${o.categorie}</td><td><span class="rec-badge ${cls}"><i class="fas ${icon}"></i> ${label}</span></td><td style="font-weight:700">${o.montant_formatted} Fbu</td><td>${o.source_beneficiaire||'—'}</td><td>${o.mode_paiement||'—'}</td><td style="color:#64748b;font-size:.72rem;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${o.description||''}">${o.description||'—'}</td><td style="font-family:monospace;font-size:.62rem">${o.reference||'—'}</td></tr>`;
        });
        h+='</tbody></table>';wrap.innerHTML=h;
    });
}
function toggleOpForm(){const w=$('op-form-wrap');w.style.display=w.style.display==='none'?'':'none';}
function loadCatOps(){
    const t=$('op-type').value;if(!t)return;
    const a=$('caisse-annee')?.value||'';
    get(R.catOps+'?annee='+a+'&type='+t).then(d=>{
        const sel=$('op-cat');sel.innerHTML='<option value="">— Catégorie —</option>';
        (d.categories||[]).forEach(c=>{sel.innerHTML+=`<option value="${c.id}">${c.nom}</option>`;});
    });
}
function exportOpsPDF(){
    const a=$('caisse-annee')?.value||'',t=$('caisse-type')?.value||'',cat=$('caisse-cat')?.value||'';
    window.open('/api/recouvrement/operations-pdf/?annee='+a+'&type='+t+'&categorie='+cat,'_blank');
}
function exportOpsExcel(){
    const a=$('caisse-annee')?.value||'',t=$('caisse-type')?.value||'',cat=$('caisse-cat')?.value||'';
    window.location.href='/api/recouvrement/operations-excel/?annee='+a+'&type='+t+'&categorie='+cat;
}

/* ========== FORM HANDLERS ========== */
function setupForms(){
    const cf=$('cat-form');
    if(cf)cf.onsubmit=function(e){e.preventDefault();post(R.saveCat,new FormData(cf)).then(d=>{if(d.success){cf.reset();loadCategories();toast('Catégorie ajoutée',true);}else toast(d.error,false);});};
    const vf=$('var-form');
    if(vf)vf.onsubmit=function(e){e.preventDefault();post(R.saveVar,new FormData(vf)).then(d=>{if(d.success){vf.reset();loadVariables();toast('Variable ajoutée',true);}else toast(d.error,false);});};
    const bf=$('banque-form');
    if(bf)bf.onsubmit=function(e){e.preventDefault();post(R.saveBanque,new FormData(bf)).then(d=>{if(d.success){bf.reset();loadBanques();toast('Banque ajoutée',true);}else toast(d.error,false);});};
    const cof=$('compte-form');
    if(cof)cof.onsubmit=function(e){e.preventDefault();post(R.saveCompte,new FormData(cof)).then(d=>{if(d.success){cof.reset();loadBanques();toast('Compte ajouté',true);}else toast(d.error,false);});};
    const pf=$('pay-form');
    if(pf)pf.onsubmit=function(e){e.preventDefault();post(R.savePai,new FormData(pf)).then(d=>{if(d.success){pf.reset();togglePayForm();loadPayAll();loadVarsRestant();toast('Paiement enregistré',true);}else toast(d.error,false);});};
    const of=$('op-form');
    if(of)of.onsubmit=function(e){e.preventDefault();
        $('op-annee').value=$('caisse-annee')?.value||'';
        const fd=new FormData(of);
        post(R.saveOp,fd).then(d=>{if(d.success){of.reset();toggleOpForm();loadOperations();toast('Opération enregistrée',true);}else toast(d.error,false);});
    };
    // Category operations form
    const copf=$('cat-op-form');
    if(copf)copf.onsubmit=function(e){e.preventDefault();
        $('catop-annee').value=$('caisse-annee')?.value||$('dash-annee')?.value||'';
        post(R.saveCatOp,new FormData(copf)).then(d=>{if(d.success){copf.reset();loadCatOperations();toast('Catégorie ajoutée',true);}else toast(d.error,false);});
    };
    // Pénalité form
    const penf=$('pen-form');
    if(penf)penf.onsubmit=function(e){e.preventDefault();
        post(R.savePen,new FormData(penf)).then(d=>{if(d.success){penf.reset();loadPenalites();toast('Pénalité ajoutée',true);}else toast(d.error,false);});
    };
    // Date butoire form
    const butf=$('but-form');
    if(butf)butf.onsubmit=function(e){e.preventDefault();
        const fd=new FormData(butf);
        const cs=$('but-classe')?.selectedOptions[0];
        if(cs){fd.append('idCampus',cs.dataset.campus||'');fd.append('id_cycle',cs.dataset.cycle||'');}
        post(R.saveDateBut,fd).then(d=>{if(d.success){butf.reset();loadButoires();toast('Date butoire enregistrée',true);}else toast(d.error,false);});
    };
}

/* ========== INIT ========== */
document.addEventListener('DOMContentLoaded',function(){
    loadDashboard();
    loadCategories();loadVariables();loadBanques();
    const pa=$('pay-annee');if(pa)loadClasses('pay-classe',pa.value);
    loadPrixClasses();loadPenalites();loadButClasses();loadButoires();
    loadCatOperations();loadOperations();
    setupForms();
    // Make stat cards clickable for details
    document.querySelectorAll('.stat-card').forEach(card=>{card.style.cursor='pointer';});
});
