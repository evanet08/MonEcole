/* parent_child.js — Logic for parent child detail page */
const ID_ELEVE = window._ELEVE_ID;
let sectionsLoaded = {};

function showSection(name) {
    document.querySelectorAll('.section-pane').forEach(p => p.style.display = 'none');
    const el = document.getElementById('sec-' + name);
    if (el) el.style.display = 'block';
    // Immersive mode for communication
    if (name === 'comm') { document.body.classList.add('comm-active'); }
    else { document.body.classList.remove('comm-active'); }
    // Close FAB
    const menu = document.getElementById('fabMenu');
    if (menu && menu.classList.contains('open')) toggleFab();
    // Lazy load
    if (!sectionsLoaded[name]) {
        sectionsLoaded[name] = true;
        if (name === 'notes') loadNotes();
        if (name === 'dashboard') loadDashboard();
        if (name === 'payments') loadPayments();
        if (name === 'comm') loadComm();
        if (name === 'profile') loadProfile();
    }
    window.scrollTo({top: 0, behavior: 'smooth'});
}

/* ═══ NOTES ═══ */
async function loadNotes() {
    try {
        const r = await fetch(`/parent/api/evaluations/?id_eleve=${ID_ELEVE}`);
        const d = await r.json();
        const c = document.getElementById('notesList');
        if (!d.success || !d.evaluations || !d.evaluations.length) {
            c.innerHTML = '<div class="empty-msg"><i class="fas fa-clipboard-list"></i>Aucune évaluation disponible</div>';
            return;
        }
        // Group by cours
        const byCours = {};
        d.evaluations.forEach(n => {
            const k = n.cours || '—';
            if (!byCours[k]) byCours[k] = [];
            byCours[k].push(n);
        });
        let h = '';
        for (const [cours, evals] of Object.entries(byCours)) {
            h += `<div style="margin-bottom:16px">`;
            h += `<div style="font-size:.68rem;font-weight:700;color:#6366f1;text-transform:uppercase;letter-spacing:.5px;margin:0 0 6px 4px;display:flex;align-items:center;gap:6px"><i class="fas fa-book" style="font-size:.6rem"></i>${cours}</div>`;
            evals.forEach(n => {
                const v = n.note_eleve !== null ? parseFloat(n.note_eleve) : null;
                const pond = n.ponderation || 20;
                const pct = v !== null ? (v / pond * 100) : 0;
                const cls = v === null ? 'na' : pct >= 70 ? 'good' : pct >= 50 ? 'avg' : 'poor';
                const typeLabel = n.type_note ? `<span style="font-size:.5rem;background:#eff6ff;color:#3b82f6;padding:1px 6px;border-radius:4px;font-weight:600;margin-left:4px">${n.type_note}</span>` : '';
                const repLabel = n.note_repechage !== null && n.note_repechage !== undefined ? `<span style="font-size:.5rem;color:#d97706;margin-left:4px">(Rp: ${parseFloat(n.note_repechage).toFixed(1)})</span>` : '';
                const docBtn = n.document_url ? `<a href="${n.document_url}" target="_blank" style="display:inline-flex;align-items:center;gap:3px;font-size:.55rem;color:#6366f1;text-decoration:none;margin-top:2px"><i class="fas fa-file-alt"></i>Document</a>` : '';
                h += `<div class="data-row" style="flex-wrap:wrap">`;
                h += `<div class="data-main"><div class="data-title">${n.title || '—'}${typeLabel}</div><div class="data-sub">${n.date_eval || ''} ${docBtn}</div></div>`;
                h += `<div class="data-badge ${cls}">${v !== null ? v.toFixed(1) : '—'}/${pond}${repLabel}</div>`;
                h += `</div>`;
            });
            h += `</div>`;
        }
        c.innerHTML = h;
    } catch(e) { document.getElementById('notesList').innerHTML = '<div class="empty-msg">Erreur de chargement</div>'; }
}

