odoo.define('l10n_ec_web_hr_recruitment.form', function (require) {
    'use strict';
    
var core = require('web.core');
var FormEditorRegistry = require('website_form.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('apply_job', {
    fields: [{
        name: 'partner_study',
        type: 'many2one',
        relation: 'hr.study',
        string: _t('Preparation Academic'),
    }, {
        name: 'partner_experience',
        type: 'char',
        string: _t('Work Experience'),
    }, {
        name: 'partner_futher',
        type: 'char',
        string: _t('Further Training'),
    }],
});

});