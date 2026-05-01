/* parent_child.js — Logic for parent child detail page */
const ID_ELEVE = window._ELEVE_ID;
let sectionsLoaded = {};

function showSection(name) {
    document.querySelectorAll('.section-pane').forEach(p => p.style.display = 'none');
    const el = document.getElementById('sec-' + name);
    if (el) el.style.display = 'block';
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
            c.innerHTML = '<div class="empty-msg"><i class="fas fa-clipboard-list"></i>Aucune note disponible</div>';
            return;
        }
        let h = '';
        d.evaluations.forEach(n => {
            const v = n.note_eleve !== null ? parseFloat(n.note_eleve) : null;
            const cls = v === null ? 'na' : v >= 14 ? 'good' : v >= 10 ? 'avg' : 'poor';
            h += `<div class="data-row"><div class="data-main"><div class="data-title">${n.cours||'—'}</div><div class="data-sub">${n.title||''} · ${n.date_eval||''}</div></div><div class="data-badge ${cls}">${v !== null ? v.toFixed(1) : '—'}/${n.ponderation||20}</div></div>`;
        });
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
        const r = await fetch(`/parent/api/child-profile/?id_eleve=${ID_ELEVE}`);
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
        const r = await fetch('/parent/api/update-profile/', {
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
        const r = await fetch('/parent/api/upload-photo/', {
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

/* ═══ COMMUNICATION (WhatsApp-style) ═══ */
let commContacts = [];
let commActiveContact = null;
let commThreadsCache = {};

async function loadComm() {
    const container = document.getElementById('commArea');
    try {
        const cr = await fetch(`/parent/api/messages/contacts/?id_eleve=${ID_ELEVE}`);
        const cd = await cr.json();
        if (cd.success) {
            commContacts = [];
            (cd.contacts.direction||[]).forEach(c => commContacts.push({...c, type:'direction', icon:'user-tie', color:'#ea580c'}));
            (cd.contacts.enseignants||[]).forEach(c => commContacts.push({...c, type:'teacher', icon:'chalkboard-teacher', color:'#16a34a'}));
        }
        // Load threads
        const mr = await fetch(`/parent/api/messages/?id_eleve=${ID_ELEVE}`);
        const md = await mr.json();
        if (md.success) {
            (md.threads||[]).forEach(t => { commThreadsCache[t.thread_id] = t; });
        }
    } catch(e) { console.error(e); }
    renderCommSidebar();
}

function renderCommSidebar() {
    const panel = document.getElementById('commArea');
    let h = `<div class="wa-wrap">
        <div class="wa-sidebar" id="waParentSidebar">
            <div class="wa-sb-head"><i class="fas fa-comments"></i> Messages</div>
            <div class="wa-search"><input type="text" placeholder="Rechercher..." oninput="filterCommContacts(this.value)"></div>
            <div class="wa-contacts" id="waParentContacts">`;
    if (commContacts.length === 0) {
        h += '<div style="padding:20px;text-align:center;color:#94a3b8;font-size:.75rem">Aucun contact</div>';
    } else {
        commContacts.forEach(c => {
            const tid = `p_${ID_ELEVE}_${c.id_personnel}`;
            const tc = commThreadsCache[tid];
            const lastMsg = tc ? (tc.messages && tc.messages.length ? tc.messages[0].message.substring(0,40) : tc.subject||'') : c.role||'';
            const unread = tc ? tc.unread : 0;
            h += `<div class="wa-contact" onclick="openCommChat(${c.id_personnel})" data-name="${(c.nom||'').toLowerCase()}">
                <div class="wa-contact-avatar" style="background:${c.color}"><i class="fas fa-${c.icon}"></i></div>
                <div class="wa-contact-info"><div class="wa-contact-name">${c.nom}</div><div class="wa-contact-sub">${lastMsg}</div></div>
                <div class="wa-contact-meta">${unread>0?`<div class="wa-unread-badge">${unread}</div>`:''}</div>
            </div>`;
        });
    }
    h += `</div></div>
        <div class="wa-chat" id="waParentChat">
            <div class="wa-chat-bg"></div>
            <div class="wa-empty"><i class="fas fa-comments"></i><div class="wa-empty-text">Sélectionnez un contact</div><div class="wa-empty-sub">Choisissez un enseignant ou la direction</div></div>
        </div>
    </div>`;
    panel.innerHTML = h;
}

function filterCommContacts(q) {
    const f = q.toLowerCase();
    document.querySelectorAll('#waParentContacts .wa-contact').forEach(el => {
        el.style.display = !f || (el.dataset.name||'').includes(f) ? '' : 'none';
    });
}

async function openCommChat(personnelId) {
    commActiveContact = commContacts.find(c => c.id_personnel === personnelId);
    if (!commActiveContact) return;
    const sidebar = document.getElementById('waParentSidebar');
    if (window.innerWidth <= 768 && sidebar) sidebar.classList.add('hidden');
    const panel = document.getElementById('waParentChat');
    const tid = `p_${ID_ELEVE}_${personnelId}`;
    let h = `<div class="wa-chat-bg"></div>
        <div class="wa-chat-head">
            <button class="back-btn" onclick="showCommSidebar()"><i class="fas fa-arrow-left"></i></button>
            <div class="wa-contact-avatar" style="background:${commActiveContact.color};width:36px;height:36px;font-size:.65rem"><i class="fas fa-${commActiveContact.icon}"></i></div>
            <div style="flex:1"><div>${commActiveContact.nom}</div><div style="font-size:.55rem;opacity:.8">${commActiveContact.role||'Contact'}</div></div>
        </div>
        <div class="wa-messages" id="waParentMessages"><div style="text-align:center;color:#94a3b8;font-size:.65rem;margin:auto"><i class="fas fa-spinner fa-spin"></i> Chargement...</div></div>
        <div class="wa-input-bar">
            <input type="text" id="waParentInput" placeholder="Écrivez un message..." onkeydown="if(event.key==='Enter')sendCommMsg()">
            <button onclick="sendCommMsg()"><i class="fas fa-paper-plane"></i></button>
        </div>`;
    panel.innerHTML = h;
    // Load thread messages
    const tc = commThreadsCache[tid];
    const area = document.getElementById('waParentMessages');
    if (tc && tc.messages && tc.messages.length) {
        renderCommMessages(tc.messages);
    } else {
        area.innerHTML = '<div style="text-align:center;color:#94a3b8;font-size:.65rem;margin:auto"><i class="fas fa-comments" style="display:block;font-size:2rem;opacity:.15;margin-bottom:4px"></i>Démarrez une conversation</div>';
    }
    document.getElementById('waParentInput')?.focus();
}

function renderCommMessages(msgs) {
    const area = document.getElementById('waParentMessages');
    if (!area) return;
    let h = '';
    msgs.forEach(m => {
        const dir = m.is_mine ? 'sent' : 'recv';
        h += `<div class="wa-msg ${dir}">`;
        if (!m.is_mine && m.sender_name) h += `<div class="wa-msg-sender">${m.sender_name}</div>`;
        if (m.subject) h += `<div style="font-size:.58rem;font-weight:700;color:#075e54;margin-bottom:2px">📌 ${m.subject}</div>`;
        h += `<div>${m.message}</div><div class="wa-msg-time">${m.time||''}</div></div>`;
    });
    area.innerHTML = h;
    area.scrollTop = area.scrollHeight;
}

function showCommSidebar() {
    const sb = document.getElementById('waParentSidebar');
    if (sb) sb.classList.remove('hidden');
}

async function sendCommMsg() {
    if (!commActiveContact) return;
    const inp = document.getElementById('waParentInput');
    const txt = inp.value.trim();
    if (!txt) return;
    inp.value = '';
    const area = document.getElementById('waParentMessages');
    // Optimistic UI
    const empt = area.querySelector('div[style*="margin:auto"]');
    if (empt) empt.remove();
    const now = new Date();
    const time = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    const el = document.createElement('div');
    el.className = 'wa-msg sent';
    el.innerHTML = `<div>${txt}</div><div class="wa-msg-time">${time} <span style="color:#34b7f1;font-size:.5rem"><i class="fas fa-clock"></i></span></div>`;
    area.appendChild(el);
    area.scrollTop = area.scrollHeight;
    try {
        const r = await fetch('/parent/api/messages/send/', {
            method: 'POST',
            headers: {'Content-Type':'application/json','X-CSRFToken': getCsrfToken()},
            body: JSON.stringify({id_eleve: ID_ELEVE, message: txt, target_personnel_id: commActiveContact.id_personnel, scope: 'teacher'})
        });
        const d = await r.json();
        if (d.success) {
            const statusEl = el.querySelector('.wa-msg-time span');
            if (statusEl) statusEl.innerHTML = '<i class="fas fa-check-double"></i>';
            showToast('Message envoyé', 'success');
        } else showToast(d.error||'Erreur', 'error');
    } catch(e) { showToast('Erreur réseau', 'error'); }
}