/* ═══ DASHBOARD ═══ */
async function loadDashboard() {
    try {
        const r = await fetch(`/parent/api/dashboard/?id_eleve=${ID_ELEVE}`);
        const d = await r.json();
        if (!d.success) return;
        const db = d.dashboard;
        if (db.presence) {
            document.getElementById('tauxPresence').textContent = (db.presence.taux_presence||100)+'%';
            document.getElementById('nbPresents').textContent = db.presence.presents||0;
            document.getElementById('nbAbsents').textContent = db.presence.absents||0;
            let ah = '';
            (db.presence.absences_recentes||[]).forEach(a => {
                ah += `<div class="data-row"><div class="data-main"><div class="data-title">${a.date}</div><div class="data-sub">${a.creneau}</div></div><div class="data-badge poor">${a.motif}</div></div>`;
            });
            document.getElementById('absencesList').innerHTML = ah || '<div class="empty-msg">Aucune absence</div>';
        }
        let ch = '';
        (db.conduite||[]).forEach(c => {
            ch += `<div class="data-row"><div class="data-main"><div class="data-title">${c.motif}</div><div class="data-sub">${c.date}</div></div><div class="data-badge ${c.quote>=5?'good':c.quote>=3?'avg':'poor'}">${c.quote}/10</div></div>`;
        });
        document.getElementById('conduiteList').innerHTML = ch || '<div class="empty-msg">Aucun incident</div>';
        let eh = '';
        (db.resultats_evolution||[]).forEach(r => {
            eh += `<div class="data-row"><div class="data-main"><div class="data-title">Période ${r.periode_id}</div><div class="data-sub">Place: ${r.place}</div></div><div class="data-badge ${r.pourcentage>=60?'good':r.pourcentage>=50?'avg':'poor'}">${r.pourcentage}%</div></div>`;
        });
        document.getElementById('evolutionList').innerHTML = eh || '<div class="empty-msg">Pas encore de résultats</div>';
    } catch(e) { console.error(e); }
}

/* ═══ PAYMENTS ═══ */
async function loadPayments() {
    try {
        const r = await fetch(`/parent/api/payments/?id_eleve=${ID_ELEVE}`);
        const d = await r.json();
        const sumC = document.getElementById('paymentsSummary');
        const listC = document.getElementById('paymentsList');
        if (!d.success) { listC.innerHTML = '<div class="empty-msg">Erreur</div>'; return; }
        let sh = '';
        (d.summary||[]).forEach(s => {
            const pct = s.montant_attendu > 0 ? Math.round(s.montant_paye / s.montant_attendu * 100) : 0;
            sh += `<div class="data-row"><div class="data-main"><div class="data-title">${s.variable}</div><div class="data-sub">${s.categorie} · Payé: ${s.montant_paye.toLocaleString()} / ${s.montant_attendu.toLocaleString()}</div></div><div class="data-badge ${pct>=100?'good':pct>=50?'avg':'poor'}">${pct}%</div></div>`;
        });
        sumC.innerHTML = sh || '<div class="empty-msg">Aucune variable</div>';
        let ph = '';
        (d.payments||[]).forEach(p => {
            const cls = p.statut === 'validé' ? 'good' : p.statut === 'rejeté' ? 'poor' : 'avg';
            ph += `<div class="data-row"><div class="data-main"><div class="data-title">${p.variable||'Paiement'}</div><div class="data-sub">${p.date_paie||'—'} · ${p.banque||''}</div></div><div class="data-badge ${cls}">${(p.montant||0).toLocaleString()}</div></div>`;
        });
        listC.innerHTML = ph || '<div class="empty-msg">Aucun paiement</div>';
    } catch(e) { document.getElementById('paymentsList').innerHTML = '<div class="empty-msg">Erreur</div>'; }
}

/* ═══ PROFILE EDIT ═══ */
let profileData = null;
let adminTypes = [];
let adminInstances = {};

async function loadProfile() {
    try {
        const r = await fetch(`/parent/api/profile/?id_eleve=${ID_ELEVE}`);
        const d = await r.json();
        if (!d.success) return;
        profileData = d.profile;
        adminTypes = d.admin_types || [];
        adminInstances = d.admin_instances || {};
        renderProfileForm();
    } catch(e) { console.error(e); }
}

function renderProfileForm() {
    const p = profileData;
    const c = document.getElementById('profileForm');
    let h = `
    <div class="pf-photo-wrap">
        <div class="pf-avatar" id="pfAvatar">${p.photo ? `<img src="${p.photo}" onerror="this.remove()">` : (p.prenom||'?').charAt(0)+(p.nom||'?').charAt(0)}</div>
        <label class="pf-photo-btn"><i class="fas fa-camera"></i> Modifier<input type="file" accept="image/*" onchange="uploadPhoto(this)" style="display:none"></label>
    </div>
    <div class="pf-grid">
        <div class="pf-field"><label>Nom</label><input id="pf_nom" value="${p.nom||''}" disabled></div>
        <div class="pf-field"><label>Prénom</label><input id="pf_prenom" value="${p.prenom||''}" disabled></div>
        <div class="pf-field"><label>Genre</label><input value="${p.genre==='F'?'Féminin':'Masculin'}" disabled></div>
        <div class="pf-field"><label>Date de naissance</label><input value="${p.date_naissance||'—'}" disabled></div>
        <div class="pf-field"><label>Téléphone</label><input id="pf_telephone" value="${p.telephone||''}"></div>
        <div class="pf-field"><label>Email</label><input id="pf_email" value="${p.email||''}"></div>
        <div class="pf-field"><label>Nationalité</label><input id="pf_nationalite" value="${p.nationalite||''}"></div>
        <div class="pf-field"><label>État civil</label><input id="pf_etat_civil" value="${p.etat_civil||''}"></div>
        <div class="pf-field full"><label>Matricule</label><input value="${p.matricule||'—'}" disabled></div>
    </div>
    <p class="sec-label" style="margin-top:16px">Adresse de naissance</p>`;
    h += renderRefAdmin('naissance', p.ref_administrative_naissance || '');
    h += `<p class="sec-label" style="margin-top:14px">Adresse de résidence</p>
    <label class="pf-checkbox"><input type="checkbox" id="sameAddr" onchange="toggleSameAddr()"> Adresse identique à l'adresse de naissance</label>`;
    h += `<div id="residenceFields">`;
    h += renderRefAdmin('residence', p.ref_administrative_residence || '');
    h += `</div>`;
    h += `<button class="pf-save-btn" onclick="saveProfile()"><i class="fas fa-save"></i> Enregistrer les modifications</button>`;
    c.innerHTML = h;
    // Init dropdowns
    initRefAdminDropdowns('naissance', p.naissance_chain || []);
    initRefAdminDropdowns('residence', p.residence_chain || []);
}

