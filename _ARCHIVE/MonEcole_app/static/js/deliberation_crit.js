

document.addEventListener('DOMContentLoaded', function () {
    const logFormData = (formData) => {
        console.log('Form data:', Object.fromEntries(formData));
   };

    const handleFormSubmission = (form, successRedirect, failureRedirect) => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log(`${form.id} submit triggered`);

            const formData = new FormData(form);
            logFormData(formData);

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => {
                    console.log('Response status:', response.status);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.text();
                })
                .then(text => {
                    console.log('Raw response:', text);
                    try {
                        const data = JSON.parse(text);
                        console.log('Response data:', data);
                        alert(data.message);
                        window.location.href = data.redirect || successRedirect;
                    } catch (e) {
                        throw new Error(`JSON parse error: ${e.message}`);
                    }
                })
                .catch(error => {
                    console.error('Erreur lors de la soumission:', error);
                    alert('Erreur lors de la soumission du formulaire : ' + error.message);
                    window.location.href = failureRedirect;
                });
        });
    };

    // Mention Edit Functionality
    const mentionButtons = document.querySelectorAll('.edit-btn-mention');
    mentionButtons.forEach(button => {
        button.addEventListener('click', function () {
            document.getElementById('mention_id').value = this.dataset.mentionId || '';
            document.getElementById('mention').value = this.dataset.mention || '';
            document.getElementById('abbreviation').value = this.dataset.abbreviation || '';
            document.getElementById('min').value = this.dataset.min || '';
            document.getElementById('max').value = this.dataset.max || '';

            /*console.log('Mention modal fields populated:', {
                id_mention: this.dataset.mentionId,
                mention: this.dataset.mention,
                abbreviation: this.dataset.abbreviation,
                min: this.dataset.min,
                max: this.dataset.max
            });*/
        });
    });

    const mentionForm = document.getElementById('edit_mention_form');
    if (mentionForm) {
        console.log('Edit mention form listener attached');
        handleFormSubmission(mentionForm, '/create_mention', '/create_mention');
    } else {
        console.warn('Edit mention form not found');
    }

    // Session Edit Functionality
    const sessionButtons = document.querySelectorAll('.edit-btn-session');
    sessionButtons.forEach(button => {
        button.addEventListener('click', function () {
            document.getElementById('session_id').value = this.dataset.sessionId || '';
            document.getElementById('session').value = this.dataset.session || '';

           /* console.log('Session modal fields populated:', {
                id_session: this.dataset.sessionId,
                session: this.dataset.session
            });*/
        });
    });

    const sessionForm = document.getElementById('edit_session_form');
    if (sessionForm) {
       // console.log('Edit session form listener attached');
        handleFormSubmission(sessionForm, '/create_session', '/create_session');
    } else {
        console.warn('Edit session form not found');
    }

    // Deliberation Type Edit Functionality
    const deliberationTypeButtons = document.querySelectorAll('.edit-btn-deliberation-type');
    deliberationTypeButtons.forEach(button => {
        button.addEventListener('click', function () {
            document.getElementById('deliberation_type_id').value = this.dataset.deliberationTypeId || '';
            document.getElementById('type').value = this.dataset.type || '';

           /* console.log('Deliberation Type modal fields populated:', {
                id_deliberation_type: this.dataset.deliberationTypeId,
                type: this.dataset.type
            });*/
        });
    });

    const deliberationTypeForm = document.getElementById('edit_deliberation_type_form');
    if (deliberationTypeForm) {
        //console.log('Edit deliberation type form listener attached');
        handleFormSubmission(deliberationTypeForm, '/create_deliberation_type', '/create_deliberation_type');
    } else {
        console.warn('Edit deliberation type form not found');
    }

    // Deliberation Finalite Edit Functionality
    const finaliteButtons = document.querySelectorAll('.edit-btn-finalite');
    finaliteButtons.forEach(button => {
        button.addEventListener('click', function () {
            document.getElementById('finalite_id').value = this.dataset.finaliteId || '';
            document.getElementById('finalite').value = this.dataset.finalite || '';
            document.getElementById('sigle').value = this.dataset.sigle || '';

            /*console.log('Finalite modal fields populated:', {
                id_finalite: this.dataset.finaliteId,
                finalite: this.dataset.finalite
            });*/
        });
    });

    const finaliteForm = document.getElementById('edit_finalite_form');
    if (finaliteForm) {
        //console.log('Edit finalite form listener attached');
        handleFormSubmission(finaliteForm, '/create_deliberation_finalite', '/create_deliberation_finalite');
    } else {
        console.warn('Edit finalite form not found');
    }

});