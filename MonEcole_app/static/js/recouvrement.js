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
    invoice:'/api/recouvrement/invoice/'
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
    loadPayHistory();
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
        if(!d.success||!d.variables.length){$('pay-variables-cards').style.display='none';return;}
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
                    <span style="color:#64748b">Payé: ${fmt(v.total_deja_paye)}</span>
                    <span style="font-weight:700;color:${color}">Reste: ${fmt(v.reste_a_payer)}</span>
                </div>
                ${v.reduction?'<div style="font-size:.58rem;color:#7c3aed;margin-top:2px"><i class="fas fa-percentage" style="font-size:.5rem"></i> Réduction: '+v.reduction+'%</div>':''}
            </div>`;
        });
        h+='</div>';$('pay-vars-grid').innerHTML=h;
        // Fill variable select in form
        const sel=$('pf-variable');sel.innerHTML='<option value="">— Variable —</option>';
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
function loadPayHistory(){
    const a=$('pay-annee').value,c=$('pay-classe').value;if(!c)return;
    get(R.paiValid+'?id_annee='+a+'&id_classe='+c).then(d=>{
        if(!d.success||!d.data.length){$('pay-history-wrap').innerHTML='<div class="rec-empty"><i class="fas fa-inbox"></i>Aucun paiement</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>N°</th><th>Élève</th><th>Variable</th><th>Montant</th><th>Statut</th><th>Actions</th></tr></thead><tbody>';
        d.data.forEach((p,i)=>{
            const badge=p.is_rejected?'<span class="rec-badge rec-badge-danger"><i class="fas fa-times-circle"></i> Rejeté</span>':'<span class="rec-badge rec-badge-success"><i class="fas fa-check-circle"></i> Validé</span>';
            h+=`<tr><td>${i+1}</td><td style="font-weight:600">${p.eleve_nom} ${p.eleve_prenom}</td><td>${p.variable}</td><td style="font-weight:700">${fmt(p.montant)} Fbu</td><td>${badge}</td><td><a href="${R.invoice}${p.id_paiement}/" target="_blank" class="rec-btn rec-btn-outline" style="padding:2px 8px;font-size:.62rem"><i class="fas fa-file-pdf"></i></a></td></tr>`;
        });
        h+='</tbody></table>';$('pay-history-wrap').innerHTML=h;
    });
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
    get(R.categories).then(d=>{
        if(!d.categories)return;
        const cats={};d.categories.forEach(c=>{cats[c.id_variable_categorie]=c.nom;});
        // For now load all variables by fetching categories (variables come via prix)
        const list=$('var-list');
        if(list){
            // We need a dedicated endpoint but for now use categories
            list.innerHTML='<div class="rec-empty"><i class="fas fa-tags"></i>Les variables apparaîtront après création</div>';
        }
    });
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
function loadPrix(){/* TODO: load prix grid for selected classe */}

/* ========== CAISSE ========== */
function loadOperations(){
    const a=$('caisse-annee')?.value||'',t=$('caisse-type')?.value||'';
    get(R.ops+'?annee='+a+'&type='+t).then(d=>{
        if(!d.success)return;
        const s=d.stats||{};
        if($('caisse-entrees'))$('caisse-entrees').textContent=fmt(s.entrees);
        if($('caisse-sorties'))$('caisse-sorties').textContent=fmt(s.sorties);
        if($('caisse-solde'))$('caisse-solde').textContent=fmt((s.entrees||0)-(s.sorties||0));
        const wrap=$('op-table-wrap');
        if(!d.operations||!d.operations.length){wrap.innerHTML='<div class="rec-empty"><i class="fas fa-inbox"></i>Aucune opération</div>';return;}
        let h='<table class="rec-table"><thead><tr><th>Date</th><th>Type</th><th>Catégorie</th><th>Montant</th><th>Source/Bénéf.</th><th>Mode</th><th>Réf.</th></tr></thead><tbody>';
        d.operations.forEach(o=>{
            const cls=o.type_operation==='ENTREE'?'rec-badge-success':'rec-badge-danger';
            const icon=o.type_operation==='ENTREE'?'fa-arrow-down':'fa-arrow-up';
            h+=`<tr><td>${o.date}</td><td><span class="rec-badge ${cls}"><i class="fas ${icon}"></i> ${o.type_operation}</span></td><td>${o.categorie}</td><td style="font-weight:700">${o.montant_formatted} Fbu</td><td>${o.source_beneficiaire}</td><td>${o.mode_paiement}</td><td style="font-family:monospace;font-size:.62rem">${o.reference}</td></tr>`;
        });
        h+='</tbody></table>';wrap.innerHTML=h;
    });
}
function toggleOpForm(){const w=$('op-form-wrap');w.style.display=w.style.display==='none'?'':'none';}
function loadCatOps(){
    const t=$('op-type').value;if(!t)return;
    const a=$('caisse-annee').value;
    get(R.catOps+'?annee='+a+'&type='+t).then(d=>{
        const sel=$('op-cat');sel.innerHTML='<option value="">— Catégorie —</option>';
        (d.categories||[]).forEach(c=>{sel.innerHTML+=`<option value="${c.id}">${c.nom}</option>`;});
    });
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
    if(pf)pf.onsubmit=function(e){e.preventDefault();post(R.savePai,new FormData(pf)).then(d=>{if(d.success){pf.reset();togglePayForm();loadPayHistory();loadVarsRestant();toast('Paiement enregistré',true);}else toast(d.error,false);});};
    const of=$('op-form');
    if(of)of.onsubmit=function(e){e.preventDefault();
        $('op-annee').value=$('caisse-annee').value;
        // Use first campus if available
        const fd=new FormData(of);
        post(R.saveOp,fd).then(d=>{if(d.success){of.reset();toggleOpForm();loadOperations();toast('Opération enregistrée',true);}else toast(d.error,false);});
    };
}

/* ========== INIT ========== */
document.addEventListener('DOMContentLoaded',function(){
    loadDashboard();
    loadCategories();loadVariables();loadBanques();
    const pa=$('pay-annee');if(pa)loadClasses('pay-classe',pa.value);
    loadPrixClasses();
    loadOperations();
    setupForms();
    // Make stat cards clickable for details
    document.querySelectorAll('.stat-card').forEach(card=>{card.style.cursor='pointer';});
});