function renderRefAdmin(prefix, currentVal) {
    let h = '<div class="pf-grid" id="ra_'+prefix+'">';
    adminTypes.forEach((t, i) => {
        h += `<div class="pf-field"><label>${t.nom}</label><select id="ra_${prefix}_${t.ordre}" onchange="onRefAdminChange('${prefix}',${t.ordre},${i})"><option value="">— Sélectionner —</option></select></div>`;
    });
    h += '</div>';
    return h;
}

function initRefAdminDropdowns(prefix, chain) {
    if (!adminTypes.length) return;
    // First level
    const firstOrdre = adminTypes[0].ordre;
    const sel0 = document.getElementById(`ra_${prefix}_${firstOrdre}`);
    if (sel0 && adminInstances[firstOrdre]) {
        adminInstances[firstOrdre].forEach(item => {
            const opt = document.createElement('option');
            opt.value = item.id; opt.textContent = item.nom;
            if (chain.length > 0 && chain[0].id === item.id) opt.selected = true;
            sel0.appendChild(opt);
        });
    }
    // Fill subsequent levels from chain
    for (let i = 1; i < chain.length && i < adminTypes.length; i++) {
        const ordre = adminTypes[i].ordre;
        const parentId = chain[i-1].id;
        fillRefAdminLevel(prefix, ordre, parentId, chain[i].id);
    }
}

function fillRefAdminLevel(prefix, ordre, parentId, selectedId) {
    const sel = document.getElementById(`ra_${prefix}_${ordre}`);
    if (!sel) return;
    sel.innerHTML = '<option value="">— Sélectionner —</option>';
    if (!adminInstances[ordre]) return;
    // Filter by code prefix (rough matching) or show all for this level
    adminInstances[ordre].forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.id; opt.textContent = item.nom;
        if (selectedId && item.id === selectedId) opt.selected = true;
        sel.appendChild(opt);
    });
}

function onRefAdminChange(prefix, ordre, typeIndex) {
    // Clear subsequent levels
    for (let i = typeIndex + 1; i < adminTypes.length; i++) {
        const o = adminTypes[i].ordre;
        const sel = document.getElementById(`ra_${prefix}_${o}`);
        if (sel) sel.innerHTML = '<option value="">— Sélectionner —</option>';
    }
    // Fill next level
    if (typeIndex + 1 < adminTypes.length) {
        const nextOrdre = adminTypes[typeIndex + 1].ordre;
        const selectedId = document.getElementById(`ra_${prefix}_${ordre}`).value;
        if (selectedId) fillRefAdminLevel(prefix, nextOrdre, selectedId, null);
    }
}

function buildRefAdminString(prefix) {
    let parts = [];
    adminTypes.forEach(t => {
        const sel = document.getElementById(`ra_${prefix}_${t.ordre}`);
        if (sel && sel.value) parts.push(sel.value);
    });
    return parts.join('-');
}

function toggleSameAddr() {
    const same = document.getElementById('sameAddr').checked;
    document.getElementById('residenceFields').style.display = same ? 'none' : 'block';
}

async function saveProfile() {
    const body = {
        id_eleve: ID_ELEVE,
        telephone: document.getElementById('pf_telephone')?.value || '',
        email: document.getElementById('pf_email')?.value || '',
        nationalite: document.getElementById('pf_nationalite')?.value || '',
        etat_civil: document.getElementById('pf_etat_civil')?.value || '',
        ref_administrative_naissance: buildRefAdminString('naissance'),
    };
    if (document.getElementById('sameAddr')?.checked) {
        body.ref_administrative_residence = body.ref_administrative_naissance;
    } else {
        body.ref_administrative_residence = buildRefAdminString('residence');
    }
    try {
        const r = await fetch('/parent/api/profile/update/', {
            method: 'POST',
            headers: {'Content-Type':'application/json','X-CSRFToken': getCsrfToken()},
            body: JSON.stringify(body)
        });
        const d = await r.json();
        if (d.success) showToast('Profil mis à jour', 'success');
        else showToast(d.error || 'Erreur', 'error');
    } catch(e) { showToast('Erreur réseau', 'error'); }
}

async function uploadPhoto(input) {
    if (!input.files || !input.files[0]) return;
    const fd = new FormData();
    fd.append('id_eleve', ID_ELEVE);
    fd.append('photo', input.files[0]);
    try {
        const r = await fetch('/parent/api/profile/photo/', {
            method: 'POST',
            headers: {'X-CSRFToken': getCsrfToken()},
            body: fd
        });
        const d = await r.json();
        if (d.success) {
            showToast('Photo mise à jour', 'success');
            const av = document.getElementById('pfAvatar');
            if (av && d.photo_url) av.innerHTML = `<img src="${d.photo_url}">`;
        } else showToast(d.error || 'Erreur', 'error');
    } catch(e) { showToast('Erreur réseau', 'error'); }
}

/* ═══ COMMUNICATION — SEBC WhatsApp-style + Notifications ═══ */
let commContacts = [];
let commActiveContact = null;
let commThreadsCache = {};
let _pollTimer = null;
let _totalUnread = 0;

/* Notification sound — two-tone WhatsApp-style chime */
function _playNotifSound(){
    try{
        const a=new(window.AudioContext||window.webkitAudioContext)();
        const g=a.createGain();g.connect(a.destination);g.gain.value=0.4;
        // First tone
        const o1=a.createOscillator();o1.connect(g);o1.frequency.value=783.99;o1.type='sine';
        o1.start(a.currentTime);o1.stop(a.currentTime+0.12);
        // Second tone (higher)
        const o2=a.createOscillator();o2.connect(g);o2.frequency.value=1046.5;o2.type='sine';
        o2.start(a.currentTime+0.15);o2.stop(a.currentTime+0.3);
        g.gain.exponentialRampToValueAtTime(0.01,a.currentTime+0.35);
    }catch(e){}
}

/* System notification — persists in phone notification bar */
async function _showSystemNotif(title, body){
    if(!('Notification' in window))return;
    if(Notification.permission==='granted'){
        try{
            if('serviceWorker' in navigator){
                const reg=await navigator.serviceWorker.ready;
                if(reg){
                    await reg.showNotification(title,{
                        body:body,
                        icon:'/static/MonEcole_app/icons/icon-512.png',
                        badge:'/static/MonEcole_app/icons/icon-512.png',
                        tag:'monecole-msg',
                        renotify:true,
                        requireInteraction:true,
                        vibrate:[200,100,200,100,200],
                        data:{url:window.location.href}
                    });
                    return;
                }
            }
            // Fallback: basic Notification API
            new Notification(title,{body:body,icon:'/static/MonEcole_app/icons/icon-512.png',requireInteraction:true});
        }catch(e){
            try{new Notification(title,{body:body,icon:'/static/MonEcole_app/icons/icon-512.png'});}catch(e2){}
        }
    }else if(Notification.permission!=='denied'){
        const perm=await Notification.requestPermission();
        if(perm==='granted'){
            try{new Notification(title,{body:body,icon:'/static/MonEcole_app/icons/icon-512.png',requireInteraction:true});}catch(e){}
        }
    }
}

/* Request notification permission proactively (must be user-gesture triggered on mobile) */
async function _requestNotifPermission(){
    if('Notification' in window && Notification.permission==='default'){
        try{ await Notification.requestPermission(); }catch(e){}
    }
}

function _updateUnreadBadge(){
    _totalUnread=0;
    for(const tid in commThreadsCache){_totalUnread+=(commThreadsCache[tid].unread||0);}
    // Update FAB badge
    let b=document.getElementById('fabNotifBadge');
    const fab=document.querySelector('.fab-btn.messages');
    if(_totalUnread>0){
        if(!b&&fab){b=document.createElement('span');b.id='fabNotifBadge';b.className='fab-notif-badge';fab.style.position='relative';fab.appendChild(b);}
        if(b)b.textContent=_totalUnread>9?'9+':_totalUnread;
        document.title=`(${_totalUnread}) MonEcole — Messages`;
    }else{
        if(b)b.remove();
        document.title='MonEcole — Espace Parents';
    }
}

async function loadComm() {
    try {
        const cr = await fetch(`/parent/api/messages/contacts/?id_eleve=${ID_ELEVE}`);
        const cd = await cr.json();
        if (cd.success) {
            commContacts = [];
            (cd.contacts.direction||[]).forEach(c => commContacts.push({...c, type:'direction', icon:'user-tie', color:'#ea580c'}));
            (cd.contacts.enseignants||[]).forEach(c => commContacts.push({...c, type:'teacher', icon:'chalkboard-teacher', color:'#16a34a'}));
        }
        const mr = await fetch(`/parent/api/messages/?id_eleve=${ID_ELEVE}`);
        const md = await mr.json();
        if (md.success) { (md.threads||[]).forEach(t => { commThreadsCache[t.thread_id] = t; }); }
    } catch(e) { console.error(e); }
    renderContactsScreen();
    _updateUnreadBadge();
    _requestNotifPermission();
    // Start polling every 6 seconds
    if(_pollTimer)clearInterval(_pollTimer);
    _pollTimer=setInterval(_pollNewMessages,6000);
}

async function _pollNewMessages(){
    try{
        const r=await fetch(`/parent/api/messages/?id_eleve=${ID_ELEVE}`);
        const d=await r.json();
        if(!d.success)return;
        let hadNew=false;const oldUnread=_totalUnread;
        (d.threads||[]).forEach(t=>{
            const old=commThreadsCache[t.thread_id];
            const oldCount=old?old.unread:0;
            commThreadsCache[t.thread_id]=t;
            if(t.unread>oldCount)hadNew=true;
        });
        _updateUnreadBadge();
        if(hadNew&&_totalUnread>oldUnread){_playNotifSound();showToast('💬 Nouveau message reçu','info');_showSystemNotif('MonEcole',`${_totalUnread} nouveau${_totalUnread>1?'x':''} message${_totalUnread>1?'s':''}`);}
        // Refresh contacts if visible
        const sc=document.getElementById('screenContacts');
        if(sc&&sc.style.display!=='none')renderContactsScreen();
        // Refresh chat if open
        if(commActiveContact){
            const npid=Number(commActiveContact.id_personnel);
            let tid=findTid(npid);
            let tc=tid?commThreadsCache[tid]:null;
            // Broader scan if findTid fails
            if(!tc){
                for(const ttid in commThreadsCache){
                    const tt=commThreadsCache[ttid];
                    if(tt.messages && tt.messages.some(m=>Number(m.sender_personnel_id)===npid||Number(m.target_personnel_id)===npid)){
                        tc=tt;tid=ttid;break;
                    }
                }
            }
            if(tc&&tc.messages){const ma=document.getElementById('msgArea');if(ma)_renderMsgs(tc.messages,ma);}
        }
    }catch(e){}
}

function renderContactsScreen() {
    const area = document.getElementById('commArea');
    const dirs = commContacts.filter(c => c.type==='direction');
    const teachers = commContacts.filter(c => c.type==='teacher');
    let h = `<div id="screenContacts" style="display:flex;flex-direction:column;height:100%">
      <div class="wa-sb-head"><i class="fas fa-comments"></i> Messages${_totalUnread>0?` <span style="margin-left:6px;background:#25d366;padding:1px 7px;border-radius:10px;font-size:.6rem">${_totalUnread}</span>`:''}
        <button onclick="refreshComm()" style="margin-left:auto;background:rgba(255,255,255,.15);border:none;color:#fff;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:.72rem"><i class="fas fa-sync-alt"></i></button>
      </div>
      <div class="wa-search"><input type="text" placeholder="Rechercher un contact..." oninput="filterC(this.value)"></div>
      <div id="cList" style="flex:1;overflow-y:auto">`;
    if (dirs.length) {
        h += `<div class="wa-section-label direction"><i class="fas fa-user-tie"></i> Direction <span class="wa-count">(${dirs.length})</span></div>`;
        dirs.forEach(c => { h += contactRow(c); });
    }
    if (teachers.length) {
        h += `<div class="wa-section-label teachers"><i class="fas fa-chalkboard-teacher"></i> Enseignants <span class="wa-count">(${teachers.length})</span></div>`;
        teachers.forEach(c => { h += contactRow(c); });
    }
    if (!commContacts.length) h += '<div style="padding:40px;text-align:center;color:#94a3b8;font-size:.8rem"><i class="fas fa-user-slash" style="display:block;font-size:2.5rem;opacity:.15;margin-bottom:12px"></i>Aucun contact</div>';
    h += `</div></div><div id="screenChat" style="display:none;flex-direction:column;height:100%;position:relative"></div>`;
    area.innerHTML = h;
}

function contactRow(c) {
    const tid = findTid(c.id_personnel);
    const tc = tid ? commThreadsCache[tid] : null;
    const sub = tc && tc.messages && tc.messages.length ? tc.messages[0].message.substring(0,40) : c.role||'';
    const unread = tc ? tc.unread : 0;
    const time = tc && tc.messages && tc.messages.length ? tc.messages[0].time : '';
    return `<div class="wa-contact" onclick="openChat(${c.id_personnel})" data-name="${(c.nom||'').toLowerCase()}">
      <div class="wa-contact-avatar" style="background:${c.color}"><i class="fas fa-${c.icon}"></i></div>
      <div class="wa-contact-info"><div class="wa-contact-name">${c.nom}</div><div class="wa-contact-sub">${sub}</div></div>
      <div class="wa-contact-meta">${time?`<span class="wa-contact-time">${time}</span>`:''}${unread>0?`<div class="wa-unread-badge">${unread}</div>`:''}</div>
    </div>`;
}

function findTid(pid) {
    const npid = Number(pid);
    // First: match by personnel_ids in thread data (authoritative)
    for (const tid in commThreadsCache) {
        const t = commThreadsCache[tid];
        if (t.personnel_ids && t.personnel_ids.map(Number).includes(npid)) return tid;
    }
    // Fallback: match by message sender/target in thread messages
    for (const tid in commThreadsCache) {
        const t = commThreadsCache[tid];
        if (t.messages) {
            for (const m of t.messages) {
                if (Number(m.sender_personnel_id) === npid || Number(m.target_personnel_id) === npid) return tid;
            }
        }
    }
    return null;
}

function openChat(pid) {
    commActiveContact = commContacts.find(c => c.id_personnel === pid);
    if (!commActiveContact) return;
    document.getElementById('screenContacts').style.display = 'none';
    const chat = document.getElementById('screenChat');
    chat.style.display = 'flex';
    const ca = commActiveContact;
    const roleLabel = ca.role || (ca.type==='direction' ? 'Direction' : 'Enseignant');
    chat.innerHTML = `
      <div class="wa-chat-bg"></div>
      <div class="wa-chat-head">
        <button onclick="backToContacts()" style="background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;padding:4px;margin-right:4px"><i class="fas fa-arrow-left"></i></button>
        <div class="wa-contact-avatar" style="background:${ca.color};width:38px;height:38px;font-size:.7rem"><i class="fas fa-${ca.icon}"></i></div>
        <div style="flex:1;min-width:0"><div style="font-size:.82rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${ca.nom}</div><div style="font-size:.55rem;opacity:.8;font-weight:400">${roleLabel}</div></div>
      </div>
      <div id="msgArea" style="flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:6px;background:#ece5dd;position:relative;z-index:1;scrollbar-width:thin">
        <div style="text-align:center;color:#94a3b8;font-size:.65rem;margin:auto"><i class="fas fa-spinner fa-spin" style="display:block;margin-bottom:4px"></i>Chargement...</div>
      </div>
      <div id="pendingAttachBar" class="wa-pending-attach" style="display:none">
        <i class="fas fa-paperclip" style="color:#128c7e"></i>
        <span id="pendingFileName" style="flex:1;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"></span>
        <span id="pendingFileSize" style="color:#94a3b8;font-size:.58rem"></span>
        <span class="remove" onclick="clearPendingFile()">×</span>
      </div>
      <div class="wa-input-bar">
        <label style="width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#128c7e,#25d366);display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;color:#fff;font-size:.9rem;box-shadow:0 2px 8px rgba(18,140,126,.3)"><i class="fas fa-paperclip"></i><input type="file" id="chatFileInput" onchange="onChatFileSelected(this)" style="display:none" accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip"></label>
        <input type="text" id="msgIn" placeholder="Écrivez un message..." onkeydown="if(event.key==='Enter')sendM()">
        <button onclick="sendM()"><i class="fas fa-paper-plane"></i></button>
      </div>`;
    // Fetch messages from API for fresh data
    const tid = findTid(pid);
    _loadChatMessages(tid, pid);
    document.getElementById('msgIn')?.focus();
    // Mark as read
    const tc = tid ? commThreadsCache[tid] : null;
    if (tc && tc.unread > 0) {
        tc.unread = 0;
        _updateUnreadBadge();
        fetch('/parent/api/messages/read/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},body:JSON.stringify({thread_id:tid})}).catch(()=>{});
    }
}

async function _loadChatMessages(tid, pid) {
    const ma = document.getElementById('msgArea'); if(!ma) return;
    const tc = tid ? commThreadsCache[tid] : null;
    // Show cached first
    if (tc && tc.messages && tc.messages.length) _renderMsgs(tc.messages, ma);
    // Then fetch fresh from API
    try {
        const r = await fetch(`/parent/api/messages/?id_eleve=${ID_ELEVE}`);
        const d = await r.json();
        if (d.success) {
            (d.threads||[]).forEach(t => { commThreadsCache[t.thread_id] = t; });
            // Re-find tid after cache refresh (critical for first-load)
            const freshTid = tid || findTid(pid);
            const freshTc = freshTid ? commThreadsCache[freshTid] : null;
            if (freshTc && freshTc.messages && freshTc.messages.length) {
                _renderMsgs(freshTc.messages, ma);
                // Mark as read if we just loaded
                if (freshTc.unread > 0) {
                    freshTc.unread = 0;
                    _updateUnreadBadge();
                    fetch('/parent/api/messages/read/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},body:JSON.stringify({thread_id:freshTid})}).catch(()=>{});
                }
            } else if (!tc || !tc.messages || !tc.messages.length) {
                // Also scan ALL threads to find any containing messages from/to this personnel
                const npid = Number(pid);
                for (const ttid in commThreadsCache) {
                    const tt = commThreadsCache[ttid];
                    if (tt.messages) {
                        const hasMatch = tt.messages.some(m => 
                            Number(m.sender_personnel_id) === npid || Number(m.target_personnel_id) === npid);
                        if (hasMatch) {
                            _renderMsgs(tt.messages, ma);
                            return;
                        }
                    }
                }
                ma.innerHTML = '<div style="text-align:center;color:#94a3b8;font-size:.7rem;margin:auto"><i class="fas fa-comments" style="display:block;font-size:2.5rem;opacity:.12;margin-bottom:8px;color:#128c7e"></i>Démarrez une conversation</div>';
            }
        }
    } catch(e) {
        if (!tc || !tc.messages || !tc.messages.length) {
            ma.innerHTML = '<div style="text-align:center;color:#94a3b8;font-size:.7rem;margin:auto"><i class="fas fa-comments" style="display:block;font-size:2.5rem;opacity:.12;margin-bottom:8px;color:#128c7e"></i>Démarrez une conversation</div>';
        }
    }
}

/* Pending file management */
let _pendingFile = null;
function onChatFileSelected(input) {
    if (!input.files||!input.files[0]) return;
    const f = input.files[0];
    if (f.size > 10*1024*1024) { showToast('Fichier trop volumineux (max 10MB)','error'); input.value=''; return; }
    _pendingFile = f;
    document.getElementById('pendingAttachBar').style.display = 'flex';
    document.getElementById('pendingFileName').textContent = f.name;
    const kb = Math.round(f.size/1024);
    document.getElementById('pendingFileSize').textContent = kb>1024 ? `${(kb/1024).toFixed(1)} MB` : `${kb} KB`;
}
function clearPendingFile() {
    _pendingFile = null;
    document.getElementById('pendingAttachBar').style.display = 'none';
    const fi = document.getElementById('chatFileInput'); if(fi) fi.value = '';
}

function _renderMsgs(msgs, area) {
    if (!msgs || !msgs.length) { area.innerHTML = '<div style="text-align:center;color:#94a3b8;font-size:.7rem;margin:auto"><i class="fas fa-comments" style="display:block;font-size:2.5rem;opacity:.12;margin-bottom:8px;color:#128c7e"></i>Démarrez une conversation</div>'; return; }
    let h = '', lastDate = '';
    const sorted = msgs.slice().reverse();
    sorted.forEach(m => {
        const msgDate = m.created_at ? m.created_at.split(' ')[0] : '';
        if (msgDate && msgDate !== lastDate) {
            const d = new Date(msgDate); const today = new Date(); const yest = new Date(today); yest.setDate(today.getDate()-1);
            let label = d.toLocaleDateString('fr-FR',{day:'2-digit',month:'long',year:'numeric'});
            if (d.toDateString()===today.toDateString()) label="Aujourd'hui";
            else if (d.toDateString()===yest.toDateString()) label="Hier";
            h += `<div class="wa-date-sep"><span>${label}</span></div>`;
            lastDate = msgDate;
        }
        const dir = m.is_mine ? 'sent' : 'recv';
        const statusIcon = m.is_mine ? '<span class="msg-status"><i class="fas fa-check-double"></i></span>' : '';
        h += `<div class="wa-msg ${dir}">`;
        if (!m.is_mine && m.sender_name) h += `<div class="wa-msg-sender">${m.sender_name}</div>`;
        // Scope badge — individual vs class vs etab
        if (!m.is_mine && m.scope) {
            const scopeMap = {
                'individual': {icon:'fa-user',label:'Personnel',bg:'#dcfce7',color:'#059669'},
                'class': {icon:'fa-users',label:'Classe',bg:'#dbeafe',color:'#2563eb'},
                'etab': {icon:'fa-school',label:'Établissement',bg:'#fef3c7',color:'#d97706'},
            };
            const s = scopeMap[m.scope];
            if (s) h += `<div style="display:inline-flex;align-items:center;gap:3px;font-size:.48rem;background:${s.bg};color:${s.color};padding:1px 6px;border-radius:4px;font-weight:600;margin-bottom:3px"><i class="fas ${s.icon}" style="font-size:.4rem"></i>${s.label}</div>`;
        }
        if (m.subject) h += `<div style="font-size:.58rem;font-weight:700;color:#075e54;margin-bottom:2px">📌 ${m.subject}</div>`;
        if (m.attachment) {
            const att = m.attachment;
            const ext = (att.name||'').split('.').pop().toLowerCase();
            if (['jpg','jpeg','png','gif','webp'].includes(ext) || (att.type||'').startsWith('image')) {
                h += `<div style="margin:4px 0"><a href="${att.url}" target="_blank"><img src="${att.url}" style="max-width:220px;max-height:180px;border-radius:10px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.1)" loading="lazy"></a></div>`;
            } else {
                const iconCls = ext==='pdf'?'pdf':['doc','docx','odt'].includes(ext)?'doc':'other';
                const icon = ext==='pdf'?'fa-file-pdf':['doc','docx','odt'].includes(ext)?'fa-file-word':['xls','xlsx'].includes(ext)?'fa-file-excel':'fa-file';
                h += `<a href="${att.url}" target="_blank" class="wa-attach-card"><div class="wa-attach-icon ${iconCls}"><i class="fas ${icon}"></i></div><div style="flex:1;min-width:0"><div style="font-size:.7rem;font-weight:600;color:#0f172a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${att.name||'Fichier'}</div><div style="font-size:.5rem;color:#94a3b8">Cliquez pour ouvrir</div></div><i class="fas fa-download" style="color:#94a3b8;font-size:.65rem"></i></a>`;
            }
        }
        if (m.message && m.message !== '📎 Pièce jointe') h += `<div>${m.message}</div>`;
        else if (!m.attachment) h += `<div>${m.message}</div>`;
        h += `<div class="wa-msg-time">${m.time||''} ${statusIcon}</div></div>`;
    });
    area.innerHTML = h;
    area.scrollTop = area.scrollHeight;
}

function backToContacts() {
    commActiveContact = null;
    document.getElementById('screenChat').style.display = 'none';
    document.getElementById('screenContacts').style.display = 'flex';
    renderContactsScreen();
}

function filterC(q) {
    const f = q.toLowerCase();
    document.querySelectorAll('#cList .wa-contact').forEach(el => { el.style.display = !f || (el.dataset.name||'').includes(f) ? '' : 'none'; });
}

function refreshComm() { sectionsLoaded['comm']=false; commThreadsCache={}; loadComm(); }

async function sendM() {
    if (!commActiveContact) return;
    const inp = document.getElementById('msgIn');
    const txt = inp.value.trim();
    const hasFile = !!_pendingFile;
    if (!txt && !hasFile) return;
    inp.value = '';
    const area = document.getElementById('msgArea');
    const em = area.querySelector('div[style*="margin:auto"]'); if (em) em.remove();
    const t = new Date(), time = t.getHours().toString().padStart(2,'0')+':'+t.getMinutes().toString().padStart(2,'0');
    // Optimistic UI
    const el = document.createElement('div'); el.className = 'wa-msg sent';
    let optH = '';
    if (hasFile) optH += `<div style="display:flex;align-items:center;gap:6px;padding:4px 8px;background:rgba(0,0,0,.04);border-radius:6px;margin-bottom:3px;font-size:.65rem"><i class="fas fa-paperclip" style="color:#128c7e"></i> ${_pendingFile.name}</div>`;
    if (txt) optH += `<div>${txt}</div>`;
    optH += `<div class="wa-msg-time">${time} <span class="msg-status"><i class="fas fa-clock"></i></span></div>`;
    el.innerHTML = optH;
    area.appendChild(el); area.scrollTop = area.scrollHeight;
    try {
        let r;
        if (hasFile) {
            const fd = new FormData();
            fd.append('id_eleve', ID_ELEVE);
            fd.append('target_personnel_id', commActiveContact.id_personnel);
            fd.append('scope', 'teacher');
            fd.append('message', txt || `📎 ${_pendingFile.name}`);
            fd.append('attachment', _pendingFile);
            r = await fetch('/parent/api/messages/send/',{method:'POST',headers:{'X-CSRFToken':getCsrfToken()},body:fd});
            clearPendingFile();
        } else {
            r = await fetch('/parent/api/messages/send/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCsrfToken()},body:JSON.stringify({id_eleve:ID_ELEVE,message:txt,target_personnel_id:commActiveContact.id_personnel,scope:'teacher'})});
        }
        const d = await r.json();
        if (d.success) {
            const s = el.querySelector('.msg-status'); if(s) s.innerHTML = '<i class="fas fa-check-double"></i>';
            if (d.email_sent) {
                showToast('✉️ Message envoyé et email livré à l\'enseignant','success');
            } else {
                showToast('Message envoyé','success');
            }
        } else showToast(d.error||'Erreur','error');
    } catch(e) { showToast('Erreur réseau','error'); }
}
